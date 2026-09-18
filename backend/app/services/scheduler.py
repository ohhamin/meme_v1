from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import get_settings


class AdaptiveDecisionScheduler:
    def __init__(self):
        self.config = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.config.app_timezone)

    def start(self) -> None:
        if not self.config.scheduler_enabled:
            return
        if not self.scheduler.running:
            self.scheduler.start()
        self.schedule_next(self.config.decision_default_interval_minutes)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_next(self, proposed_minutes: int) -> int:
        minutes = self.config.clamp_decision_interval(proposed_minutes)

        # TODO: Decision Engine 연결 후 실제 cycle 함수를 등록한다.
        # 현재는 골격 단계라 자동 주문이 발생하지 않도록 job을 만들지 않는다.
        return minutes

    def next_run_at(self, proposed_minutes: int) -> datetime:
        minutes = self.config.clamp_decision_interval(proposed_minutes)
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)
