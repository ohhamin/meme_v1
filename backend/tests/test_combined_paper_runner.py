import asyncio
from types import SimpleNamespace

from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    PaperCycleResponse,
)
from backend.app.services.combined_paper_runner import CombinedPaperRunner


class _Universe:
    def __init__(self, values):
        self.values = values

    def get(self):
        return list(self.values)


class _MarketData:
    def __init__(self, snapshots, configured=True):
        self._snapshots = snapshots
        self.configured = configured

    async def snapshots(self, values, *, with_features=False):
        assert with_features is True
        return list(self._snapshots)


class _PaperCycle:
    def __init__(
        self,
        *,
        crypto_positions=None,
        stock_positions=None,
    ):
        self.received = None
        self._portfolio_data = {
            "crypto": SimpleNamespace(
                positions=list(crypto_positions or [])
            ),
            "stock": SimpleNamespace(
                positions=list(stock_positions or [])
            ),
        }

    def _portfolios(self):
        return self._portfolio_data

    async def run(self, *, instruments):
        self.received = list(instruments)
        return PaperCycleResponse(
            status="completed",
            next_check_minutes=60,
            cycle_summary="ok",
            items=[],
            portfolios=None,
        )


def test_combined_runner_sends_stock_and_crypto_in_one_cycle():
    runner = CombinedPaperRunner()
    runner.upbit_universe = _Universe(["KRW-BTC"])
    runner.toss_universe = _Universe(["005930"])
    runner.upbit = _MarketData(
        [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol="KRW-BTC",
                name="비트코인",
                price=100000000,
                data_age_seconds=1,
                market_open=True,
            )
        ]
    )
    runner.toss = _MarketData(
        [
            MarketInstrumentSnapshot(
                market="stock",
                symbol="005930",
                name="삼성전자",
                price=70000,
                data_age_seconds=1,
                market_open=True,
            )
        ]
    )
    runner.paper_cycle = _PaperCycle()
    runner.audit.write = lambda *args, **kwargs: None

    result = asyncio.run(runner.run())

    assert result.status == "completed"
    assert runner.paper_cycle.received is not None
    assert {
        (item.market, item.symbol)
        for item in runner.paper_cycle.received
    } == {
        ("crypto", "KRW-BTC"),
        ("stock", "005930"),
    }


def test_closed_stock_market_does_not_block_crypto_cycle():
    runner = CombinedPaperRunner()
    runner.upbit_universe = _Universe(["KRW-BTC"])
    runner.toss_universe = _Universe(["005930"])
    runner.upbit = _MarketData(
        [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol="KRW-BTC",
                name="비트코인",
                price=100000000,
                data_age_seconds=1,
                market_open=True,
            )
        ]
    )
    runner.toss = _MarketData(
        [
            MarketInstrumentSnapshot(
                market="stock",
                symbol="005930",
                name="삼성전자",
                price=70000,
                data_age_seconds=1,
                market_open=False,
            )
        ]
    )
    runner.paper_cycle = _PaperCycle()
    runner.audit.write = lambda *args, **kwargs: None

    result = asyncio.run(runner.run())

    assert result.status == "completed"
    assert len(runner.paper_cycle.received) == 1
    assert runner.paper_cycle.received[0].market == "crypto"



def test_held_crypto_is_evaluated_even_after_watchlist_removal():
    runner = CombinedPaperRunner()
    runner.upbit_universe = _Universe([])
    runner.toss_universe = _Universe([])
    runner.upbit = _MarketData(
        [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol="KRW-BTC",
                name="비트코인",
                price=100000000,
                data_age_seconds=1,
                market_open=True,
            )
        ]
    )
    runner.toss = _MarketData([], configured=False)
    runner.paper_cycle = _PaperCycle(
        crypto_positions=[
            SimpleNamespace(symbol="KRW-BTC")
        ]
    )
    runner.audit.write = lambda *args, **kwargs: None

    result = asyncio.run(runner.run())

    assert result.status == "completed"
    assert runner.paper_cycle.received is not None
    assert [
        item.symbol
        for item in runner.paper_cycle.received
    ] == ["KRW-BTC"]
