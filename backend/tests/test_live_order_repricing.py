import asyncio
from decimal import Decimal

from backend.app.services.live_order_service import LiveOrderService


def test_live_auto_stock_reprices_notional_before_execute(monkeypatch):
    service = LiveOrderService()
    monkeypatch.setattr(
        service,
        "_require_live_auto",
        lambda broker: None,
    )

    async def fake_toss(symbol):
        return {
            "broker": "toss",
            "market": "stock",
            "symbol": symbol,
            "price": Decimal("80000"),
        }

    captured = {}

    async def fake_execute(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(service.snapshots, "toss", fake_toss)
    monkeypatch.setattr(service, "_execute", fake_execute)

    result = asyncio.run(
        service.auto_order(
            market="stock",
            symbol="005930",
            side="buy",
            quantity=Decimal("2"),
            notional=Decimal("140000"),
        )
    )

    assert result == "ok"
    assert captured["notional"] == Decimal("160000")


def test_live_auto_crypto_buy_preserves_krw_notional(monkeypatch):
    service = LiveOrderService()
    monkeypatch.setattr(
        service,
        "_require_live_auto",
        lambda broker: None,
    )

    async def fake_upbit(symbol):
        return {
            "broker": "upbit",
            "market": "crypto",
            "symbol": symbol,
            "price": Decimal("120000000"),
        }

    captured = {}

    async def fake_execute(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(service.snapshots, "upbit", fake_upbit)
    monkeypatch.setattr(service, "_execute", fake_execute)

    result = asyncio.run(
        service.auto_order(
            market="crypto",
            symbol="KRW-BTC",
            side="buy",
            quantity=Decimal("0.001"),
            notional=Decimal("100000"),
        )
    )

    assert result == "ok"
    assert captured["notional"] == Decimal("100000")
