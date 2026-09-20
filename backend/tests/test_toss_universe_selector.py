import asyncio
from types import SimpleNamespace

from backend.app.services.toss_universe_selector import TossUniverseSelector


class _Universe:
    def __init__(self):
        self.symbols = ["005930"]
        self.mode = "manual"
        self.limit = 15

    def get(self):
        return list(self.symbols)

    def selection_mode(self):
        return self.mode

    def auto_limit(self):
        return self.limit

    def set_auto(self, symbols, *, limit):
        self.symbols = list(symbols)
        self.mode = "auto"
        self.limit = limit
        return list(self.symbols)


class _MarketData:
    async def stock_info(self, symbols):
        wanted = {"005930", "000660", "035420", "035720"}
        return [
            SimpleNamespace(
                symbol=symbol,
                name=symbol,
                status="ACTIVE",
                currency="KRW",
                security_type="STOCK",
                trading_suspended=False,
                market="KOSPI",
            )
            for symbol in symbols
            if symbol in wanted
        ]

    async def candles(self, symbol, *, interval, count):
        assert interval == "1d"
        assert count == 91
        configs = {
            "005930": (70000, 2000000, 0.002),
            "000660": (180000, 1200000, 0.004),
            "035420": (220000, 250000, 0.001),
            # Strong but blow-off move: selector should penalize it.
            "035720": (50000, 400000, 0.020),
        }
        base, volume, drift = configs[symbol]
        rows = []
        price = float(base)
        for index in range(91):
            price *= 1 + drift
            rows.append(
                {
                    "timestamp": f"2026-07-{index + 1:02d}",
                    "open": price * 0.995,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "volume": volume * (1 + index / 200),
                }
            )
        return rows


def test_stock_selector_builds_auto_universe_from_objective_metrics(tmp_path):
    universe = _Universe()
    selector = TossUniverseSelector(
        market_data=_MarketData(),
        universe=universe,
    )
    selector.state_path = tmp_path / "selector.json"

    selected = asyncio.run(selector.select(limit=3, force=True))

    assert len(selected) == 3
    assert universe.mode == "auto"
    assert universe.limit == 3
    assert "005930" in selected
    assert "000660" in selected
    status = selector.status()
    assert status["selection_mode"] == "auto"
    selected_rows = [
        item
        for item in status["ranking"]
        if item["selected"]
    ]
    assert len(selected_rows) == 3
    assert selected_rows[0]["rank"] == 1
    assert 0 <= selected_rows[0]["liquidity_score"] <= 100
    assert 0 <= selected_rows[0]["sign_60d_score"] <= 100
    assert 0 <= selected_rows[0]["momentum_20d_score"] <= 100
    assert 0 <= selected_rows[0]["activity_score"] <= 100
    assert "penalty_reasons" in selected_rows[0]


def test_metrics_reject_insufficient_history():
    assert TossUniverseSelector._metrics(
        [
            {
                "timestamp": "2026-09-01",
                "close": 100,
                "volume": 1000,
            }
        ]
    ) is None
