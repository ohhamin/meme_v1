import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class LLMRuntimeStateService:
    """LLM API 장애/한도 상태를 로컬에 보존한다."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "llm_runtime.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict:
        state = self._read()

        retry_at = state.get("retry_at")
        if state.get("mode") == "backoff" and retry_at:
            try:
                retry_dt = datetime.fromisoformat(retry_at)
                if datetime.now(self.tz) >= retry_dt:
                    state = self.resume()
            except ValueError:
                state = self.resume()

        return state

    def backoff(self, *, reason: str, retry_after_seconds: int) -> dict:
        retry_at = datetime.now(self.tz) + timedelta(
            seconds=max(1, retry_after_seconds)
        )
        return self._write(
            {
                "mode": "backoff",
                "reason": reason,
                "retry_at": retry_at.isoformat(),
            }
        )

    def pause(self, *, reason: str) -> dict:
        return self._write(
            {
                "mode": "paused",
                "reason": reason,
                "retry_at": None,
            }
        )

    def resume(self) -> dict:
        return self._write(
            {
                "mode": "normal",
                "reason": None,
                "retry_at": None,
            }
        )

    def handle_api_failure(
        self,
        *,
        kind: str,
        retry_after_seconds: int | None = None,
    ) -> dict:
        """OpenAI client 연결 후 예외를 정규화해 호출한다.

        transient/rate_limit/overloaded -> 잠시 backoff
        quota/billing/auth -> 자동 재시도하지 않고 pause
        """
        normalized = kind.lower().strip()

        if normalized in {
            "rate_limit",
            "overloaded",
            "timeout",
            "transient",
        }:
            return self.backoff(
                reason=normalized,
                retry_after_seconds=retry_after_seconds or 60,
            )

        return self.pause(reason=normalized)

    def _default(self) -> dict:
        return {
            "mode": "normal",
            "reason": None,
            "retry_at": None,
        }

    def _read(self) -> dict:
        if not self.path.exists():
            return self._write(self._default())

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._write(self._default())

        if not isinstance(raw, dict):
            return self._write(self._default())
        return {
            **self._default(),
            **raw,
        }

    def _write(self, state: dict) -> dict:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return state
