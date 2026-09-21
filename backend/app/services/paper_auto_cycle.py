from decimal import Decimal

from backend.app.models.schemas import (
    CycleExecutionItem,
    MarketInstrumentSnapshot,
    PaperCycleResponse,
    PositionSizeResult,
    RiskGuardResult,
    RiskOrderIntent,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.decision_cycle import DecisionCycleService
from backend.app.services.decision_store import DecisionMarkdownStore
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.position_sizer import PositionSizer
from backend.app.services.push import PushService
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.cycle_metrics import CycleMetricsStore
from backend.app.services.auto_trade_activity import AutoTradeActivityService


class PaperAutoCycleService:
    """LLM -> Position Sizer -> Risk Guard -> separated Paper accounts.

    Stocks and crypto use different account equity/cash, matching
    Toss (stocks) and Upbit (crypto). Live brokers are never called here.
    """

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.decisions = DecisionCycleService()
        self.store = DecisionMarkdownStore()
        self.brokers = {
            "stock": PaperBroker("stock"),
            "crypto": PaperBroker("crypto"),
        }
        self.sizer = PositionSizer()
        self.risk = RiskGuard()
        self.audit = AuditLogger()
        self.push = PushService()
        self.metrics = CycleMetricsStore()
        self.auto_activity = AutoTradeActivityService()

    def _portfolios(self) -> dict:
        return {
            market: broker.portfolio()
            for market, broker in self.brokers.items()
        }

    def _total_open_positions(self) -> int:
        return sum(
            len(broker.portfolio().positions)
            for broker in self.brokers.values()
        )

    async def run(
        self,
        *,
        instruments: list[MarketInstrumentSnapshot],
    ) -> PaperCycleResponse:
        runtime = self.runtime.get()

        if runtime.mode != "paper":
            return PaperCycleResponse(
                status="blocked",
                reason="Paper auto cycle only runs in Paper mode.",
            )

        if runtime.kill_switch:
            return PaperCycleResponse(
                status="blocked",
                reason="Kill switch is enabled.",
                portfolios=self._portfolios(),
            )

        if not instruments:
            return PaperCycleResponse(
                status="blocked",
                reason="No market instruments supplied.",
                portfolios=self._portfolios(),
            )

        for broker in self.brokers.values():
            broker.update_prices(instruments)

        account_snapshot = {
            "stock": self.brokers["stock"].account_snapshot(),
            "crypto": self.brokers["crypto"].account_snapshot(),
            "portfolio_policy": {
                "accounts_are_separate": True,
                "max_open_positions_total": self.risk.config.risk_max_open_positions,
                "minimum_open_positions": 0,
                "all_cash_allowed": True,
            },
        }
        market_snapshot = {
            "instruments": [
                instrument.model_dump(mode="json")
                for instrument in instruments
            ]
        }

        preview = await self.decisions.preview(
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )
        if preview.status != "completed" or preview.result is None:
            return PaperCycleResponse(
                status="blocked",
                reason=preview.reason or "Decision cycle unavailable.",
                portfolios=self._portfolios(),
            )

        result = preview.result
        by_key = {
            (instrument.market, instrument.symbol): instrument
            for instrument in instruments
        }
        seen: set[tuple[str, str]] = set()
        items: list[CycleExecutionItem] = []

        for decision in result.decisions:
            key = (decision.market, decision.symbol)
            instrument = by_key.get(key)

            if instrument is None:
                items.append(
                    CycleExecutionItem(
                        decision=decision,
                        sizing=PositionSizeResult(
                            status="NO_ORDER",
                            market=decision.market,
                            symbol=decision.symbol,
                            action=decision.action,
                            score=decision.score,
                            reason=(
                                "Decision symbol is missing from the supplied "
                                "market snapshot."
                            ),
                        ),
                        risk=RiskGuardResult(
                            status="BLOCK",
                            symbol=decision.symbol,
                            action=decision.action,
                            reasons=[
                                "Missing market snapshot for decision symbol."
                            ],
                        ),
                    )
                )
                continue

            broker = self.brokers[decision.market]
            portfolio = broker.portfolio()
            sizing = self.sizer.size(
                decision=decision,
                instrument=instrument,
                portfolio=portfolio,
            )

            if sizing.status == "NO_ORDER":
                items.append(
                    CycleExecutionItem(
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
                seen.add(key)
                continue

            current_position = broker.position(decision.symbol)

            intent = RiskOrderIntent(
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
                    current_position.market_value
                    if current_position is not None
                    else Decimal("0")
                ),
                position_quantity=(
                    current_position.quantity
                    if current_position is not None
                    else Decimal("0")
                ),
                open_position_count=self._total_open_positions(),
                daily_pnl_pct=portfolio.daily_pnl_pct,
                daily_order_count=portfolio.daily_order_count,
                data_age_seconds=instrument.data_age_seconds,
                market_open=instrument.market_open,
                same_cycle_duplicate=key in seen,
                seconds_since_last_auto_order=(
                    self.auto_activity.seconds_since_last(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                    )
                ),
                seconds_since_last_buy=(
                    self.auto_activity.seconds_since_last(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                        side="buy",
                    )
                ),
                seconds_since_last_sell=(
                    self.auto_activity.seconds_since_last(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                        side="sell",
                    )
                ),
                seconds_since_last_stop_exit=(
                    self.auto_activity.seconds_since_last(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                        event="stop_exit",
                    )
                ),
            )
            risk_result = self.risk.evaluate(intent)
            seen.add(key)

            order = None
            if risk_result.status in {"ALLOW", "REDUCE"}:
                effective_quantity = (
                    risk_result.adjusted_quantity
                    if risk_result.status == "REDUCE"
                    else sizing.order_quantity
                )
                try:
                    order = broker.execute(
                        symbol=decision.symbol,
                        name=decision.name or instrument.name,
                        side=(
                            "buy"
                            if decision.action == "BUY"
                            else "sell"
                        ),
                        quantity=effective_quantity,
                        market_price=instrument.price,
                        decision_score=decision.score,
                        decision_reason=decision.reason,
                        source="auto",
                        market_open=instrument.market_open,
                    )
                    order_side = (
                        "buy"
                        if decision.action == "BUY"
                        else "sell"
                    )
                    self.auto_activity.record(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                        at=order.created_at,
                    )
                    self.auto_activity.record(
                        mode="paper",
                        market=decision.market,
                        symbol=decision.symbol,
                        side=order_side,
                        at=order.created_at,
                    )
                except ValueError as exc:
                    risk_result = RiskGuardResult(
                        status="BLOCK",
                        symbol=decision.symbol,
                        action=decision.action,
                        reasons=[
                            f"Paper broker rejected order: {exc}"
                        ],
                    )

            if risk_result.status == "BLOCK":
                self.push.send(
                    title="Risk Guard 차단",
                    body=f"{decision.symbol} {decision.action}",
                    data={
                        "type": "risk_block",
                        "symbol": decision.symbol,
                        "action": decision.action,
                    },
                )

            items.append(
                CycleExecutionItem(
                    decision=decision,
                    sizing=sizing,
                    risk=risk_result,
                    order=order,
                )
            )

        self.store.append_execution_cycle(result, items)
        portfolios = self._portfolios()

        order_count = sum(
            1
            for item in items
            if item.order is not None
        )
        blocked_count = sum(
            1
            for item in items
            if item.risk is not None
            and item.risk.status == "BLOCK"
        )

        self.metrics.append(
            mode="paper",
            accounts={
                market: {
                    "equity": str(portfolio.equity),
                    "cash": str(portfolio.cash),
                    "daily_pnl_pct": str(portfolio.daily_pnl_pct),
                    "position_count": len(portfolio.positions),
                }
                for market, portfolio in portfolios.items()
            },
            decision_count=len(result.decisions),
            order_count=order_count,
            blocked_count=blocked_count,
            next_check_minutes=result.next_check_minutes,
        )

        self.audit.write(
            "system",
            {
                "event": "paper_auto_cycle_completed",
                "decision_count": len(result.decisions),
                "order_count": sum(
                    1 for item in items if item.order is not None
                ),
                "blocked_count": sum(
                    1
                    for item in items
                    if item.risk is not None
                    and item.risk.status == "BLOCK"
                ),
                "open_position_count": self._total_open_positions(),
                "next_check_minutes": result.next_check_minutes,
                "stock_equity": str(portfolios["stock"].equity),
                "crypto_equity": str(portfolios["crypto"].equity),
            },
        )

        return PaperCycleResponse(
            status="completed",
            next_check_minutes=result.next_check_minutes,
            cycle_summary=result.cycle_summary,
            items=items,
            portfolios=portfolios,
        )
