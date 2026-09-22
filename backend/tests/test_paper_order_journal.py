import json
from types import SimpleNamespace

from backend.app.services import paper_order_journal as module
from backend.app.services.paper_order_journal import PaperOrderJournal


def make_journal(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            data_path=tmp_path,
            app_timezone="Asia/Seoul",
        ),
    )
    return PaperOrderJournal()


def test_reset_market_removes_only_selected_market(monkeypatch, tmp_path):
    journal = make_journal(monkeypatch, tmp_path)
    path = journal.base_dir / "2026-09-21.jsonl"
    rows = [
        {"market": "stock", "symbol": "005930", "side": "sell"},
        {"market": "crypto", "symbol": "KRW-BTC", "side": "sell"},
        {"market": "crypto", "symbol": "KRW-ETH", "side": "buy"},
    ]
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )

    removed = journal.reset_market("crypto")

    assert removed == 2
    remaining = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert remaining == [rows[0]]


def test_reset_market_deletes_empty_daily_file(monkeypatch, tmp_path):
    journal = make_journal(monkeypatch, tmp_path)
    path = journal.base_dir / "2026-09-21.jsonl"
    path.write_text(
        json.dumps({"market": "crypto", "symbol": "KRW-BTC"}) + "\n",
        encoding="utf-8",
    )

    assert journal.reset_market("crypto") == 1
    assert not path.exists()
