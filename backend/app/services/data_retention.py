from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger
from backend.app.services.rolling_context import RollingContextService
from backend.app.services.idempotency import IdempotencyStore


class DataRetentionService:
    """Prune date-named news/decision Markdown beyond retention window."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.audit = AuditLogger()

    def run(self) -> dict:
        keep_days = max(1, self.config.data_retention_days)
        today = datetime.now(self.tz).date()
        cutoff = today - timedelta(days=keep_days - 1)

        deleted = {
            "news": self._prune_folder(
                self.config.data_path / "news",
                cutoff,
            ),
            "decisions": self._prune_folder(
                self.config.data_path / "decisions",
                cutoff,
            ),
        }

        deleted["idempotency"] = IdempotencyStore().prune()
        RollingContextService().refresh_all()
        self.audit.write(
            "system",
            {
                "event": "data_retention_completed",
                "retention_days": keep_days,
                "cutoff": cutoff.isoformat(),
                "deleted": deleted,
            },
        )
        return deleted

    @staticmethod
    def _prune_folder(
        folder: Path,
        cutoff: date,
    ) -> int:
        folder.mkdir(parents=True, exist_ok=True)
        deleted = 0

        for path in folder.glob("*.md"):
            try:
                file_day = date.fromisoformat(path.stem)
            except ValueError:
                continue

            if file_day < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1

        return deleted
