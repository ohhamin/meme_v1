from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger
from backend.app.services.data_retention import DataRetentionService
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_order_reconciler import LiveOrderReconciler
from backend.app.services.push import PushService


class StartupMaintenanceService:
    """Best-effort startup recovery that never submits a new broker order."""

    def __init__(self):
        self.config = get_settings()
        self.audit = AuditLogger()
        self.retention = DataRetentionService()
        self.journal = LiveOrderJournal()
        self.reconciler = LiveOrderReconciler()
        self.push = PushService()

    async def run(self) -> None:
        retention_result = None
        reconcile_result = None

        try:
            retention_result = self.retention.run()
        except Exception as exc:
            self.audit.write(
                "system",
                {
                    "event": "startup_retention_failed",
                    "error_type": type(exc).__name__,
                },
            )

        try:
            if self.journal.unresolved(limit=200):
                reconcile_result = await self.reconciler.reconcile(
                    limit=200
                )
        except Exception as exc:
            self.audit.write(
                "system",
                {
                    "event": "startup_reconciliation_failed",
                    "error_type": type(exc).__name__,
                },
            )

        self.audit.write(
            "system",
            {
                "event": "startup_maintenance_completed",
                "retention": retention_result,
                "reconciled": (
                    reconcile_result.updated
                    if reconcile_result is not None
                    else 0
                ),
                "unresolved": (
                    reconcile_result.unresolved
                    if reconcile_result is not None
                    else len(self.journal.unresolved(limit=200))
                ),
            },
        )

        if self.config.startup_push_enabled:
            self.push.send(
                title="meme_v1 시작",
                body="백엔드가 시작되었고 안전 상태를 점검했어요.",
                data={"type": "backend_started"},
            )
