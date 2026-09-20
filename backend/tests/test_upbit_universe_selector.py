import asyncio
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.upbit_universe_selector import UpbitUniverseSelector


class _Universe:
    def __init__(self):
        self.saved = []
        self.mode = "manual"
        self.limit = 10

    def get(self):
        return list(self.saved)

    def selection_mode(self):
        return self.mode

    def auto_limit(self):
        return self.limit

    def set_auto(self, markets, *, limit):
        self.saved = list(markets)
        self.mode = "auto"
        self.limit = limit
        return list(self.saved)


class _MarketData:
    async def list_markets(self, *, quote_currency, details):
        assert quote_currency == "KRW"
        assert details is True
        return [
            SimpleNamespace(market="KRW-BTC", warning=False, caution=False),
            SimpleNamespace(market="KRW-ETH", warning=False, caution=False),
            SimpleNamespace(market="KRW-XRP", warning=False, caution=False),
            SimpleNamespace(market="KRW-USDT", warning=False, caution=False),
            SimpleNamespace(market="KRW-WARN", warning=True, caution=False),
            SimpleNamespace(market="KRW-CAUTION", warning=False, caution=True),
        ]

    async def quotes(self, markets):
        assert markets == ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        values = {
            "KRW-BTC": Decimal("300"),
            "KRW-ETH": Decimal("200"),
            "KRW-XRP": Decimal("100"),
        }
        return [
            SimpleNamespace(
                market=market,
                acc_trade_price_24h=values[market],
            )
            for market in markets
        ]

    async def daily_candles(self, market, *, count=64):
        assert count == 64
        configs = {
            "KRW-BTC": (100.0, 0.001),
            "KRW-ETH": (100.0, 0.006),
            "KRW-XRP": (100.0, -0.002),
        }
        price, drift = configs[market]
        rows = []
        for index in range(64):
            open_price = price
            close = open_price * (1.0 + drift)
            rows.append(
                {
                    "timestamp": f"{index:03d}",
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "volume": 1000 + index * 20,
                }
            )
            price = close
        return rows


def test_selector_excludes_risky_stablecoin_and_uses_momentum(tmp_path):
    universe = _Universe()
    selector = UpbitUniverseSelector(
        market_data=_MarketData(),
        universe=universe,
    )
    selector.state_path = tmp_path / "upbit_selector.json"

    selected = asyncio.run(
        selector.select(limit=2, force=True)
    )

    assert len(selected) == 2
    assert "KRW-USDT" not in selected
    assert "KRW-WARN" not in selected
    assert "KRW-CAUTION" not in selected
    assert "KRW-ETH" in selected
    assert universe.mode == "auto"
    assert universe.limit == 2

    payload = selector.state_path.read_text(encoding="utf-8")
    assert "momentum_21d_score" in payload
    assert "liquidity_score" in payload


def test_refresh_if_auto_preserves_manual_selection():
    universe = _Universe()
    universe.saved = ["KRW-BTC"]
    universe.mode = "manual"
    selector = UpbitUniverseSelector(
        market_data=_MarketData(),
        universe=universe,
    )

    selected = asyncio.run(selector.refresh_if_auto())

    assert selected == ["KRW-BTC"]
