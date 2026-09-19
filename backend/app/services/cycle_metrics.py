import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class CycleMetricsStore:
    """Append compact non-secret cycle telemetry for later strategy review."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.base_dir: Path = (
            self.config.data_path
            / "metrics"
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        mode: str,
        accounts: dict,
        decision_count: int,
        order_count: int,
        blocked_count: int,
        next_check_minutes: int,
    ) -> Path:
        now = datetime.now(self.tz)
        path = self.base_dir / f"{now.date().isoformat()}.jsonl"

        payload = {
            "timestamp": now.isoformat(),
            "mode": mode,
            "decision_count": decision_count,
            "order_count": order_count,
            "blocked_count": blocked_count,
            "next_check_minutes": next_check_minutes,
            "accounts": accounts,
        }

        with path.open("a", encoding="utf-8") as fp:
            fp.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
        return path

    def recent(self, limit_days: int = 7) -> list[dict]:
        files = sorted(
            self.base_dir.glob("*.jsonl"),
            reverse=True,
        )[: max(1, limit_days)]

        records: list[dict] = []
        for path in reversed(files):
            try:
                lines = path.read_text(
                    encoding="utf-8"
                ).splitlines()
            except OSError:
                continue

            for line in lines:
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(raw, dict):
                    records.append(raw)

        return records
