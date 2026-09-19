import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from backend.app.core.config import get_settings


class IdempotencyStore:
    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = (
            self.config.data_path
            / "state"
            / "idempotency.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_new(self, key: str) -> None:
        entries = self._read()
        if key in entries:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate order request.",
            )

    def remember(self, key: str, order_id: str) -> None:
        entries = self._read()
        entries[key] = {
            "order_id": order_id,
            "created_at": datetime.now(self.tz).isoformat(),
        }
        self._write(entries)

    def prune(self) -> int:
        raw = self._read_raw()
        normalized = self._normalize(raw)
        pruned = self._pruned(normalized)
        removed = len(normalized) - len(pruned)
        if removed or raw != pruned:
            self._write(pruned)
        return removed

    def _read(self) -> dict[str, dict[str, str]]:
        raw = self._read_raw()
        normalized = self._normalize(raw)
        pruned = self._pruned(normalized)

        if raw != pruned:
            self._write(pruned)

        return pruned

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            return raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _normalize(self, raw: dict) -> dict[str, dict[str, str]]:
        now = datetime.now(self.tz).isoformat()
        result: dict[str, dict[str, str]] = {}

        for key, value in raw.items():
            if not isinstance(key, str):
                continue

            # Migration from the original {"key": "order_id"} format.
            if isinstance(value, str):
                result[key] = {
                    "order_id": value,
                    "created_at": now,
                }
                continue

            if not isinstance(value, dict):
                continue

            order_id = str(value.get("order_id") or "")
            created_at = str(value.get("created_at") or now)
            if not order_id:
                continue

            result[key] = {
                "order_id": order_id,
                "created_at": created_at,
            }

        return result

    def _pruned(
        self,
        entries: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, str]]:
        days = max(1, self.config.idempotency_retention_days)
        cutoff = datetime.now(self.tz) - timedelta(days=days)

        result: dict[str, dict[str, str]] = {}
        for key, value in entries.items():
            try:
                created = datetime.fromisoformat(
                    value["created_at"]
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=self.tz)
                created = created.astimezone(self.tz)
            except (ValueError, KeyError):
                # Unknown timestamps are retained rather than risking a
                # duplicate order after a malformed state migration.
                result[key] = value
                continue

            if created >= cutoff:
                result[key] = value

        return result

    def _write(self, entries: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                entries,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)
