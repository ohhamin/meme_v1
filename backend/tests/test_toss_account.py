import asyncio
from decimal import Decimal

from backend.app.brokers.toss_account import TossAccountAdapter


def test_toss_holdings_filter_korean_and_convert_rate(monkeypatch):
    adapter = TossAccountAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/holdings"
        assert account_seq == 1
        return {
            "result": {
                "items": [
                    {
                        "symbol": "005930",
                        "name": "삼성전자",
                        "marketCountry": "KR",
                        "currency": "KRW",
                        "quantity": "10",
                        "lastPrice": "72000",
                        "averagePurchasePrice": "65000",
                        "marketValue": {
                            "purchaseAmount": "650000",
                            "amount": "720000",
                        },
                        "profitLoss": {
                            "rate": "0.1077",
                        },
                    },
                    {
                        "symbol": "AAPL",
                        "name": "Apple",
                        "marketCountry": "US",
                        "currency": "USD",
                        "quantity": "1",
                        "lastPrice": "200",
                        "averagePurchasePrice": "180",
                        "marketValue": {
                            "purchaseAmount": "180",
                            "amount": "200",
                        },
                        "profitLoss": {
                            "rate": "0.1111",
                        },
                    },
                ]
            }
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    items = asyncio.run(
        adapter.holdings(account_seq=1)
    )

    assert len(items) == 1
    assert items[0].symbol == "005930"
    assert items[0].return_rate == Decimal("10.7700")


def test_toss_buying_power(monkeypatch):
    adapter = TossAccountAdapter()

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/buying-power"
        assert params == {"currency": "KRW"}
        assert account_seq == 3
        return {
            "result": {
                "currency": "KRW",
                "cashBuyingPower": "5000000",
            }
        }

    monkeypatch.setattr(adapter.client, "get", fake_get)
    value = asyncio.run(
        adapter.buying_power(account_seq=3)
    )

    assert value == Decimal("5000000")
