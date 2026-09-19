import asyncio
from types import SimpleNamespace

from backend.app.services.scheduler import AdaptiveDecisionScheduler


def test_adaptive_scheduler_reschedules_after_unexpected_cycle_error(
    monkeypatch,
):
    scheduler = AdaptiveDecisionScheduler()
    scheduler.audit.write = lambda *args, **kwargs: None
    scheduler.push.send = lambda *args, **kwargs: None

    monkeypatch.setattr(
        scheduler.runtime,
        "get",
        lambda: SimpleNamespace(mode="paper"),
    )

    async def fail():
        raise RuntimeError("boom")

    monkeypatch.setattr(
        scheduler.combined_paper_runner,
        "run",
        fail,
    )

    scheduled = []

    def fake_schedule(minutes):
        scheduled.append(minutes)
        return minutes

    monkeypatch.setattr(
        scheduler,
        "schedule_next",
        fake_schedule,
    )

    asyncio.run(scheduler._run_decision_cycle())

    assert scheduled == [
        scheduler.config.decision_default_interval_minutes
    ]


def test_adaptive_scheduler_uses_llm_next_interval_on_success(
    monkeypatch,
):
    scheduler = AdaptiveDecisionScheduler()
    scheduler.audit.write = lambda *args, **kwargs: None

    monkeypatch.setattr(
        scheduler.runtime,
        "get",
        lambda: SimpleNamespace(mode="paper"),
    )

    async def success():
        return SimpleNamespace(
            status="completed",
            next_check_minutes=35,
            reason=None,
        )

    monkeypatch.setattr(
        scheduler.combined_paper_runner,
        "run",
        success,
    )

    scheduled = []
    monkeypatch.setattr(
        scheduler,
        "schedule_next",
        lambda minutes: scheduled.append(minutes) or minutes,
    )

    asyncio.run(scheduler._run_decision_cycle())

    assert scheduled == [35]
