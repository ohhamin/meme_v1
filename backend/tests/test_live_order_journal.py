from decimal import Decimal

from backend.app.services.live_order_journal import LiveOrderJournal


def make_journal(tmp_path):
    journal = LiveOrderJournal()
    journal.base_dir = tmp_path / "live_orders"
    journal.base_dir.mkdir(parents=True, exist_ok=True)
    return journal


def test_live_order_journal_persists_state_before_submission(tmp_path):
    journal = make_journal(tmp_path)
    record = journal.create(
        broker="upbit",
        source="manual",
        market="crypto",
        symbol="KRW-BTC",
        side="buy",
        quantity=Decimal("0.001"),
        notional=Decimal("100000"),
        reference_price=Decimal("100000000"),
    )

    assert record.status == "CREATED"
    assert record.client_order_id.startswith("meme-")

    updated = journal.update(
        record.intent_id,
        status="SUBMITTING",
    )
    loaded = journal.get(record.intent_id)

    assert updated.status == "SUBMITTING"
    assert loaded.status == "SUBMITTING"
    assert len(journal.unresolved()) == 1


def test_live_order_unknown_is_never_terminal(tmp_path):
    journal = make_journal(tmp_path)
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

    assert journal.unresolved()[0].status == "UNKNOWN"



def test_same_symbol_unresolved_guard(tmp_path):
    journal = make_journal(tmp_path)
    first = journal.create(
        broker="upbit",
        source="auto",
        market="crypto",
        symbol="KRW-BTC",
        side="buy",
        quantity=Decimal("0.001"),
        notional=Decimal("100000"),
        reference_price=Decimal("100000000"),
    )
    journal.update(first.intent_id, status="SUBMITTED")

    assert journal.has_unresolved(
        broker="upbit",
        symbol="krw-btc",
    ) is True
    assert journal.has_unresolved(
        broker="upbit",
        symbol="KRW-ETH",
    ) is False

    journal.update(first.intent_id, status="CONFIRMED")
    assert journal.has_unresolved(
        broker="upbit",
        symbol="KRW-BTC",
    ) is False
