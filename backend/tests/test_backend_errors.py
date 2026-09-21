from types import SimpleNamespace

from backend.app.services import backend_errors as module
from backend.app.services.backend_errors import BackendErrorStore


def make_store(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            data_path=tmp_path,
            app_timezone="Asia/Seoul",
        ),
    )
    return BackendErrorStore()


def test_backend_error_store_deduplicates_and_reopens(
    monkeypatch,
    tmp_path,
):
    store = make_store(monkeypatch, tmp_path)

    first = store.report(
        error_type="ValidationError",
        message="field failed",
        stack="Traceback\nline 1",
        source="scheduler.decision_cycle",
        context="mode=paper",
    )
    store.mark_improved(first["id"], True)

    second = store.report(
        error_type="ValidationError",
        message="field failed",
        stack="Traceback\nline 1",
        source="scheduler.decision_cycle",
        context="mode=paper",
    )

    assert first["id"] == second["id"]
    assert second["count"] == 2
    assert second["improved"] is False
    assert second["improved_at"] is None


def test_backend_error_store_captures_exception_traceback(
    monkeypatch,
    tmp_path,
):
    store = make_store(monkeypatch, tmp_path)

    try:
        raise ValueError("bad value")
    except ValueError as exc:
        item = store.report_exception(
            exc,
            source="test",
            context="unit",
        )

    assert item["error_type"] == "ValueError"
    assert item["message"] == "bad value"
    assert "ValueError: bad value" in item["stack"]
    assert item["source"] == "test"
