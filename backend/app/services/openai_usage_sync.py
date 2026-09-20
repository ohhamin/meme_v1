import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from backend.app.core.config import get_settings


@dataclass
class OpenAIUsageState:
    date: str
    status: str = "unavailable"
    last_synced_at: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    error: str | None = None


class OpenAIUsageSyncService:
    """OpenAI official organization Usage/Costs sync.

    These endpoints require OPENAI_ADMIN_KEY. OpenAI currently does not expose
    a documented API for prepaid credit balance, so this service never invents
    or estimates that balance.
    """

    _lock = asyncio.Lock()

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "openai_usage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    def _today(self) -> str:
        return self._now().date().isoformat()

    def status(self) -> dict:
        if not self.config.openai_admin_key:
            return self._decorate(
                OpenAIUsageState(
                    date=self._today(),
                    status="admin_key_required",
                    error="OPENAI_ADMIN_KEY is not configured.",
                )
            )

        if not self.path.exists():
            return self._decorate(OpenAIUsageState(date=self._today()))

        try:
            state = OpenAIUsageState(
                **json.loads(self.path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            state = OpenAIUsageState(date=self._today())

        if state.date != self._today():
            state = OpenAIUsageState(date=self._today(), status="stale")
        return self._decorate(state)

    def _decorate(self, state: OpenAIUsageState) -> dict:
        payload = asdict(state)
        payload["source"] = "openai_organization_api"
        payload["credit_balance_usd"] = None
        payload["credit_balance_available"] = False
        payload["credit_balance_note"] = (
            "OpenAI does not provide a documented API for prepaid credit balance."
        )
        payload["project_filter"] = self.config.openai_project_id or None
        return payload

    async def refresh(self) -> dict:
        if not self.config.openai_admin_key:
            return self.status()

        async with self._lock:
            now = self._now()
            start = datetime.combine(now.date(), time.min, tzinfo=self.tz)
            headers = {
                "Authorization": f"Bearer {self.config.openai_admin_key}",
                "Content-Type": "application/json",
            }
            common: list[tuple[str, str | int]] = [
                ("start_time", int(start.timestamp())),
                ("end_time", int(now.timestamp()) + 1),
                ("bucket_width", "1d"),
                ("limit", 2),
            ]
            usage_params = list(common)
            cost_params = list(common)
            if self.config.openai_project_id:
                usage_params.append(("project_ids", self.config.openai_project_id))
                cost_params.append(("project_ids", self.config.openai_project_id))

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    usage_response, cost_response = await asyncio.gather(
                        client.get(
                            "https://api.openai.com/v1/organization/usage/completions",
                            headers=headers,
                            params=usage_params,
                        ),
                        client.get(
                            "https://api.openai.com/v1/organization/costs",
                            headers=headers,
                            params=cost_params,
                        ),
                    )
                usage_response.raise_for_status()
                cost_response.raise_for_status()

                input_tokens = 0
                output_tokens = 0
                for bucket in usage_response.json().get("data", []):
                    for result in bucket.get("results", []):
                        input_tokens += int(result.get("input_tokens") or 0)
                        output_tokens += int(result.get("output_tokens") or 0)

                cost_usd = 0.0
                for bucket in cost_response.json().get("data", []):
                    for result in bucket.get("results", []):
                        amount = result.get("amount") or {}
                        if str(amount.get("currency") or "").lower() == "usd":
                            cost_usd += float(amount.get("value") or 0)

                state = OpenAIUsageState(
                    date=now.date().isoformat(),
                    status="ok",
                    last_synced_at=now.isoformat(),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost_usd=round(cost_usd, 6),
                )
                self._write(state)
                return self._decorate(state)
            except Exception as exc:
                old = self.status()
                state = OpenAIUsageState(
                    date=self._today(),
                    status="error",
                    last_synced_at=old.get("last_synced_at"),
                    input_tokens=int(old.get("input_tokens") or 0),
                    output_tokens=int(old.get("output_tokens") or 0),
                    total_tokens=int(old.get("total_tokens") or 0),
                    cost_usd=old.get("cost_usd"),
                    error=f"{type(exc).__name__}: {exc}",
                )
                self._write(state)
                return self._decorate(state)

    def _write(self, state: OpenAIUsageState) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
