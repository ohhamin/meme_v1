import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class DeviceTokenService:
    """Small single-user FCM token registry persisted on the backend."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = (
            self.config.data_path
            / "state"
            / "device_tokens.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        *,
        token: str,
        platform: str = "unknown",
    ) -> None:
        data = self._read()
        now = datetime.now(self.tz).isoformat()
        data[token] = {
            "platform": platform,
            "updated_at": now,
        }
        self._write(data)

    def clear(self) -> None:
        self._write({})

    def tokens(self) -> list[str]:
        data = self._read()
        return list(data.keys())

    def status(self) -> dict:
        tokens = self.tokens()
        return {
            "registered": bool(tokens),
            "token_count": len(tokens),
        }

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
