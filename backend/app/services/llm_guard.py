from dataclasses import dataclass

from backend.app.services.llm_budget import LLMBudgetService


@dataclass
class LLMExecutionDecision:
    allowed: bool
    mode: str
    reason: str | None = None


class LLMExecutionGuard:
    """LLM 장애/예산 소진 시 자동매매를 fail-closed 하기 위한 사전 가드."""

    def __init__(self):
        self.budget = LLMBudgetService()

    def before_cycle(self, estimated_input_tokens: int) -> LLMExecutionDecision:
        status = self.budget.status()

        if status["mode"] == "disabled":
            return LLMExecutionDecision(
                allowed=False,
                mode="disabled",
                reason="LLM is disabled.",
            )

        if not self.budget.can_start_cycle(estimated_input_tokens):
            return LLMExecutionDecision(
                allowed=False,
                mode="paused",
                reason="LLM token budget or per-cycle input limit reached.",
            )

        return LLMExecutionDecision(
            allowed=True,
            mode=status["mode"],
        )
