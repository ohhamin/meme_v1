from backend.app.core.config import get_settings
from backend.app.services.context_compactor import (
    CompactContextBuilder,
    CompactDecisionContext,
)
from backend.app.services.llm_guard import LLMExecutionDecision, LLMExecutionGuard


class DecisionEngine:
    """LLM 연결 전 단계의 context/budget orchestration.

    실제 BUY/SELL/HOLD 생성 및 주문 연결은 다음 구현 단계에서 추가한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.contexts = CompactContextBuilder()
        self.guard = LLMExecutionGuard()

    def build_context(
        self,
        *,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> CompactDecisionContext:
        return self.contexts.build(
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )

    def can_call_llm(
        self,
        context: CompactDecisionContext,
    ) -> LLMExecutionDecision:
        return self.guard.before_cycle(context.estimated_input_tokens)

    def clamp_next_check(self, proposed_minutes: int) -> int:
        return self.config.clamp_decision_interval(proposed_minutes)
