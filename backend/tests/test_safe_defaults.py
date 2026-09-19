import asyncio

import pytest
from fastapi import HTTPException

from backend.app.services.live_auto_cycle import LiveAutoCycleService
from backend.app.services.live_order_service import LiveOrderService


def test_default_live_manual_crypto_order_is_blocked_before_network():
    service = LiveOrderService()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.manual_crypto_order(
                symbol="KRW-BTC",
                side="buy",
                amount_krw=10000,
                idempotency_key="safe-default-test",
            )
        )

    assert exc.value.status_code == 423
    detail = exc.value.detail
    assert "Live order is disabled" in detail["message"]


def test_default_live_manual_stock_order_is_blocked_before_network():
    service = LiveOrderService()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.manual_stock_order(
                symbol="005930",
                side="buy",
                quantity=1,
                idempotency_key="safe-default-stock-test",
            )
        )

    assert exc.value.status_code == 423


def test_default_live_auto_cycle_is_blocked_before_llm_or_broker():
    service = LiveAutoCycleService()
    result = asyncio.run(service.run())

    assert result.status == "blocked"
    assert result.reason
