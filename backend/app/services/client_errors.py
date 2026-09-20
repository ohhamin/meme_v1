import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class ClientErrorStore:
    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "client_errors.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        data = self._read()
        return sorted(
            data,
            key=lambda item: str(item.get("last_seen_at") or ""),
            reverse=True,
        )

    def report(
        self,
        *,
        message: str,
        stack: str = "",
        library: str = "",
        context: str = "",
    ) -> dict:
        normalized = (message.strip() + "\n" + stack.strip()[:4000]).strip()
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        now = datetime.now(self.tz).isoformat()
        items = self._read()

        for item in items:
            if item.get("fingerprint") == fingerprint:
                item["last_seen_at"] = now
                item["count"] = int(item.get("count") or 1) + 1
                item["message"] = message[:4000]
                item["stack"] = stack[:12000]
                item["library"] = library[:500]
                item["context"] = context[:1000]
                # A recurrence means it is not currently improved.
                item["improved"] = False
                item["improved_at"] = None
                self._write(items)
                return item

        record = {
            "id": fingerprint,
            "fingerprint": fingerprint,
            "message": message[:4000],
            "stack": stack[:12000],
            "library": library[:500],
            "context": context[:1000],
            "first_seen_at": now,
            "last_seen_at": now,
            "count": 1,
            "improved": False,
            "improved_at": None,
        }
        items.append(record)
        self._write(items)
        return record

    def mark_improved(self, error_id: str, improved: bool = True) -> dict:
        items = self._read()
        for item in items:
            if item.get("id") == error_id:
                item["improved"] = improved
                item["improved_at"] = (
                    datetime.now(self.tz).isoformat() if improved else None
                )
                self._write(items)
                return item
        raise KeyError(error_id)

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _write(self, items: list[dict]) -> None:
        # Keep a practical history without letting runtime state grow forever.
        items = sorted(
            items,
            key=lambda item: str(item.get("last_seen_at") or ""),
            reverse=True,
        )[:200]
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
