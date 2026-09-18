import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class LiveDailyBaselineService:
    """Stores first observed live account equity for each broker/day."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = (
            self.config.data_path
            / "state"
            / "live_daily_baselines.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def daily_pnl_pct(
        self,
        *,
        broker: str,
        equity: Decimal,
    ) -> Decimal:
        baseline = self.get_or_create(
            broker=broker,
            equity=equity,
        )
        if baseline <= 0:
            return Decimal("0")
        return (
            (equity - baseline)
            / baseline
            * Decimal("100")
        )

    def get_or_create(
        self,
        *,
        broker: str,
        equity: Decimal,
    ) -> Decimal:
        data = self._read()
        today = datetime.now(self.tz).date().isoformat()
        key = f"{today}:{broker}"

        if key not in data:
            data[key] = str(equity)
            self._write(data)

        try:
            return Decimal(str(data[key]))
        except Exception:
            data[key] = str(equity)
            self._write(data)
            return equity

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            return raw if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, str]) -> None:
        # Keep only a small rolling window.
        if len(data) > 30:
            data = dict(
                sorted(data.items())[-30:]
            )
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
