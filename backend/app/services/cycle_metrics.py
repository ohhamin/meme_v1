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
        self.reset_markers_path = self.base_dir / "paper_reset_markers.json"

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


    def mark_paper_reset(self, market: str) -> str:
        """Record a Paper reset boundary without deleting telemetry."""
        if market not in {"stock", "crypto", "all"}:
            raise ValueError("market must be stock, crypto, or all")

        now = datetime.now(self.tz).isoformat()
        markers = self.paper_reset_markers()
        targets = ("stock", "crypto") if market == "all" else (market,)
        for target in targets:
            markers[target] = now

        temp = self.reset_markers_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(markers, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temp.replace(self.reset_markers_path)
        return now

    def paper_reset_markers(self) -> dict[str, str]:
        if not self.reset_markers_path.exists():
            return {}
        try:
            raw = json.loads(
                self.reset_markers_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {
            key: str(value)
            for key, value in raw.items()
            if key in {"stock", "crypto"} and value
        }
