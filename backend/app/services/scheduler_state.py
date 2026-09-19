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

    def enabled(self, default: bool) -> bool:
        data = self._read()
        value = data.get("enabled")
        return bool(value) if isinstance(value, bool) else bool(default)

    def save_enabled(self, enabled: bool) -> None:
        data = self._read()
        data["enabled"] = bool(enabled)
        if not enabled:
            data.pop("next_decision_at", None)
        self._write(data)

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
        data = self._read()
        data["next_decision_at"] = value.isoformat()
        self._write(data)

    def last_run(self) -> dict | None:
        data = self._read()
        value = data.get("last_run")
        return value if isinstance(value, dict) else None

    def save_last_run(self, value: dict) -> None:
        data = self._read()
        data["last_run"] = value
        self._write(data)

    def clear_next_decision_at(self) -> None:
        data = self._read()
        data.pop("next_decision_at", None)
        self._write(data)

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
