import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class AuditLogger:
    def __init__(self):
        self.config = get_settings()
        self.base_dir: Path = self.config.data_path / "logs"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tz = ZoneInfo(self.config.app_timezone)

    def write(self, stream: str, event: dict) -> None:
        now = datetime.now(self.tz)
        path = self.base_dir / f"{stream}-{now.date().isoformat()}.jsonl"
        payload = {
            "timestamp": now.isoformat(),
            **event,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
