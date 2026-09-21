import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class AutoTradeActivityService:
    """Persist last successful automatic order time per mode/market/symbol."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = (
            self.config.data_path
            / "state"
            / "auto_trade_activity.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def seconds_since_last(
        self,
        *,
        mode: str,
        market: str,
        symbol: str,
        side: str | None = None,
        event: str | None = None,
        now: datetime | None = None,
    ) -> int | None:
        data = self._read()
        raw = data.get(
            self._key(
                mode=mode,
                market=market,
                symbol=symbol,
                side=side,
                event=event,
            )
        )
        if not raw:
            return None

        try:
            value = datetime.fromisoformat(str(raw))
            if value.tzinfo is None:
                value = value.replace(tzinfo=self.tz)
            current = now or datetime.now(self.tz)
            if current.tzinfo is None:
                current = current.replace(tzinfo=self.tz)
            delta = (
                current.astimezone(self.tz)
                - value.astimezone(self.tz)
            ).total_seconds()
        except (TypeError, ValueError):
            return None

        return max(0, int(delta))

    def record(
        self,
        *,
        mode: str,
        market: str,
        symbol: str,
        side: str | None = None,
        event: str | None = None,
        at: datetime | None = None,
    ) -> None:
        data = self._read()
        value = at or datetime.now(self.tz)
        if value.tzinfo is None:
            value = value.replace(tzinfo=self.tz)

        data[
            self._key(
                mode=mode,
                market=market,
                symbol=symbol,
                side=side,
                event=event,
            )
        ] = value.astimezone(self.tz).isoformat()

        self._write(data)

    @staticmethod
    def _key(
        *,
        mode: str,
        market: str,
        symbol: str,
        side: str | None = None,
        event: str | None = None,
    ) -> str:
        base = (
            f"{mode.strip().lower()}:"
            f"{market.strip().lower()}:"
            f"{symbol.strip().upper()}"
        )
        if event:
            return f"{base}:event:{event.strip().lower()}"
        if side:
            return f"{base}:side:{side.strip().lower()}"
        return base

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}

        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            if not isinstance(raw, dict):
                return {}
            return {
                str(key): str(value)
                for key, value in raw.items()
                if isinstance(key, str)
                and isinstance(value, str)
            }
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, str]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)
