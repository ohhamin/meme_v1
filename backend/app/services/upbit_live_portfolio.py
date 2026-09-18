from decimal import Decimal

from backend.app.brokers.upbit_account import (
    UpbitAccountAdapter,
    UpbitAccountError,
)
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)


class UpbitLivePortfolioService:
    """Build a read-only live portfolio view from Upbit balances + quotes."""

    def __init__(self):
        self.accounts = UpbitAccountAdapter()
        self.market_data = UpbitMarketDataAdapter()

    async def positions(self) -> list[dict]:
        status = await self.accounts.balances()

        if not status.configured:
            raise UpbitAccountError(
                "Upbit API keys are not configured."
            )

        assets = [
            asset
            for asset in status.assets
            if asset.currency != "KRW"
            and asset.total > 0
            and asset.unit_currency == "KRW"
        ]

        if not assets:
            return []

        markets = [
            f"KRW-{asset.currency}"
            for asset in assets
        ]

        try:
            quotes = await self.market_data.quotes(markets)
        except UpbitMarketDataError:
            quotes = []

        quote_map = {
            quote.market: quote
            for quote in quotes
        }

        positions: list[dict] = []
        for asset in assets:
            market = f"KRW-{asset.currency}"
            quote = quote_map.get(market)
            current_price = (
                quote.trade_price
                if quote is not None
                else Decimal("0")
            )

            invested = asset.total * asset.avg_buy_price
            market_value = asset.total * current_price

            if asset.avg_buy_price > 0 and current_price > 0:
                return_rate = (
                    (current_price - asset.avg_buy_price)
                    / asset.avg_buy_price
                    * Decimal("100")
                )
            else:
                return_rate = Decimal("0")

            positions.append(
                {
                    "symbol": market,
                    "name": (
                        quote.korean_name
                        if quote is not None
                        and quote.korean_name
                        else asset.currency
                    ),
                    "invested_amount": invested,
                    "quantity": asset.total,
                    "return_rate": return_rate,
                    "decision_score": None,
                    "current_price": current_price,
                    "market_value": market_value,
                    "source": "upbit_live",
                }
            )

        return positions
