from decimal import Decimal

from fastapi import HTTPException

from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)
from backend.app.models.schemas import (
    LiveAutoCycleResponse,
    LiveCycleExecutionItem,
    PositionSizeResult,
    RiskGuardResult,
    RiskOrderIntent,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.decision_cycle import DecisionCycleService
from backend.app.services.decision_store import DecisionMarkdownStore
from backend.app.services.live_order_service import LiveOrderService
from backend.app.services.live_portfolio_snapshot import (
    LivePortfolioSnapshotService,
)
from backend.app.services.position_sizer import PositionSizer
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.upbit_universe import UpbitUniverseService
from backend.app.services.cycle_metrics import CycleMetricsStore


class LiveAutoCycleService:
    """Prepared live automatic cycle, disabled by default with explicit gates."""

    def __init__(self):
        self.config = RuntimeSettingsService().config
        self.runtime = RuntimeSettingsService()
        self.decisions = DecisionCycleService()
        self.store = DecisionMarkdownStore()
        self.orders = LiveOrderService()
        self.portfolios = LivePortfolioSnapshotService()
        self.sizer = PositionSizer()
        self.risk = RiskGuard()
        self.upbit_market = UpbitMarketDataAdapter()
        self.toss_market = TossMarketDataAdapter()
        self.upbit_universe = UpbitUniverseService()
        self.toss_universe = TossUniverseService()
        self.audit = AuditLogger()
        self.metrics = CycleMetricsStore()

    async def run(self) -> LiveAutoCycleResponse:
        gate_reasons = self._gate_reasons()
        if gate_reasons:
            return LiveAutoCycleResponse(
                status="blocked",
                reason=" | ".join(gate_reasons),
            )

        instruments = []
        account_snapshot: dict = {}
        portfolio_by_market = {}

        if self.config.upbit_live_order_enabled:
            markets = self.upbit_universe.get()
            if markets:
                try:
                    crypto = await self.upbit_market.snapshots(
                        markets,
                        with_features=True,
                    )
                    if len(crypto) != len(set(markets)):
                        raise RuntimeError(
                            "Incomplete Upbit market snapshot."
                        )
                    instruments.extend(crypto)
                    portfolio = await self.portfolios.upbit()
                    portfolio_by_market["crypto"] = portfolio
                    account_snapshot["crypto"] = {
                        "broker": "upbit",
                        "cash": str(portfolio.cash),
                        "equity": str(portfolio.equity),
                        "daily_pnl_pct": str(portfolio.daily_pnl_pct),
                        "daily_order_count": portfolio.daily_order_count,
                        "positions": [
                            p.model_dump(mode="json")
                            for p in portfolio.positions
                        ],
                    }
                except Exception as exc:
                    self.audit.write(
                        "system",
                        {
                            "event": "live_auto_upbit_snapshot_failed",
                            "reason": str(exc),
                        },
                    )

        if self.config.toss_live_order_enabled:
            symbols = self.toss_universe.get()
            if symbols:
                try:
                    stocks = await self.toss_market.snapshots(
                        symbols,
                        with_features=True,
                    )
                    if len(stocks) != len(set(symbols)):
                        raise RuntimeError(
                            "Incomplete Toss market snapshot."
                        )
                    # Do not spend LLM tokens on stock candidates when every
                    # selected stock is outside a tradable KRX/NXT session.
                    tradable = [
                        item
                        for item in stocks
                        if item.market_open
                    ]
                    if tradable:
                        instruments.extend(tradable)
                        portfolio = await self.portfolios.toss()
                        portfolio_by_market["stock"] = portfolio
                        account_snapshot["stock"] = {
                            "broker": "toss",
                            "cash": str(portfolio.cash),
                            "equity": str(portfolio.equity),
                            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
                            "daily_order_count": portfolio.daily_order_count,
                            "positions": [
                                p.model_dump(mode="json")
                                for p in portfolio.positions
                            ],
                        }
                except Exception as exc:
                    self.audit.write(
                        "system",
                        {
                            "event": "live_auto_toss_snapshot_failed",
                            "reason": str(exc),
                        },
                    )

        if not instruments:
            return LiveAutoCycleResponse(
                status="blocked",
                reason=(
                    "No enabled broker has a complete tradable market "
                    "snapshot and live portfolio."
                ),
            )

        market_snapshot = {
            "instruments": [
                item.model_dump(mode="json")
                for item in instruments
            ]
        }
        account_snapshot["portfolio_policy"] = {
            "accounts_are_separate": True,
            "max_open_positions_total": self.config.risk_max_open_positions,
            "minimum_open_positions": 0,
            "all_cash_allowed": True,
        }

        preview = await self.decisions.preview(
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )
        if preview.status != "completed" or preview.result is None:
            return LiveAutoCycleResponse(
                status="blocked",
                reason=preview.reason or "LLM decision unavailable.",
            )

        result = preview.result
        instrument_map = {
            (item.market, item.symbol): item
            for item in instruments
        }
        total_open_positions = sum(
            len(portfolio.positions)
            for portfolio in portfolio_by_market.values()
        )
        seen: set[tuple[str, str]] = set()
        items: list[LiveCycleExecutionItem] = []

        for decision in result.decisions:
            key = (decision.market, decision.symbol)
            instrument = instrument_map.get(key)
            portfolio = portfolio_by_market.get(decision.market)

            if instrument is None or portfolio is None:
                items.append(
                    LiveCycleExecutionItem(
                        decision=decision,
                        sizing=self._no_order(
                            decision,
                            "No complete live broker snapshot for this decision.",
                        ),
                        risk=RiskGuardResult(
                            status="BLOCK",
                            symbol=decision.symbol,
                            action=decision.action,
                            reasons=[
                                "No complete live broker snapshot."
                            ],
                        ),
                    )
                )
                continue

            sizing = self.sizer.size(
                decision=decision,
                instrument=instrument,
                portfolio=portfolio,
            )
            if sizing.status == "NO_ORDER":
                items.append(
                    LiveCycleExecutionItem(
                        decision=decision,
                        sizing=sizing,
                        risk=RiskGuardResult(
                            status="NO_ORDER",
                            symbol=decision.symbol,
                            action=decision.action,
                            reasons=[sizing.reason],
                        ),
                    )
                )
                continue

            position = next(
                (
                    p
                    for p in portfolio.positions
                    if p.symbol == decision.symbol
                ),
                None,
            )
            preliminary = self.risk.evaluate(
                RiskOrderIntent(
                    source="auto",
                    market=decision.market,
                    symbol=decision.symbol,
                    action=decision.action,
                    order_notional=sizing.order_notional,
                    order_quantity=sizing.order_quantity,
                    price=instrument.price,
                    portfolio_equity=portfolio.equity,
                    available_cash=portfolio.cash,
                    position_value=(
                        position.market_value
                        if position is not None
                        else Decimal("0")
                    ),
                    position_quantity=(
                        position.quantity
                        if position is not None
                        else Decimal("0")
                    ),
                    open_position_count=total_open_positions,
                    daily_pnl_pct=portfolio.daily_pnl_pct,
                    daily_order_count=portfolio.daily_order_count,
                    data_age_seconds=instrument.data_age_seconds,
                    market_open=instrument.market_open,
                    same_cycle_duplicate=key in seen,
                )
            )
            seen.add(key)

            if preliminary.status != "PASS":
                items.append(
                    LiveCycleExecutionItem(
                        decision=decision,
                        sizing=sizing,
                        risk=preliminary,
                    )
                )
                continue

            try:
                order = await self.orders.auto_order(
                    market=decision.market,
                    symbol=decision.symbol,
                    side=(
                        "buy"
                        if decision.action == "BUY"
                        else "sell"
                    ),
                    quantity=sizing.order_quantity,
                    notional=sizing.order_notional,
                )
                message = (
                    f"Live order submitted: {order.order_id}"
                )
            except HTTPException as exc:
                message = str(exc.detail)
                items.append(
                    LiveCycleExecutionItem(
                        decision=decision,
                        sizing=sizing,
                        risk=RiskGuardResult(
                            status="BLOCK",
                            symbol=decision.symbol,
                            action=decision.action,
                            reasons=[message],
                        ),
                        message=message,
                    )
                )
                continue

            items.append(
                LiveCycleExecutionItem(
                    decision=decision,
                    sizing=sizing,
                    risk=preliminary,
                    message=message,
                )
            )

        self.store.append_live_execution_cycle(
            result,
            items,
        )

        submitted_count = sum(
            1
            for item in items
            if item.message
            and item.message.startswith("Live order submitted")
        )
        blocked_count = sum(
            1
            for item in items
            if item.risk is not None
            and item.risk.status == "BLOCK"
        )
        self.metrics.append(
            mode="live",
            accounts={
                market: {
                    "equity": str(portfolio.equity),
                    "cash": str(portfolio.cash),
                    "daily_pnl_pct": str(portfolio.daily_pnl_pct),
                    "position_count": len(portfolio.positions),
                }
                for market, portfolio in portfolio_by_market.items()
            },
            decision_count=len(result.decisions),
            order_count=submitted_count,
            blocked_count=blocked_count,
            next_check_minutes=result.next_check_minutes,
        )

        self.audit.write(
            "system",
            {
                "event": "live_auto_cycle_completed",
                "decision_count": len(result.decisions),
                "submitted_count": submitted_count,
                "next_check_minutes": result.next_check_minutes,
            },
        )

        return LiveAutoCycleResponse(
            status="completed",
            next_check_minutes=result.next_check_minutes,
            cycle_summary=result.cycle_summary,
            items=items,
        )

    def _gate_reasons(self) -> list[str]:
        runtime = self.runtime.get()
        reasons: list[str] = []

        if runtime.mode != "live":
            reasons.append("Runtime mode is not live.")
        if runtime.kill_switch:
            reasons.append("Kill switch is enabled.")
        if not self.config.trading_enabled:
            reasons.append("TRADING_ENABLED=false.")
        if not self.config.live_auto_order_enabled:
            reasons.append("LIVE_AUTO_ORDER_ENABLED=false.")
        if not (
            self.config.upbit_live_order_enabled
            or self.config.toss_live_order_enabled
        ):
            reasons.append(
                "No broker live-order gate is enabled."
            )
        return reasons

    @staticmethod
    def _no_order(decision, reason: str) -> PositionSizeResult:
        return PositionSizeResult(
            status="NO_ORDER",
            market=decision.market,
            symbol=decision.symbol,
            action=decision.action,
            score=decision.score,
            reason=reason,
        )
