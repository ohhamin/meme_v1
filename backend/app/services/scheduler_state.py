import json
from datetime import datetime
from pathlib import Path

from backend.app.core.config import get_settings


class SchedulerStateService:
    """Persist only the next adaptive decision time across backend restarts."""

    def __init__(self):
        self.config = get_settings()
        self.path: Path = (
            self.config.data_path
            / "state"
            / "scheduler.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def next_decision_at(self) -> datetime | None:
        data = self._read()
        raw = data.get("next_decision_at")
        if not raw:
            return None
        try:
            value = datetime.fromisoformat(str(raw))
        except ValueError:
            return None
        return value if value.tzinfo is not None else None

    def save_next_decision_at(self, value: datetime) -> None:
        self._write(
            {"next_decision_at": value.isoformat()}
        )

    def clear_next_decision_at(self) -> None:
        self._write({})

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            return raw if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
