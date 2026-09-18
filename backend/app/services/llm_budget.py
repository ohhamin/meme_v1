import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


@dataclass
class LLMUsageState:
    date: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class LLMBudgetService:
    """로컬 LLM 토큰 예산 추적.

    실제 OpenAI 응답의 usage 값을 record_usage()에 넣어 누적한다.
    API 호출 전에는 estimate_tokens()로 대략적인 입력 크기를 확인한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.path: Path = self.config.data_path / "state" / "llm_usage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _today(self) -> str:
        return datetime.now(self.tz).date().isoformat()

    def _empty(self) -> LLMUsageState:
        return LLMUsageState(date=self._today())

    def get(self) -> LLMUsageState:
        if not self.path.exists():
            state = self._empty()
            self._write(state)
            return state

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            state = LLMUsageState(**raw)
        except (OSError, json.JSONDecodeError, TypeError):
            state = self._empty()

        if state.date != self._today():
            state = self._empty()
            self._write(state)

        return state

    def status(self) -> dict:
        state = self.get()
        budget = self.config.llm_daily_token_budget
        remaining = max(0, budget - state.total_tokens) if budget > 0 else None
        percent_remaining = (
            int((remaining / budget) * 100)
            if budget > 0 and remaining is not None
            else None
        )

        if not self.config.llm_enabled:
            mode = "disabled"
        elif budget > 0 and remaining == 0:
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
            "budget_tokens": budget,
            "used_tokens": state.total_tokens,
            "input_tokens": state.input_tokens,
            "output_tokens": state.output_tokens,
            "remaining_tokens": remaining,
            "percent_remaining": percent_remaining,
        }

    def can_start_cycle(self, estimated_input_tokens: int) -> bool:
        if not self.config.llm_enabled:
            return False

        if estimated_input_tokens > self.config.llm_cycle_input_token_limit:
            return False

        budget = self.config.llm_daily_token_budget
        if budget <= 0:
            return True

        state = self.get()
        return state.total_tokens + estimated_input_tokens <= budget

    def record_usage(self, *, input_tokens: int, output_tokens: int) -> None:
        state = self.get()
        state.input_tokens += max(0, input_tokens)
        state.output_tokens += max(0, output_tokens)
        state.total_tokens += max(0, input_tokens) + max(0, output_tokens)
        self._write(state)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # 모델별 tokenizer가 연결되기 전 사용할 보수적 근사치.
        # 실제 호출 후에는 반드시 API usage 값을 record_usage()에 기록한다.
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
