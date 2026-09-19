from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.services.upbit_universe import UpbitUniverseService


class UpbitUniverseSelector:
    """Build a liquid, read-only Upbit KRW decision universe."""

    def __init__(
        self,
        market_data: UpbitMarketDataAdapter | None = None,
        universe: UpbitUniverseService | None = None,
    ):
        self.market_data = market_data or UpbitMarketDataAdapter()
        self.universe = universe or UpbitUniverseService()

    async def select(self, *, limit: int = 10) -> list[str]:
        limit = max(1, min(limit, 50))
        markets = await self.market_data.list_markets(
            quote_currency="KRW",
            details=True,
        )
        eligible = [
            item.market
            for item in markets
            if not item.warning
            and not item.caution
            and item.market != "KRW-USDT"
        ]
        quotes = await self.market_data.quotes(eligible)
        ranked = sorted(
            quotes,
            key=lambda item: item.acc_trade_price_24h or 0,
            reverse=True,
        )
        selected = [
            item.market
            for item in ranked
            if item.acc_trade_price_24h is not None
            and item.acc_trade_price_24h > 0
        ][:limit]
        return self.universe.set(selected)
