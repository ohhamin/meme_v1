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


class PaperAutoCycleService:
    """LLM -> Position Sizer -> Risk Guard -> Paper Broker.

    This is the first end-to-end automatic trading path.
    It never calls a live broker.
    """

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.decisions = DecisionCycleService()
        self.store = DecisionMarkdownStore()
        self.broker = PaperBroker()
        self.sizer = PositionSizer()
        self.risk = RiskGuard()
        self.audit = AuditLogger()
        self.push = PushService()

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

        # Save LLM tokens: when no automatic order can possibly pass, do not call the LLM.
        if runtime.kill_switch:
            return PaperCycleResponse(
                status="blocked",
                reason="Kill switch is enabled.",
                portfolio=self.broker.portfolio(),
            )

        if not instruments:
            return PaperCycleResponse(
                status="blocked",
                reason="No market instruments supplied.",
                portfolio=self.broker.portfolio(),
            )

        self.broker.update_prices(instruments)
        account_snapshot = self.broker.account_snapshot()
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
                portfolio=self.broker.portfolio(),
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
                            reason="Decision symbol is missing from the supplied market snapshot.",
                        ),
                        risk=RiskGuardResult(
                            status="BLOCK",
                            symbol=decision.symbol,
                            action=decision.action,
                            reasons=["Missing market snapshot for decision symbol."],
                        ),
                    )
                )
                continue

            portfolio = self.broker.portfolio()
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

            current_position = next(
                (
                    p
                    for p in portfolio.positions
                    if p.market == decision.market
                    and p.symbol == decision.symbol
                ),
                None,
            )

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
                market_exposure_value=self.broker.market_exposure_value(
                    decision.market
                ),
                daily_pnl_pct=portfolio.daily_pnl_pct,
                daily_order_count=portfolio.daily_order_count,
                data_age_seconds=instrument.data_age_seconds,
                market_open=instrument.market_open,
                same_cycle_duplicate=key in seen,
            )
            risk_result = self.risk.evaluate(intent)
            seen.add(key)

            order = None
            if risk_result.status == "PASS":
                try:
                    order = self.broker.execute(
                        market=decision.market,
                        symbol=decision.symbol,
                        name=decision.name or instrument.name,
                        side="buy" if decision.action == "BUY" else "sell",
                        quantity=sizing.order_quantity,
                        market_price=instrument.price,
                        decision_score=decision.score,
                    )
                except ValueError as exc:
                    risk_result = RiskGuardResult(
                        status="BLOCK",
                        symbol=decision.symbol,
                        action=decision.action,
                        reasons=[f"Paper broker rejected order: {exc}"],
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
        portfolio = self.broker.portfolio()

        self.audit.write(
            "system",
            {
                "event": "paper_auto_cycle_completed",
                "decision_count": len(result.decisions),
                "order_count": sum(1 for item in items if item.order is not None),
                "blocked_count": sum(
                    1
                    for item in items
                    if item.risk is not None and item.risk.status == "BLOCK"
                ),
                "next_check_minutes": result.next_check_minutes,
                "equity": str(portfolio.equity),
                "cash": str(portfolio.cash),
            },
        )

        return PaperCycleResponse(
            status="completed",
            next_check_minutes=result.next_check_minutes,
            cycle_summary=result.cycle_summary,
            items=items,
            portfolio=portfolio,
        )
