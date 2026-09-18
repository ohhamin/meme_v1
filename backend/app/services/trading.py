from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from fastapi import HTTPException, status

from backend.app.core.config import get_settings
from backend.app.models.schemas import OrderResult, RiskOrderIntent
from backend.app.services.audit import AuditLogger
from backend.app.services.idempotency import IdempotencyStore
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.push import PushService
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.runtime_settings import RuntimeSettingsService


class TradingService:
    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()
        self.idempotency = IdempotencyStore()
        self.audit = AuditLogger()
        self.push = PushService()
        self.paper = {
            "stock": PaperBroker("stock"),
            "crypto": PaperBroker("crypto"),
        }
        self.risk = RiskGuard()

    def _paper_broker(self, market: str) -> PaperBroker:
        return self.paper[market]

    def _total_open_positions(self) -> int:
        return sum(
            len(broker.portfolio().positions)
            for broker in self.paper.values()
        )

    def stock_positions(self) -> list[dict]:
        runtime = self.runtime.get()
        if runtime.mode == "paper":
            return [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "invested_amount": p.invested_amount,
                    "quantity": p.quantity,
                    "return_rate": p.return_rate,
                    "decision_score": p.decision_score,
                }
                for p in self.paper["stock"].portfolio().positions
            ]

        # TODO: Toss stock adapter connection.
        return []

    def crypto_positions(self) -> list[dict]:
        runtime = self.runtime.get()
        if runtime.mode == "paper":
            return [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "invested_amount": p.invested_amount,
                    "quantity": p.quantity,
                    "return_rate": p.return_rate,
                    "decision_score": p.decision_score,
                }
                for p in self.paper["crypto"].portfolio().positions
            ]

        # TODO: Upbit adapter connection.
        return []

    def manual_stock_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        idempotency_key: str,
    ) -> OrderResult:
        runtime = self.runtime.get()

        if runtime.mode == "paper":
            return self._paper_manual_order(
                market="stock",
                symbol=symbol,
                side=side,
                quantity=Decimal(quantity),
                idempotency_key=idempotency_key,
            )

        return self._live_not_ready(
            symbol=symbol,
            side=side,
            idempotency_key=idempotency_key,
        )

    def manual_crypto_order(
        self,
        *,
        symbol: str,
        side: str,
        amount_krw,
        idempotency_key: str,
    ) -> OrderResult:
        runtime = self.runtime.get()

        if runtime.mode == "paper":
            broker = self._paper_broker("crypto")
            position = broker.position(symbol)
            if position is None or position.last_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "No recent Paper price is available for this crypto. "
                        "Run a market/decision cycle first."
                    ),
                )

            quantity = (
                Decimal(str(amount_krw)) / position.last_price
            ).quantize(
                Decimal("0.00000001"),
                rounding=ROUND_DOWN,
            )

            if quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Calculated crypto quantity is zero.",
                )

            return self._paper_manual_order(
                market="crypto",
                symbol=symbol,
                side=side,
                quantity=quantity,
                idempotency_key=idempotency_key,
            )

        return self._live_not_ready(
            symbol=symbol,
            side=side,
            idempotency_key=idempotency_key,
        )

    def _paper_manual_order(
        self,
        *,
        market: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        idempotency_key: str,
    ) -> OrderResult:
        if side not in {"buy", "sell"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="side must be buy or sell",
            )

        self.idempotency.ensure_new(idempotency_key)
        broker = self._paper_broker(market)

        position = broker.position(symbol)
        if position is None or position.last_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No recent Paper price is available for this symbol. "
                    "Run a market/decision cycle first."
                ),
            )

        portfolio = broker.portfolio()
        action = "BUY" if side == "buy" else "SELL"
        notional = quantity * position.last_price
        data_age_seconds = self._price_age_seconds(
            position.last_price_at
        )

        intent = RiskOrderIntent(
            source="manual",
            market=market,
            symbol=symbol,
            action=action,
            order_notional=notional,
            order_quantity=quantity,
            price=position.last_price,
            portfolio_equity=portfolio.equity,
            available_cash=portfolio.cash,
            position_value=position.market_value,
            position_quantity=position.quantity,
            open_position_count=self._total_open_positions(),
            daily_pnl_pct=portfolio.daily_pnl_pct,
            daily_order_count=portfolio.daily_order_count,
            data_age_seconds=data_age_seconds,
            market_open=position.last_market_open,
            same_cycle_duplicate=False,
        )
        risk = self.risk.evaluate(intent)

        if risk.status != "PASS":
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": (
                        "Risk Guard blocked the manual Paper order."
                    ),
                    "reasons": risk.reasons,
                },
            )

        try:
            execution = broker.execute(
                symbol=symbol,
                name=position.name,
                side=side,
                quantity=quantity,
                market_price=position.last_price,
                decision_score=position.decision_score,
                source="manual",
                market_open=position.last_market_open,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        self.idempotency.remember(
            idempotency_key,
            execution.order_id,
        )

        return OrderResult(
            order_id=execution.order_id,
            symbol=symbol,
            side=side,
            status="paper_filled",
            message=(
                f"Paper manual order filled: {execution.quantity} "
                f"@ {execution.price}"
            ),
            created_at=execution.created_at,
        )

    def _live_not_ready(
        self,
        *,
        symbol: str,
        side: str,
        idempotency_key: str,
    ) -> OrderResult:
        runtime = self.runtime.get()

        if runtime.kill_switch:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=(
                    "Kill switch is enabled. New orders are blocked."
                ),
            )

        self.idempotency.ensure_new(idempotency_key)

        if not self.config.trading_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Live mode is selected, but "
                    "TRADING_ENABLED=false."
                ),
            )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Live broker adapter is not implemented yet.",
        )

    def _price_age_seconds(self, last_price_at) -> int:
        if last_price_at is None:
            return self.config.risk_max_data_age_seconds + 1

        now = datetime.now(last_price_at.tzinfo or timezone.utc)
        return max(
            0,
            int((now - last_price_at).total_seconds()),
        )
