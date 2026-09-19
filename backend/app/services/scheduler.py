from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import get_settings
from backend.app.services.algorithm_review import AlgorithmReviewService
from backend.app.services.audit import AuditLogger
from backend.app.services.news_collector import NewsCollector
from backend.app.services.live_order_reconciler import LiveOrderReconciler
from backend.app.services.live_auto_cycle import LiveAutoCycleService
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.data_retention import DataRetentionService
from backend.app.services.scheduler_state import SchedulerStateService
from backend.app.services.combined_paper_runner import CombinedPaperRunner
from backend.app.services.push import PushService


class AdaptiveDecisionScheduler:
    def __init__(self):
        self.config = get_settings()
        self.scheduler = AsyncIOScheduler(
            timezone=self.config.app_timezone
        )
        self.news_collector = NewsCollector()
        self.algorithm_review = AlgorithmReviewService()
        self.live_order_reconciler = LiveOrderReconciler()
        self.live_auto_cycle = LiveAutoCycleService()
        self.runtime = RuntimeSettingsService()
        self.retention = DataRetentionService()
        self.state = SchedulerStateService()
        self.combined_paper_runner = CombinedPaperRunner()
        self.audit = AuditLogger()
        self.push = PushService()

    def start(self) -> None:
        if not self.config.scheduler_enabled:
            return

        if not self.scheduler.running:
            self.scheduler.start()

        self.schedule_news_collection()
        self.schedule_algorithm_review()
        self.schedule_live_order_reconciliation()
        self.schedule_retention()

        saved_next = self.state.next_decision_at()
        now = datetime.now(timezone.utc)
        if (
            saved_next is not None
            and saved_next.astimezone(timezone.utc) > now
        ):
            self._schedule_at(
                saved_next.astimezone(timezone.utc)
            )
        else:
            self.schedule_next(
                self.config.decision_default_interval_minutes
            )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_news_collection(self) -> None:
        """뉴스는 시작 시 즉시 1회 확인하고 이후 설정된 간격으로 수집한다."""
        self.scheduler.add_job(
            self.news_collector.run,
            trigger="interval",
            hours=self.config.news_collection_interval_hours,
            id="news-collector",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(timezone.utc),
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

    def schedule_live_order_reconciliation(self) -> None:
        """Broker status checks only; never submits or retries a live order."""
        self.scheduler.add_job(
            self.live_order_reconciler.reconcile,
            trigger="interval",
            minutes=5,
            id="live-order-reconciler",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def schedule_retention(self) -> None:
        self.scheduler.add_job(
            self.retention.run,
            trigger="cron",
            hour=3,
            minute=10,
            id="data-retention",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def schedule_next(self, proposed_minutes: int) -> int:
        """Schedule one future decision cycle and persist its run time."""
        minutes = self.config.clamp_decision_interval(
            proposed_minutes
        )
        run_at = datetime.now(timezone.utc) + timedelta(
            minutes=minutes
        )

        if self.scheduler.running:
            self._schedule_at(run_at)
        else:
            self.state.save_next_decision_at(run_at)

        return minutes

    def _schedule_at(self, run_at: datetime) -> None:
        self.scheduler.add_job(
            self._run_decision_cycle,
            trigger="date",
            run_date=run_at,
            id="adaptive-decision-cycle",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300,
        )
        self.state.save_next_decision_at(run_at)

        minutes = max(
            0,
            int(
                (
                    run_at - datetime.now(timezone.utc)
                ).total_seconds()
                // 60
            ),
        )
        self.audit.write(
            "system",
            {
                "event": "decision_cycle_scheduled",
                "run_at": run_at.isoformat(),
                "minutes": minutes,
                "crypto_universe": (
                    self.combined_paper_runner.upbit_universe.get()
                ),
                "stock_universe": (
                    self.combined_paper_runner.toss_universe.get()
                ),
            },
        )

    def status(self) -> dict:
        job = (
            self.scheduler.get_job("adaptive-decision-cycle")
            if self.scheduler.running
            else None
        )
        next_run = (
            job.next_run_time
            if job is not None
            else self.state.next_decision_at()
        )
        return {
            "enabled": self.config.scheduler_enabled,
            "running": self.scheduler.running,
            "last_run": self.state.last_run(),
            "next_decision_at": (
                next_run.isoformat()
                if next_run is not None
                else None
            ),
        }

    async def _run_decision_cycle(self) -> None:
        runtime = self.runtime.get()
        next_minutes = (
            self.config.decision_default_interval_minutes
        )

        try:
            if runtime.mode == "live":
                result = await self.live_auto_cycle.run()
            else:
                result = await self.combined_paper_runner.run()

            if (
                result.status == "completed"
                and result.next_check_minutes is not None
            ):
                next_minutes = result.next_check_minutes

            self.state.save_last_run(
                {
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "mode": runtime.mode,
                    "status": result.status,
                    "reason": result.reason,
                    "next_check_minutes": next_minutes,
                    "decision_count": len(result.items),
                    "order_count": sum(1 for item in result.items if item.order is not None),
                }
            )

            self.audit.write(
                "system",
                {
                    "event": "scheduled_decision_cycle_finished",
                    "mode": runtime.mode,
                    "status": result.status,
                    "reason": result.reason,
                    "next_check_minutes": next_minutes,
                },
            )
        except Exception as exc:
            self.state.save_last_run(
                {
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "mode": runtime.mode,
                    "status": "failed",
                    "reason": type(exc).__name__,
                    "next_check_minutes": next_minutes,
                    "decision_count": 0,
                    "order_count": 0,
                }
            )
            # This is a one-shot adaptive job. Any unexpected exception must
            # still schedule the next cycle or automation would silently stop.
            self.audit.write(
                "system",
                {
                    "event": "scheduled_decision_cycle_failed",
                    "mode": runtime.mode,
                    "error_type": type(exc).__name__,
                    "next_check_minutes": next_minutes,
                },
            )
            self.push.send(
                title="자동 판단 오류",
                body=(
                    "판단 사이클에서 예외가 발생했어요. "
                    "신규 주문 없이 기본 주기로 다시 시도합니다."
                ),
                data={
                    "type": "decision_cycle_failed",
                    "mode": runtime.mode,
                },
            )
        finally:
            self.schedule_next(next_minutes)

    def next_run_at(self, proposed_minutes: int) -> datetime:
        minutes = self.config.clamp_decision_interval(
            proposed_minutes
        )
        return datetime.now(timezone.utc) + timedelta(
            minutes=minutes
        )
