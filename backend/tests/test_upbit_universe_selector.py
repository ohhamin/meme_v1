import asyncio
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.upbit_universe_selector import UpbitUniverseSelector


class _Universe:
    def __init__(self):
        self.saved = []

    def set(self, markets):
        self.saved = list(markets)
        return self.saved


class _MarketData:
    async def list_markets(self, *, quote_currency, details):
        assert quote_currency == "KRW"
        assert details is True
        return [
            SimpleNamespace(market="KRW-BTC", warning=False, caution=False),
            SimpleNamespace(market="KRW-ETH", warning=False, caution=False),
            SimpleNamespace(market="KRW-USDT", warning=False, caution=False),
            SimpleNamespace(market="KRW-WARN", warning=True, caution=False),
            SimpleNamespace(market="KRW-CAUTION", warning=False, caution=True),
        ]

    async def quotes(self, markets):
        assert markets == ["KRW-BTC", "KRW-ETH"]
        return [
            SimpleNamespace(market="KRW-BTC", acc_trade_price_24h=Decimal("100")),
            SimpleNamespace(market="KRW-ETH", acc_trade_price_24h=Decimal("200")),
        ]


def test_selector_excludes_risky_and_stablecoin_then_ranks_by_turnover():
    universe = _Universe()
    selector = UpbitUniverseSelector(
        market_data=_MarketData(),
        universe=universe,
    )

    selected = asyncio.run(selector.select(limit=2))

    assert selected == ["KRW-ETH", "KRW-BTC"]
    assert universe.saved == selected
