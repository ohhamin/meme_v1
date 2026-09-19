from datetime import datetime, timezone

from backend.app.services.scheduler_state import SchedulerStateService


def test_scheduler_state_round_trip(tmp_path):
    service = SchedulerStateService()
    service.path = tmp_path / "scheduler.json"

    value = datetime(2026, 9, 19, 3, 30, tzinfo=timezone.utc)
    service.save_next_decision_at(value)

    loaded = service.next_decision_at()
    assert loaded == value


def test_scheduler_state_ignores_invalid_timestamp(tmp_path):
    service = SchedulerStateService()
    service.path = tmp_path / "scheduler.json"
    service.path.write_text(
        '{"next_decision_at":"not-a-date"}',
        encoding="utf-8",
    )

    assert service.next_decision_at() is None
