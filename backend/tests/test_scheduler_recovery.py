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
            items=[],
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


def test_adaptive_scheduler_pushes_completed_cycle_summary(
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
            next_check_minutes=45,
            reason=None,
            items=[
                SimpleNamespace(
                    decision=SimpleNamespace(action="BUY"),
                    order=SimpleNamespace(),
                ),
                SimpleNamespace(
                    decision=SimpleNamespace(action="HOLD"),
                    order=None,
                ),
                SimpleNamespace(
                    decision=SimpleNamespace(action="SELL"),
                    order=None,
                ),
            ],
        )

    monkeypatch.setattr(
        scheduler.combined_paper_runner,
        "run",
        success,
    )
    monkeypatch.setattr(
        scheduler,
        "schedule_next",
        lambda minutes: minutes,
    )

    sent = []
    monkeypatch.setattr(
        scheduler.push,
        "send",
        lambda **kwargs: sent.append(kwargs),
    )

    asyncio.run(scheduler._run_decision_cycle())

    assert len(sent) == 1
    assert sent[0]["title"] == "자동 판단 완료"
    assert "BUY 1 / SELL 1 / HOLD 1" in sent[0]["body"]
    assert "주문 1건" in sent[0]["body"]
    assert "다음 판단 45분 후" in sent[0]["body"]
    assert sent[0]["data"]["type"] == "decision_cycle_completed"
