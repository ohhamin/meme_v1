from dataclasses import dataclass

from backend.app.services.llm_budget import LLMBudgetService
from backend.app.services.llm_runtime import LLMRuntimeStateService


@dataclass
class LLMExecutionDecision:
    allowed: bool
    mode: str
    reason: str | None = None


class LLMExecutionGuard:
    """LLM 장애/예산 소진 시 자동매매를 fail-closed 하기 위한 사전 가드."""

    def __init__(self):
        self.budget = LLMBudgetService()
        self.runtime = LLMRuntimeStateService()

    def before_cycle(self, estimated_input_tokens: int) -> LLMExecutionDecision:
        runtime = self.runtime.status()
        if runtime["mode"] != "normal":
            return LLMExecutionDecision(
                allowed=False,
                mode=runtime["mode"],
                reason=runtime.get("reason") or "LLM is temporarily unavailable.",
            )

        status = self.budget.status()

        if status["mode"] == "disabled":
            return LLMExecutionDecision(
                allowed=False,
                mode="disabled",
                reason="LLM is disabled.",
            )

        block_reason = self.budget.block_reason(estimated_input_tokens)
        if block_reason is not None:
            return LLMExecutionDecision(
                allowed=False,
                mode="paused",
                reason=block_reason,
            )

        return LLMExecutionDecision(
            allowed=True,
            mode=status["mode"],
        )
