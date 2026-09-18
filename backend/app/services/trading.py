from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from backend.app.core.config import get_settings
from backend.app.models.schemas import OrderResult
from backend.app.services.audit import AuditLogger
from backend.app.services.idempotency import IdempotencyStore
from backend.app.services.push import PushService
from backend.app.services.runtime_settings import RuntimeSettingsService


class TradingService:
    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()
        self.idempotency = IdempotencyStore()
        self.audit = AuditLogger()
        self.push = PushService()

    def stock_positions(self) -> list[dict]:
        # TODO: 국내주식 Broker Adapter 연결
        return []

    def crypto_positions(self) -> list[dict]:
        # TODO: Upbit Adapter 연결
        return []

    def manual_stock_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        idempotency_key: str,
    ) -> OrderResult:
        return self._manual_order(
            market="stock",
            symbol=symbol,
            side=side,
            description=f"{quantity}주",
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
        return self._manual_order(
            market="crypto",
            symbol=symbol,
            side=side,
            description=f"{amount_krw} KRW",
            idempotency_key=idempotency_key,
        )

    def _manual_order(
        self,
        *,
        market: str,
        symbol: str,
        side: str,
        description: str,
        idempotency_key: str,
    ) -> OrderResult:
        runtime = self.runtime.get()

        if runtime.kill_switch:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Kill switch is enabled. New orders are blocked.",
            )

        self.idempotency.ensure_new(idempotency_key)
        now = datetime.now(timezone.utc)

        if runtime.mode == "paper":
            result = OrderResult(
                order_id=f"paper-{uuid4().hex[:12]}",
                symbol=symbol,
                side=side,
                status="paper_filled",
                message=f"Paper order simulated: {description}",
                created_at=now,
            )
            self.idempotency.remember(idempotency_key, result.order_id)
            self.audit.write(
                "orders",
                {
                    "source": "manual",
                    "market": market,
                    "mode": "paper",
                    "symbol": symbol,
                    "side": side,
                    "description": description,
                    "order_id": result.order_id,
                    "status": result.status,
                },
            )
            self.push.send(
                title="Paper 주문 처리",
                body=f"{symbol} {side.upper()} {description}",
                data={
                    "market": market,
                    "symbol": symbol,
                    "side": side,
                    "order_id": result.order_id,
                },
            )
            return result

        if not self.config.trading_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Live mode is selected, but TRADING_ENABLED=false.",
            )

        # 실제 Adapter 연결 전에는 절대로 주문하지 않는다.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Live broker adapter is not implemented yet.",
        )
