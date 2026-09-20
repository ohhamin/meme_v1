import calendar
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.services.openai_usage_sync import OpenAIUsageSyncService
from backend.app.services.runtime_settings import RuntimeSettingsService


@dataclass
class LLMUsageState:
    date: str
    month: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    month_input_tokens: int = 0
    month_output_tokens: int = 0
    month_total_tokens: int = 0


class LLMBudgetService:
    """로컬 LLM 토큰 예산 추적.

    실제 OpenAI 응답의 usage 값을 record_usage()에 넣어 누적한다.
    API 호출 전에는 estimate_tokens()로 대략적인 입력 크기를 확인한다.
    일일 사용량과 월 누적 사용량을 함께 보관한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "llm_usage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    def _today(self) -> str:
        return self._now().date().isoformat()

    def _month(self) -> str:
        return self._now().strftime("%Y-%m")

    def _empty(self) -> LLMUsageState:
        return LLMUsageState(
            date=self._today(),
            month=self._month(),
        )

    def _daily_budget(self) -> int:
        return RuntimeSettingsService().get().llm_daily_token_budget

    def _monthly_budget(self) -> int:
        daily = self._daily_budget()
        if daily <= 0:
            return 0
        now = self._now()
        return daily * calendar.monthrange(now.year, now.month)[1]

    def get(self) -> LLMUsageState:
        if not self.path.exists():
            state = self._empty()
            self._write(state)
            return state

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            # Legacy state migration: old files only had the current day's totals.
            if "month" not in raw:
                raw["month"] = str(raw.get("date") or self._today())[:7]
                raw["month_input_tokens"] = int(raw.get("input_tokens", 0))
                raw["month_output_tokens"] = int(raw.get("output_tokens", 0))
                raw["month_total_tokens"] = int(raw.get("total_tokens", 0))
            state = LLMUsageState(**raw)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            state = self._empty()

        current_month = self._month()
        current_day = self._today()

        if state.month != current_month:
            state = self._empty()
            self._write(state)
            return state

        if state.date != current_day:
            state.date = current_day
            state.input_tokens = 0
            state.output_tokens = 0
            state.total_tokens = 0
            self._write(state)

        return state

    def status(self) -> dict:
        state = self.get()
        daily_budget = self._daily_budget()
        monthly_budget = self._monthly_budget()
        openai_usage = OpenAIUsageSyncService().status()
        synced_today = (
            openai_usage.get("status") == "ok"
            and openai_usage.get("date") == self._today()
        )
        effective_daily_used = max(
            state.total_tokens,
            int(openai_usage.get("total_tokens") or 0) if synced_today else 0,
        )

        daily_remaining = (
            max(0, daily_budget - effective_daily_used)
            if daily_budget > 0
            else None
        )
        monthly_remaining = (
            max(0, monthly_budget - state.month_total_tokens)
            if monthly_budget > 0
            else None
        )
        percent_remaining = (
            int((daily_remaining / daily_budget) * 100)
            if daily_budget > 0 and daily_remaining is not None
            else None
        )

        if not self.config.llm_enabled:
            mode = "disabled"
        elif (
            daily_budget > 0
            and daily_remaining == 0
        ) or (
            monthly_budget > 0
            and monthly_remaining == 0
        ):
            mode = "paused"
        elif (
            percent_remaining is not None
            and percent_remaining <= self.config.llm_conserve_threshold_pct
        ):
            mode = "conserve"
        else:
            mode = "normal"

        return {
            "mode": mode,
            # Backward-compatible daily fields.
            "budget_tokens": daily_budget,
            "used_tokens": effective_daily_used,
            "input_tokens": state.input_tokens,
            "output_tokens": state.output_tokens,
            "remaining_tokens": daily_remaining,
            "percent_remaining": percent_remaining,
            "cycle_input_token_limit": self.config.llm_cycle_input_token_limit,
            "daily": {
                "budget_tokens": daily_budget,
                "used_tokens": effective_daily_used,
                "remaining_tokens": daily_remaining,
                "input_tokens": (
                    int(openai_usage.get("input_tokens") or 0)
                    if synced_today
                    else state.input_tokens
                ),
                "output_tokens": (
                    int(openai_usage.get("output_tokens") or 0)
                    if synced_today
                    else state.output_tokens
                ),
                "source": "openai" if synced_today else "local_response_usage",
                "local_used_tokens": state.total_tokens,
            },
            "openai_usage": openai_usage,
            "monthly": {
                "month": state.month,
                "budget_tokens": monthly_budget,
                "used_tokens": state.month_total_tokens,
                "remaining_tokens": monthly_remaining,
                "input_tokens": state.month_input_tokens,
                "output_tokens": state.month_output_tokens,
            },
        }

    def block_reason(self, estimated_input_tokens: int) -> str | None:
        if not self.config.llm_enabled:
            return "LLM is disabled."

        cycle_limit = self.config.llm_cycle_input_token_limit
        if cycle_limit > 0 and estimated_input_tokens > cycle_limit:
            return (
                f"Estimated cycle input {estimated_input_tokens:,} tokens exceeds "
                f"the per-cycle limit {cycle_limit:,}."
            )

        status = self.status()
        daily = status["daily"]
        monthly = status["monthly"]

        if (
            daily["budget_tokens"] > 0
            and daily["used_tokens"] + estimated_input_tokens
            > daily["budget_tokens"]
        ):
            return (
                f"Daily LLM budget would be exceeded "
                f"({daily['used_tokens']:,}/{daily['budget_tokens']:,} used)."
            )

        if (
            monthly["budget_tokens"] > 0
            and monthly["used_tokens"] + estimated_input_tokens
            > monthly["budget_tokens"]
        ):
            return (
                f"Monthly LLM budget would be exceeded "
                f"({monthly['used_tokens']:,}/{monthly['budget_tokens']:,} used)."
            )

        return None

    def can_start_cycle(self, estimated_input_tokens: int) -> bool:
        return self.block_reason(estimated_input_tokens) is None

    def record_usage(self, *, input_tokens: int, output_tokens: int) -> None:
        state = self.get()
        input_value = max(0, input_tokens)
        output_value = max(0, output_tokens)
        total_value = input_value + output_value

        state.input_tokens += input_value
        state.output_tokens += output_value
        state.total_tokens += total_value

        state.month_input_tokens += input_value
        state.month_output_tokens += output_value
        state.month_total_tokens += total_value
        self._write(state)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 3)

    def _write(self, state: LLMUsageState) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
