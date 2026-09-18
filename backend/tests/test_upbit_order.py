import hashlib
from decimal import Decimal
from urllib.parse import urlencode

import jwt

from backend.app.brokers.upbit_order import UpbitOrderAdapter
from backend.app.brokers.upbit_private import UpbitPrivateClient


def test_upbit_signed_token_contains_query_hash():
    client = UpbitPrivateClient()
    old_access = client.config.upbit_access_key
    old_secret = client.config.upbit_secret_key

    try:
        client.config.upbit_access_key = "test-access"
        client.config.upbit_secret_key = "test-secret"
        body = {
            "market": "KRW-BTC",
            "side": "bid",
            "price": "10000",
            "ord_type": "price",
            "identifier": "meme-test",
        }

        token = client._create_token(body)
        decoded = jwt.decode(
            token,
            "test-secret",
            algorithms=["HS512"],
        )
        expected = hashlib.sha512(
            urlencode(list(body.items())).encode("utf-8")
        ).hexdigest()

        assert decoded["access_key"] == "test-access"
        assert decoded["query_hash_alg"] == "SHA512"
        assert decoded["query_hash"] == expected
    finally:
        client.config.upbit_access_key = old_access
        client.config.upbit_secret_key = old_secret


def test_upbit_market_buy_uses_krw_notional_not_volume():
    adapter = UpbitOrderAdapter()
    body = adapter.build_market_order(
        symbol="KRW-BTC",
        side="buy",
        quantity=Decimal("0.001"),
        notional=Decimal("10000.9"),
        identifier="meme-test",
    )

    assert body["side"] == "bid"
    assert body["ord_type"] == "price"
    assert body["price"] == "10000"
    assert "volume" not in body


def test_upbit_market_sell_uses_volume():
    adapter = UpbitOrderAdapter()
    body = adapter.build_market_order(
        symbol="KRW-BTC",
        side="sell",
        quantity=Decimal("0.00123456789"),
        notional=Decimal("100000"),
        identifier="meme-test",
    )

    assert body["side"] == "ask"
    assert body["ord_type"] == "market"
    assert body["volume"] == "0.00123456"
    assert "price" not in body
