import json
from pathlib import Path

from fastapi import HTTPException, status

from backend.app.core.config import get_settings


class IdempotencyStore:
    def __init__(self):
        self.path: Path = get_settings().data_path / "state" / "idempotency.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_new(self, key: str) -> None:
        keys = self._read()
        if key in keys:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate order request.",
            )

    def remember(self, key: str, order_id: str) -> None:
        keys = self._read()
        keys[key] = order_id
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(keys, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
