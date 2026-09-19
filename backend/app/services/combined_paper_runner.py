from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)
from backend.app.models.schemas import PaperCycleResponse
from backend.app.services.audit import AuditLogger
from backend.app.services.paper_auto_cycle import PaperAutoCycleService
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.upbit_universe import UpbitUniverseService
from backend.app.services.decision_universe import merge_decision_universe


class CombinedPaperRunner:
    """Run stock + crypto as one LLM decision cycle.

    Market-data failures are isolated by broker. A failed broker contributes
    no snapshots and therefore cannot create new orders in that market.
    """

    def __init__(self):
        self.paper_cycle = PaperAutoCycleService()
        self.upbit = UpbitMarketDataAdapter()
        self.toss = TossMarketDataAdapter()
        self.upbit_universe = UpbitUniverseService()
        self.toss_universe = TossUniverseService()
        self.audit = AuditLogger()

    async def run(self) -> PaperCycleResponse:
        snapshots = []
        failures: list[str] = []

        portfolios = self.paper_cycle._portfolios()
        upbit_markets = merge_decision_universe(
            self.upbit_universe.get(),
            [
                position.symbol
                for position in portfolios["crypto"].positions
            ],
        )
        if upbit_markets:
            try:
                crypto = await self.upbit.snapshots(
                    upbit_markets,
                    with_features=True,
                )
                requested = set(upbit_markets)
                received = {
                    item.symbol
                    for item in crypto
                }
                missing = sorted(requested - received)
                if missing:
                    failures.append(
                        "Upbit missing: " + ", ".join(missing)
                    )
                else:
                    snapshots.extend(crypto)
            except (UpbitMarketDataError, ValueError) as exc:
                failures.append(f"Upbit: {exc}")

        toss_symbols = merge_decision_universe(
            self.toss_universe.get(),
            [
                position.symbol
                for position in portfolios["stock"].positions
            ],
        )
        if toss_symbols:
            if not self.toss.configured:
                failures.append(
                    "Toss: Open API credentials are not configured."
                )
            else:
                try:
                    stock = await self.toss.snapshots(
                        toss_symbols,
                        with_features=True,
                    )
                    requested = set(toss_symbols)
                    received = {
                        item.symbol
                        for item in stock
                    }
                    missing = sorted(requested - received)
                    if missing:
                        failures.append(
                            "Toss missing/inactive: "
                            + ", ".join(missing)
                        )
                    else:
                        # Outside every tradable KR session there is no reason
                        # to spend LLM tokens on a stock-only decision.
                        if any(
                            item.market_open
                            for item in stock
                        ):
                            snapshots.extend(stock)
                        else:
                            self.audit.write(
                                "system",
                                {
                                    "event": "toss_cycle_skipped_market_closed",
                                    "symbols": toss_symbols,
                                },
                            )
                except (TossApiError, ValueError) as exc:
                    failures.append(f"Toss: {exc}")

        if failures:
            self.audit.write(
                "system",
                {
                    "event": "combined_market_data_partial_failure",
                    "failures": failures,
                },
            )

        if not snapshots:
            reason = (
                "; ".join(failures)
                if failures
                else (
                    "No active decision universe or every selected "
                    "stock market is currently closed."
                )
            )
            return PaperCycleResponse(
                status="blocked",
                reason=reason,
                portfolios=portfolios,
            )

        result = await self.paper_cycle.run(
            instruments=snapshots
        )

        self.audit.write(
            "system",
            {
                "event": "combined_paper_runner_completed",
                "status": result.status,
                "stock_snapshot_count": sum(
                    1
                    for item in snapshots
                    if item.market == "stock"
                ),
                "crypto_snapshot_count": sum(
                    1
                    for item in snapshots
                    if item.market == "crypto"
                ),
                "partial_failures": failures,
                "next_check_minutes": result.next_check_minutes,
            },
        )
        return result
