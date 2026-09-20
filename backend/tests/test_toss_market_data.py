import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from backend.app.brokers.toss_market_data import TossMarketDataAdapter


def test_toss_quotes_parse_price_and_preserve_order(monkeypatch):
    adapter = TossMarketDataAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/prices"
        assert params["symbols"] == "000660,005930"
        return {
            "result": [
                {
                    "symbol": "005930",
                    "timestamp": "2026-09-19T00:00:00+09:00",
                    "lastPrice": "72000",
                    "currency": "KRW",
                },
                {
                    "symbol": "000660",
                    "timestamp": "2026-09-19T00:00:00+09:00",
                    "lastPrice": "300000",
                    "currency": "KRW",
                },
            ]
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    quotes = asyncio.run(
        adapter.quotes(["000660", "005930"])
    )

    assert [item.symbol for item in quotes] == [
        "000660",
        "005930",
    ]
    assert quotes[0].last_price == Decimal("300000")


def test_toss_stock_info_reads_nxt_and_suspension(monkeypatch):
    adapter = TossMarketDataAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/stocks"
        return {
            "result": [
                {
                    "symbol": "005930",
                    "name": "삼성전자",
                    "englishName": "SamsungElec",
                    "market": "KOSPI",
                    "securityType": "STOCK",
                    "status": "ACTIVE",
                    "currency": "KRW",
                    "koreanMarketDetail": {
                        "nxtSupported": True,
                        "krxTradingSuspended": False,
                        "nxtTradingSuspended": False,
                    },
                }
            ]
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    items = asyncio.run(adapter.stock_info(["005930"]))

    assert len(items) == 1
    assert items[0].nxt_supported is True
    assert items[0].trading_suspended is False


def test_market_calendar_regular_session_is_open(monkeypatch):
    adapter = TossMarketDataAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/market-calendar/KR"
        return {
            "result": {
                "today": {
                    "integrated": {
                        "preMarket": {
                            "startTime": "2026-09-19T08:00:00+09:00",
                            "endTime": "2026-09-19T09:00:00+09:00",
                        },
                        "regularMarket": {
                            "startTime": "2026-09-19T09:00:00+09:00",
                            "endTime": "2026-09-19T15:30:00+09:00",
                        },
                        "afterMarket": {
                            "startTime": "2026-09-19T15:30:00+09:00",
                            "endTime": "2026-09-19T20:00:00+09:00",
                        },
                    }
                }
            }
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    now = datetime.fromisoformat(
        "2026-09-19T10:00:00+09:00"
    )
    opened = asyncio.run(
        adapter.market_is_open(
            nxt_supported=False,
            now=now,
        )
    )

    assert opened is True


def test_non_nxt_stock_is_closed_in_after_market(monkeypatch):
    adapter = TossMarketDataAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        return {
            "result": {
                "today": {
                    "integrated": {
                        "preMarket": None,
                        "regularMarket": {
                            "startTime": "2026-09-19T09:00:00+09:00",
                            "endTime": "2026-09-19T15:30:00+09:00",
                        },
                        "afterMarket": {
                            "startTime": "2026-09-19T15:30:00+09:00",
                            "endTime": "2026-09-19T20:00:00+09:00",
                        },
                    }
                }
            }
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    now = datetime.fromisoformat(
        "2026-09-19T17:00:00+09:00"
    )

    assert asyncio.run(
        adapter.market_is_open(
            nxt_supported=False,
            now=now,
        )
    ) is False
    assert asyncio.run(
        adapter.market_is_open(
            nxt_supported=True,
            now=now,
        )
    ) is True



def test_toss_snapshots_include_daily_quant_features(monkeypatch):
    adapter = TossMarketDataAdapter()

    async def fake_info(symbols):
        return [
            SimpleNamespace(
                symbol="005930",
                name="삼성전자",
                status="ACTIVE",
                nxt_supported=False,
                trading_suspended=False,
            )
        ]

    async def fake_quotes(symbols):
        return [
            SimpleNamespace(
                symbol="005930",
                last_price=Decimal("220"),
                data_age_seconds=1,
            )
        ]

    async def fake_market_is_open(*, nxt_supported, now=None):
        return True

    async def fake_candles(symbol, *, interval="1d", count=91):
        assert symbol == "005930"
        assert interval == "1d"
        assert count == 91
        return [
            {
                "timestamp": f"{index:03d}",
                "open": 99 + index,
                "high": 101 + index,
                "low": 98 + index,
                "close": 100 + index,
                "volume": 1000 + index,
            }
            for index in range(91)
        ]

    monkeypatch.setattr(adapter, "stock_info", fake_info)
    monkeypatch.setattr(adapter, "quotes", fake_quotes)
    monkeypatch.setattr(
        adapter,
        "market_is_open",
        fake_market_is_open,
    )
    monkeypatch.setattr(adapter, "candles", fake_candles)

    snapshots = asyncio.run(
        adapter.snapshots(
            ["005930"],
            with_features=True,
        )
    )

    assert len(snapshots) == 1
    assert snapshots[0].features["features_available"] == 1
    assert snapshots[0].features["feature_interval"] == "1d"
    assert snapshots[0].features["return_long_pct"] is not None
    assert snapshots[0].features["quant_action"] in {"BUY", "HOLD", "SELL"}
    assert 0 <= snapshots[0].features["quant_score"] <= 100
