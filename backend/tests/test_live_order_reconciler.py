import asyncio
from decimal import Decimal

from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_order_reconciler import LiveOrderReconciler


def test_reconciler_recovers_unknown_toss_order_by_client_id(
    tmp_path,
    monkeypatch,
):
    journal = LiveOrderJournal()
    journal.base_dir = tmp_path / "live_orders"
    journal.base_dir.mkdir(parents=True, exist_ok=True)

    record = journal.create(
        broker="toss",
        source="manual",
        market="stock",
        symbol="005930",
        side="buy",
        quantity=Decimal("1"),
        notional=Decimal("70000"),
        reference_price=Decimal("70000"),
    )
    journal.update(
        record.intent_id,
        status="UNKNOWN",
        reason="timeout",
    )

    reconciler = LiveOrderReconciler()
    reconciler.journal = journal
    reconciler.audit.write = lambda *args, **kwargs: None
    reconciler.push.send = lambda *args, **kwargs: None

    async def fake_find(*, symbol, client_order_id):
        assert symbol == "005930"
        assert client_order_id == record.client_order_id
        return {
            "orderId": "toss-order-1",
            "clientOrderId": client_order_id,
            "status": "PENDING",
        }

    async def fake_get_order(order_id):
        assert order_id == "toss-order-1"
        return {
            "result": {
                "orderId": order_id,
                "status": "FILLED",
            }
        }

    monkeypatch.setattr(
        reconciler.toss,
        "find_order_by_client_order_id",
        fake_find,
    )
    monkeypatch.setattr(
        reconciler.toss,
        "get_order",
        fake_get_order,
    )

    result = asyncio.run(
        reconciler.reconcile(intent_id=record.intent_id)
    )

    assert result.updated == 1
    assert result.unresolved == 0
    assert result.records[0].status == "CONFIRMED"
    assert result.records[0].broker_order_id == "toss-order-1"
    assert result.records[0].broker_status == "FILLED"


def test_reconciler_keeps_unknown_toss_order_when_not_found(
    tmp_path,
    monkeypatch,
):
    journal = LiveOrderJournal()
    journal.base_dir = tmp_path / "live_orders"
    journal.base_dir.mkdir(parents=True, exist_ok=True)

    record = journal.create(
        broker="toss",
        source="manual",
        market="stock",
        symbol="005930",
        side="buy",
        quantity=Decimal("1"),
        notional=Decimal("70000"),
        reference_price=Decimal("70000"),
    )
    journal.update(record.intent_id, status="UNKNOWN")

    reconciler = LiveOrderReconciler()
    reconciler.journal = journal

    async def fake_find(**kwargs):
        return None

    monkeypatch.setattr(
        reconciler.toss,
        "find_order_by_client_order_id",
        fake_find,
    )

    result = asyncio.run(
        reconciler.reconcile(intent_id=record.intent_id)
    )

    assert result.updated == 0
    assert result.unresolved == 1
    assert result.records[0].status == "UNKNOWN"
