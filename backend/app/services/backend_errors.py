import hashlib
import json
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class BackendErrorStore:
    """Persist deduplicated backend errors for in-app inspection."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "backend_errors.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_items(self) -> list:
        return sorted(
            self._read(),
            key=lambda item: str(item.get("last_seen_at") or ""),
            reverse=True,
        )

    def report_exception(
        self,
        exc: BaseException,
        *,
        source: str,
        context: str = "",
    ) -> dict:
        stack = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        return self.report(
            error_type=type(exc).__name__,
            message=str(exc) or type(exc).__name__,
            stack=stack,
            source=source,
            context=context,
        )

    def report(
        self,
        *,
        error_type: str,
        message: str,
        stack: str = "",
        source: str = "",
        context: str = "",
    ) -> dict:
        # Fingerprint excludes volatile context so repeated failures aggregate.
        normalized = (
            error_type.strip()
            + "\n"
            + message.strip()
            + "\n"
            + self._stable_stack(stack)
        ).strip()
        fingerprint = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()[:16]
        now = datetime.now(self.tz).isoformat()
        items = self._read()

        for item in items:
            if item.get("fingerprint") == fingerprint:
                item["last_seen_at"] = now
                item["count"] = int(item.get("count") or 1) + 1
                item["error_type"] = error_type[:300]
                item["message"] = message[:4000]
                item["stack"] = stack[:16000]
                item["source"] = source[:500]
                item["context"] = context[:2000]
                item["improved"] = False
                item["improved_at"] = None
                self._write(items)
                return item

        record = {
            "id": fingerprint,
            "fingerprint": fingerprint,
            "error_type": error_type[:300],
            "message": message[:4000],
            "stack": stack[:16000],
            "source": source[:500],
            "context": context[:2000],
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

    @staticmethod
    def _stable_stack(stack: str) -> str:
        # Keep enough call-site information for grouping without using the
        # entire traceback, which may contain volatile values.
        lines = [
            line.strip()
            for line in stack.splitlines()
            if line.strip()
        ]
        return "\n".join(lines[-8:])[:4000]

    def _read(self) -> list:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _write(self, items: list) -> None:
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
