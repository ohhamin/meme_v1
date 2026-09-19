import asyncio
from decimal import Decimal

from backend.app.brokers.toss_order import TossOrderAdapter


def test_toss_buy_preflight_checks_cash(monkeypatch):
    adapter = TossOrderAdapter()
    old_id = adapter.config.toss_client_id
    old_secret = adapter.config.toss_client_secret
    old_enabled = adapter.config.toss_live_order_enabled

    try:
        adapter.config.toss_client_id = "id"
        adapter.config.toss_client_secret = "secret"
        adapter.config.toss_live_order_enabled = True

        async def fake_seq():
            return 1

        async def fake_power(*, account_seq=None):
            assert account_seq == 1
            return Decimal("50000")

        monkeypatch.setattr(
            adapter.accounts,
            "selected_account_seq",
            fake_seq,
        )
        monkeypatch.setattr(
            adapter.accounts,
            "buying_power",
            fake_power,
        )

        result = asyncio.run(
            adapter.preflight(
                symbol="005930",
                side="buy",
                quantity=Decimal("1"),
                notional=Decimal("70000"),
                client_order_id="meme-test",
            )
        )

        assert result.allowed is False
        assert any("insufficient" in r.lower() for r in result.reasons)
    finally:
        adapter.config.toss_client_id = old_id
        adapter.config.toss_client_secret = old_secret
        adapter.config.toss_live_order_enabled = old_enabled


def test_toss_sell_preflight_checks_sellable_quantity(monkeypatch):
    adapter = TossOrderAdapter()
    old_id = adapter.config.toss_client_id
    old_secret = adapter.config.toss_client_secret
    old_enabled = adapter.config.toss_live_order_enabled

    try:
        adapter.config.toss_client_id = "id"
        adapter.config.toss_client_secret = "secret"
        adapter.config.toss_live_order_enabled = True

        async def fake_seq():
            return 1

        async def fake_get(path, *, params=None, account_seq=None):
            assert path == "/api/v1/sellable-quantity"
            return {"result": {"sellableQuantity": "2"}}

        monkeypatch.setattr(
            adapter.accounts,
            "selected_account_seq",
            fake_seq,
        )
        monkeypatch.setattr(adapter.client, "get", fake_get)

        result = asyncio.run(
            adapter.preflight(
                symbol="005930",
                side="sell",
                quantity=Decimal("3"),
                notional=Decimal("210000"),
                client_order_id="meme-test",
            )
        )

        assert result.allowed is False
        assert any("sellable" in r.lower() for r in result.reasons)
    finally:
        adapter.config.toss_client_id = old_id
        adapter.config.toss_client_secret = old_secret
        adapter.config.toss_live_order_enabled = old_enabled



def test_toss_market_order_payload_and_high_value_flag():
    adapter = TossOrderAdapter()
    old_confirm = adapter.config.toss_confirm_high_value_orders
    old_threshold = adapter.config.toss_high_value_order_threshold_krw

    try:
        adapter.config.toss_high_value_order_threshold_krw = 100000000
        adapter.config.toss_confirm_high_value_orders = False

        normal = adapter.build_market_order(
            symbol="005930",
            side="buy",
            quantity=Decimal("3"),
            notional=Decimal("210000"),
            client_order_id="meme-normal",
        )
        assert normal == {
            "clientOrderId": "meme-normal",
            "symbol": "005930",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": "3",
        }

        adapter.config.toss_confirm_high_value_orders = True
        high = adapter.build_market_order(
            symbol="005930",
            side="sell",
            quantity=Decimal("2000"),
            notional=Decimal("120000000"),
            client_order_id="meme-high",
        )
        assert high["confirmHighValueOrder"] is True
        assert high["side"] == "SELL"
    finally:
        adapter.config.toss_confirm_high_value_orders = old_confirm
        adapter.config.toss_high_value_order_threshold_krw = old_threshold



def test_find_toss_order_by_client_order_id_from_open(monkeypatch):
    adapter = TossOrderAdapter()

    async def fake_seq():
        return 7

    async def fake_get(path, *, params=None, account_seq=None):
        assert path == "/api/v1/orders"
        assert account_seq == 7
        assert params["symbol"] == "005930"
        if params["status"] == "OPEN":
            return {
                "result": [
                    {
                        "orderId": "order-123",
                        "clientOrderId": "meme-abc",
                        "symbol": "005930",
                        "status": "PENDING",
                    }
                ]
            }
        raise AssertionError("CLOSED lookup should not be needed")

    monkeypatch.setattr(
        adapter.accounts,
        "selected_account_seq",
        fake_seq,
    )
    monkeypatch.setattr(adapter.client, "get", fake_get)

    found = asyncio.run(
        adapter.find_order_by_client_order_id(
            symbol="005930",
            client_order_id="meme-abc",
        )
    )

    assert found is not None
    assert found["orderId"] == "order-123"


def test_find_toss_order_by_client_order_id_from_closed(monkeypatch):
    adapter = TossOrderAdapter()
    calls = []

    async def fake_seq():
        return 7

    async def fake_get(path, *, params=None, account_seq=None):
        calls.append(dict(params))
        if params["status"] == "OPEN":
            return {"result": []}
        return {
            "result": {
                "items": [
                    {
                        "orderId": "order-closed",
                        "clientOrderId": "meme-closed",
                        "symbol": "005930",
                        "status": "FILLED",
                    }
                ]
            }
        }

    monkeypatch.setattr(
        adapter.accounts,
        "selected_account_seq",
        fake_seq,
    )
    monkeypatch.setattr(adapter.client, "get", fake_get)

    found = asyncio.run(
        adapter.find_order_by_client_order_id(
            symbol="005930",
            client_order_id="meme-closed",
        )
    )

    assert found is not None
    assert found["status"] == "FILLED"
    assert [call["status"] for call in calls] == ["OPEN", "CLOSED"]
