from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)
from backend.app.models.schemas import PaperCycleResponse
from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger
from backend.app.services.paper_auto_cycle import PaperAutoCycleService
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.toss_universe_selector import TossUniverseSelector
from backend.app.services.upbit_universe import UpbitUniverseService
from backend.app.services.upbit_universe_selector import UpbitUniverseSelector
from backend.app.services.decision_universe import merge_decision_universe


class CombinedPaperRunner:
    """Run stock + crypto as one LLM decision cycle.

    Market-data failures are isolated by broker. A failed broker contributes
    no snapshots and therefore cannot create new orders in that market.
    """

    def __init__(self):
        self.config = get_settings()
        self.paper_cycle = PaperAutoCycleService()
        self.upbit = UpbitMarketDataAdapter()
        self.toss = TossMarketDataAdapter()
        self.upbit_universe = UpbitUniverseService()
        self.upbit_universe_selector = UpbitUniverseSelector(
            market_data=self.upbit,
            universe=self.upbit_universe,
        )
        self.toss_universe = TossUniverseService()
        self.toss_universe_selector = TossUniverseSelector(
            market_data=self.toss,
            universe=self.toss_universe,
        )
        self.audit = AuditLogger()

    async def run(self) -> PaperCycleResponse:
        snapshots = []
        failures: list[str] = []

        portfolios = self.paper_cycle._portfolios()
        held_crypto = [
            position.symbol
            for position in portfolios["crypto"].positions
        ]
        try:
            upbit_markets = await self.upbit_universe_selector.select(
                limit=self.config.decision_crypto_universe_limit,
                force=True,
                required_markets=held_crypto,
            )
        except (UpbitMarketDataError, ValueError) as exc:
            failures.append(f"Upbit universe refresh: {exc}")
            upbit_markets = merge_decision_universe(
                held_crypto,
                self.upbit_universe.get(),
            )[: self.config.decision_crypto_universe_limit]
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

        held_stocks = [
            position.symbol
            for position in portfolios["stock"].positions
        ]
        try:
            toss_symbols = await self.toss_universe_selector.select(
                limit=self.config.decision_stock_universe_limit,
                force=True,
                required_symbols=held_stocks,
            )
        except (TossApiError, ValueError) as exc:
            failures.append(f"Toss universe refresh: {exc}")
            toss_symbols = merge_decision_universe(
                held_stocks,
                self.toss_universe.get(),
            )[: self.config.decision_stock_universe_limit]
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
