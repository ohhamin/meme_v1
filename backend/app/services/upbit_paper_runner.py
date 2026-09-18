from backend.app.core.config import get_settings
from backend.app.models.schemas import PaperCycleResponse
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.paper_auto_cycle import PaperAutoCycleService
from backend.app.services.upbit_universe import UpbitUniverseService


class UpbitPaperRunner:
    """Fetch public Upbit quotes and run the crypto Paper decision cycle."""

    def __init__(self):
        self.config = get_settings()
        self.market_data = UpbitMarketDataAdapter()
        self.paper_cycle = PaperAutoCycleService()
        self.universe = UpbitUniverseService()
        self.audit = AuditLogger()

    async def run(
        self,
        markets: list[str] | None = None,
    ) -> PaperCycleResponse:
        selected = markets if markets is not None else self.universe.get()

        if not selected:
            return PaperCycleResponse(
                status="blocked",
                reason=(
                    "No Upbit decision markets configured. "
                    "Choose markets in the app or set UPBIT_DECISION_MARKETS."
                ),
                portfolios=self.paper_cycle._portfolios(),
            )

        try:
            snapshots = await self.market_data.snapshots(selected)
        except (UpbitMarketDataError, ValueError) as exc:
            self.audit.write(
                "system",
                {
                    "event": "upbit_market_data_failed",
                    "reason": str(exc),
                    "markets": selected,
                },
            )
            return PaperCycleResponse(
                status="blocked",
                reason=str(exc),
                portfolios=self.paper_cycle._portfolios(),
            )

        requested = {value.strip().upper() for value in selected}
        received = {snapshot.symbol for snapshot in snapshots}
        missing = sorted(requested - received)

        if missing:
            reason = (
                "Upbit did not return all requested markets: "
                + ", ".join(missing)
            )
            self.audit.write(
                "system",
                {
                    "event": "upbit_market_data_incomplete",
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
                "event": "upbit_paper_runner_completed",
                "markets": selected,
                "status": result.status,
                "next_check_minutes": result.next_check_minutes,
            },
        )
        return result
