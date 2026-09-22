from types import SimpleNamespace

from backend.app.services import cycle_metrics as module
from backend.app.services.cycle_metrics import CycleMetricsStore


def make_store(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            data_path=tmp_path,
            app_timezone="Asia/Seoul",
        ),
    )
    return CycleMetricsStore()


def test_paper_reset_markers_are_market_specific(monkeypatch, tmp_path):
    store = make_store(monkeypatch, tmp_path)

    stock_at = store.mark_paper_reset("stock")
    markers = store.paper_reset_markers()

    assert markers["stock"] == stock_at
    assert "crypto" not in markers

    store.mark_paper_reset("all")
    markers = store.paper_reset_markers()

    assert "stock" in markers
    assert "crypto" in markers
