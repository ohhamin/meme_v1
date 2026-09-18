import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter


def test_list_markets_filters_krw_and_reads_warning(monkeypatch):
    adapter = UpbitMarketDataAdapter()

    async def fake_get(path, *, params):
        assert path == "/market/all"
        return [
            {
                "market": "KRW-BTC",
                "korean_name": "비트코인",
                "english_name": "Bitcoin",
                "market_event": {
                    "warning": False,
                    "caution": {
                        "PRICE_FLUCTUATIONS": False,
                    },
                },
            },
            {
                "market": "BTC-ETH",
                "korean_name": "이더리움",
                "english_name": "Ethereum",
                "market_event": {
                    "warning": False,
                    "caution": {},
                },
            },
        ]

    monkeypatch.setattr(adapter, "_get", fake_get)
    items = asyncio.run(adapter.list_markets())

    assert len(items) == 1
    assert items[0].market == "KRW-BTC"
    assert items[0].korean_name == "비트코인"
    assert items[0].warning is False


def test_quotes_keep_requested_order_and_calculate_age(monkeypatch):
    adapter = UpbitMarketDataAdapter()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    adapter._market_cache = {
        "KRW-BTC": type(
            "Info",
            (),
            {
                "korean_name": "비트코인",
                "english_name": "Bitcoin",
            },
        )(),
        "KRW-ETH": type(
            "Info",
            (),
            {
                "korean_name": "이더리움",
                "english_name": "Ethereum",
            },
        )(),
    }

    async def fake_get(path, *, params):
        assert path == "/ticker"
        assert params["markets"] == "KRW-ETH,KRW-BTC"
        return [
            {
                "market": "KRW-BTC",
                "trade_price": 100000000,
                "signed_change_rate": 0.01,
                "acc_trade_price_24h": 100000000000,
                "timestamp": now_ms,
            },
            {
                "market": "KRW-ETH",
                "trade_price": 5000000,
                "signed_change_rate": -0.02,
                "acc_trade_price_24h": 50000000000,
                "timestamp": now_ms,
            },
        ]

    monkeypatch.setattr(adapter, "_get", fake_get)
    quotes = asyncio.run(
        adapter.quotes(["KRW-ETH", "KRW-BTC"])
    )

    assert [item.market for item in quotes] == [
        "KRW-ETH",
        "KRW-BTC",
    ]
    assert quotes[0].trade_price == Decimal("5000000")
    assert quotes[0].data_age_seconds <= 2


def test_snapshots_are_crypto_and_use_upbit_pair_symbol(monkeypatch):
    adapter = UpbitMarketDataAdapter()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    adapter._market_cache = {
        "KRW-BTC": type(
            "Info",
            (),
            {
                "korean_name": "비트코인",
                "english_name": "Bitcoin",
            },
        )(),
    }

    async def fake_get(path, *, params):
        return [
            {
                "market": "KRW-BTC",
                "trade_price": 100000000,
                "timestamp": now_ms,
            }
        ]

    monkeypatch.setattr(adapter, "_get", fake_get)
    snapshots = asyncio.run(
        adapter.snapshots(["KRW-BTC"])
    )

    assert len(snapshots) == 1
    assert snapshots[0].market == "crypto"
    assert snapshots[0].symbol == "KRW-BTC"
    assert snapshots[0].name == "비트코인"
    assert snapshots[0].market_open is True


def test_non_krw_market_is_rejected():
    adapter = UpbitMarketDataAdapter()

    try:
        asyncio.run(adapter.quotes(["BTC-ETH"]))
        raised = False
    except ValueError:
        raised = True

    assert raised is True
