from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.models.schemas import PaperCycleResponse
from backend.app.services.audit import AuditLogger
from backend.app.services.paper_auto_cycle import PaperAutoCycleService
from backend.app.services.toss_universe import TossUniverseService


class TossPaperRunner:
    """Fetch Toss Korean stock quotes and run the stock Paper cycle."""

    def __init__(self):
        self.market_data = TossMarketDataAdapter()
        self.paper_cycle = PaperAutoCycleService()
        self.universe = TossUniverseService()
        self.audit = AuditLogger()

    async def run(
        self,
        symbols: list[str] | None = None,
    ) -> PaperCycleResponse:
        selected = (
            symbols
            if symbols is not None
            else self.universe.get()
        )

        if not selected:
            return PaperCycleResponse(
                status="blocked",
                reason=(
                    "No Toss stock decision symbols configured. "
                    "Choose symbols in the app or set TOSS_DECISION_SYMBOLS."
                ),
                portfolios=self.paper_cycle._portfolios(),
            )

        if not self.market_data.configured:
            return PaperCycleResponse(
                status="blocked",
                reason="Toss Open API credentials are not configured.",
                portfolios=self.paper_cycle._portfolios(),
            )

        try:
            snapshots = await self.market_data.snapshots(
                selected
            )
        except (TossApiError, ValueError) as exc:
            self.audit.write(
                "system",
                {
                    "event": "toss_market_data_failed",
                    "reason": str(exc),
                    "symbols": selected,
                },
            )
            return PaperCycleResponse(
                status="blocked",
                reason=str(exc),
                portfolios=self.paper_cycle._portfolios(),
            )

        requested = {
            value.strip().upper()
            for value in selected
        }
        received = {
            snapshot.symbol
            for snapshot in snapshots
        }
        missing = sorted(requested - received)

        if missing:
            reason = (
                "Toss did not return all requested active Korean symbols: "
                + ", ".join(missing)
            )
            self.audit.write(
                "system",
                {
                    "event": "toss_market_data_incomplete",
                    "missing": missing,
                },
            )
            return PaperCycleResponse(
                status="blocked",
                reason=reason,
                portfolios=self.paper_cycle._portfolios(),
            )

        result = await self.paper_cycle.run(
            instruments=snapshots,
        )
        self.audit.write(
            "system",
            {
                "event": "toss_paper_runner_completed",
                "symbols": selected,
                "status": result.status,
                "next_check_minutes": result.next_check_minutes,
            },
        )
        return result
