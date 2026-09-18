from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import get_settings
from backend.app.services.news_collector import NewsCollector
from backend.app.services.algorithm_review import AlgorithmReviewService


class AdaptiveDecisionScheduler:
    def __init__(self):
        self.config = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.config.app_timezone)
        self.news_collector = NewsCollector()
        self.algorithm_review = AlgorithmReviewService()

    def start(self) -> None:
        if not self.config.scheduler_enabled:
            return

        if not self.scheduler.running:
            self.scheduler.start()

        self.schedule_news_collection()
        self.schedule_algorithm_review()
        self.schedule_next(self.config.decision_default_interval_minutes)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_news_collection(self) -> None:
        """뉴스 수집은 전체 판단 주기와 별개로 6시간 간격으로 실행한다."""
        self.scheduler.add_job(
            self.news_collector.run,
            trigger="interval",
            hours=self.config.news_collection_interval_hours,
            id="news-collector",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def schedule_algorithm_review(self) -> None:
        """알고리즘 개선 검토는 판단 사이클과 분리해 기본 24시간마다 실행한다."""
        self.scheduler.add_job(
            self.algorithm_review.review,
            trigger="interval",
            hours=self.config.algorithm_review_interval_hours,
            id="algorithm-review",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def schedule_next(self, proposed_minutes: int) -> int:
        minutes = self.config.clamp_decision_interval(proposed_minutes)

        # TODO: Decision Engine 연결 후 전체 관심/보유 종목을 한 번에 평가하는 cycle 함수를 등록한다.
        # 현재는 골격 단계라 자동 주문이 발생하지 않도록 job을 만들지 않는다.
        return minutes

    def next_run_at(self, proposed_minutes: int) -> datetime:
        minutes = self.config.clamp_decision_interval(proposed_minutes)
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)
