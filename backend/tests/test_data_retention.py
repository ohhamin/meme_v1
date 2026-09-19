from datetime import datetime, timedelta

from backend.app.services.data_retention import DataRetentionService


def test_retention_deletes_only_old_date_files(tmp_path, monkeypatch):
    service = DataRetentionService()
    service.config.data_dir = str(tmp_path)
    service.config.data_retention_days = 7
    service.audit.write = lambda *args, **kwargs: None

    news = tmp_path / "news"
    decisions = tmp_path / "decisions"
    context = tmp_path / "context"
    news.mkdir()
    decisions.mkdir()
    context.mkdir()

    today = datetime.now(service.tz).date()
    old = today - timedelta(days=8)
    keep = today - timedelta(days=6)

    (news / f"{old.isoformat()}.md").write_text("old", encoding="utf-8")
    (news / f"{keep.isoformat()}.md").write_text("keep", encoding="utf-8")
    (news / "notes.md").write_text("manual", encoding="utf-8")

    (decisions / f"{old.isoformat()}.md").write_text("old", encoding="utf-8")
    (decisions / f"{today.isoformat()}.md").write_text("today", encoding="utf-8")

    monkeypatch.setattr(
        "backend.app.services.data_retention.RollingContextService.refresh_all",
        lambda self: None,
    )

    result = service.run()

    assert result["news"] == 1
    assert result["decisions"] == 1
    assert not (news / f"{old.isoformat()}.md").exists()
    assert (news / f"{keep.isoformat()}.md").exists()
    assert (news / "notes.md").exists()
    assert (decisions / f"{today.isoformat()}.md").exists()
