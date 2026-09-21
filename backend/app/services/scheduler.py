from datetime import datetime, timedelta, timezone
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError

logger = logging.getLogger(__name__)

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
from backend.app.services.macro_market_context import MacroMarketContextService
from backend.app.services.backend_errors import BackendErrorStore


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
        self.macro_context = MacroMarketContextService()
        self.backend_errors = BackendErrorStore()

    def start(self) -> None:
        if not self.runtime.get().scheduler_enabled:
            return

        if not self.scheduler.running:
            self.scheduler.start()

        self.schedule_news_collection()
        self.schedule_macro_context()
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

    def set_enabled(self, enabled: bool) -> dict:
        self.runtime.set_scheduler_enabled(enabled)
        if enabled:
            if not self.scheduler.running:
                self.scheduler.start()
            self.schedule_news_collection()
            self.schedule_macro_context()
            self.schedule_algorithm_review()
            self.schedule_live_order_reconciliation()
            self.schedule_retention()
            self.schedule_next(self.config.decision_default_interval_minutes)
        else:
            if self.scheduler.running:
                self.scheduler.remove_all_jobs()
            self.state.clear_next_decision_at()
        return self.status()

    def schedule_news_collection(self) -> None:
        """뉴스는 매일 KST 09:00 / 21:00에 정확히 수집한다."""
        self.scheduler.add_job(
            self.news_collector.run,
            trigger="cron",
            hour="9,21",
            minute=0,
            id="news-collector",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def schedule_macro_context(self) -> None:
        """Refresh deterministic macro observations at startup and every 6 hours."""
        self.scheduler.add_job(
            self.macro_context.refresh,
            trigger="interval",
            hours=6,
            id="macro-market-context",
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
            "enabled": self.runtime.get().scheduler_enabled,
            "running": self.scheduler.running and self.runtime.get().scheduler_enabled,
            "last_run": self.state.last_run(),
            "next_decision_at": (
                next_run.isoformat()
                if next_run is not None
                else None
            ),
        }

    async def _run_decision_cycle(self) -> None:
        runtime = self.runtime.get()
        if not getattr(runtime, "scheduler_enabled", True):
            return
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

            if result.status == "completed":
                self._send_cycle_summary(
                    result=result,
                    mode=runtime.mode,
                    next_minutes=next_minutes,
                )
        except Exception as exc:
            error_type = type(exc).__name__
            if isinstance(exc, ValidationError):
                details = exc.errors(
                    include_url=False,
                    include_input=False,
                    include_context=False,
                )
                error_detail = "; ".join(
                    (
                        f"{'.'.join(str(part) for part in item.get('loc', ()))}: "
                        f"{item.get('msg', 'validation failed')}"
                    )
                    for item in details[:5]
                )
            else:
                error_detail = str(exc).strip()

            safe_reason = (
                f"{error_type}: {error_detail}"
                if error_detail
                else error_type
            )[:1000]
            logger.exception(
                "Scheduled decision cycle failed: %s",
                safe_reason,
            )
            self.backend_errors.report_exception(
                exc,
                source="scheduler.decision_cycle",
                context=f"mode={runtime.mode}",
            )
            self.state.save_last_run(
                {
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "mode": runtime.mode,
                    "status": "failed",
                    "reason": safe_reason,
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
                    "error_type": error_type,
                    "error_detail": error_detail[:1000],
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
            if getattr(self.runtime.get(), "scheduler_enabled", True):
                self.schedule_next(next_minutes)

    def _send_cycle_summary(
        self,
        *,
        result,
        mode: str,
        next_minutes: int,
    ) -> None:
        items = list(getattr(result, "items", []) or [])
        counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for item in items:
            action = getattr(
                getattr(item, "decision", None),
                "action",
                None,
            )
            if action in counts:
                counts[action] += 1

        order_count = sum(
            1
            for item in items
            if getattr(item, "order", None) is not None
        )
        self.push.send(
            title="자동 판단 완료",
            body=(
                f"BUY {counts['BUY']} / SELL {counts['SELL']} / "
                f"HOLD {counts['HOLD']} · 주문 {order_count}건 · "
                f"다음 판단 {next_minutes}분 후"
            ),
            data={
                "type": "decision_cycle_completed",
                "mode": mode,
                "buy_count": str(counts["BUY"]),
                "sell_count": str(counts["SELL"]),
                "hold_count": str(counts["HOLD"]),
                "order_count": str(order_count),
                "next_check_minutes": str(next_minutes),
            },
        )

    def next_run_at(self, proposed_minutes: int) -> datetime:
        minutes = self.config.clamp_decision_interval(
            proposed_minutes
        )
        return datetime.now(timezone.utc) + timedelta(
            minutes=minutes
        )
