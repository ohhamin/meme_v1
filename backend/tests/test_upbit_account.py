import asyncio

import jwt

from backend.app.brokers.upbit_account import UpbitAccountAdapter


def test_unconfigured_account_returns_empty():
    adapter = UpbitAccountAdapter()
    old_access = adapter.config.upbit_access_key
    old_secret = adapter.config.upbit_secret_key

    try:
        adapter.config.upbit_access_key = ""
        adapter.config.upbit_secret_key = ""

        result = asyncio.run(adapter.balances())

        assert result.configured is False
        assert result.assets == []
    finally:
        adapter.config.upbit_access_key = old_access
        adapter.config.upbit_secret_key = old_secret


def test_auth_token_uses_hs512_and_unique_nonce():
    adapter = UpbitAccountAdapter()
    old_access = adapter.config.upbit_access_key
    old_secret = adapter.config.upbit_secret_key

    try:
        adapter.config.upbit_access_key = "test-access"
        adapter.config.upbit_secret_key = "test-secret"

        token1 = adapter._create_token()
        token2 = adapter._create_token()

        payload1 = jwt.decode(
            token1,
            "test-secret",
            algorithms=["HS512"],
        )
        payload2 = jwt.decode(
            token2,
            "test-secret",
            algorithms=["HS512"],
        )

        assert payload1["access_key"] == "test-access"
        assert payload1["nonce"]
        assert payload1["nonce"] != payload2["nonce"]
    finally:
        adapter.config.upbit_access_key = old_access
        adapter.config.upbit_secret_key = old_secret
