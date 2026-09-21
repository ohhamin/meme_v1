from backend.app.models.schemas import (
    DecisionPreviewResponse,
    DecisionCycleResult,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.backend_errors import BackendErrorStore
from backend.app.services.decision_engine import DecisionEngine
from backend.app.services.decision_store import DecisionMarkdownStore
from backend.app.services.openai_decision import (
    LLMDecisionClient,
    LLMUnavailableError,
)


class DecisionCycleService:
    """현재 단계의 LLM 판단 orchestration.

    Broker 주문과 Risk Guard 실행은 아직 연결하지 않는다.
    preview는 어떤 주문도 만들지 않는다.
    """

    def __init__(self):
        self.engine = DecisionEngine()
        self.llm = LLMDecisionClient()
        self.store = DecisionMarkdownStore()
        self.audit = AuditLogger()
        self.backend_errors = BackendErrorStore()

    async def preview(
        self,
        *,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> DecisionPreviewResponse:
        context = self.engine.build_context(
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )
        gate = self.engine.can_call_llm(context)

        if not gate.allowed:
            self.audit.write(
                "system",
                {
                    "event": "decision_preview_blocked",
                    "mode": gate.mode,
                    "reason": gate.reason,
                    "estimated_input_tokens": context.estimated_input_tokens,
                },
            )
            return DecisionPreviewResponse(
                status="blocked",
                mode=gate.mode,
                estimated_input_tokens=context.estimated_input_tokens,
                reason=gate.reason,
            )

        try:
            result = await self.llm.decide(context)
        except LLMUnavailableError as exc:
            self.backend_errors.report_exception(
                exc,
                source="decision_cycle.preview",
                context=(
                    f"mode={gate.mode}; "
                    f"estimated_input_tokens={context.estimated_input_tokens}"
                ),
            )
            self.audit.write(
                "system",
                {
                    "event": "decision_preview_llm_blocked",
                    "mode": gate.mode,
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc)[:1000],
                    "estimated_input_tokens": context.estimated_input_tokens,
                },
            )
            return DecisionPreviewResponse(
                status="blocked",
                mode="unavailable",
                estimated_input_tokens=context.estimated_input_tokens,
                reason=str(exc),
            )

        return DecisionPreviewResponse(
            status="completed",
            mode=gate.mode,
            estimated_input_tokens=context.estimated_input_tokens,
            result=result,
        )

    async def run_and_record(
        self,
        *,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> DecisionCycleResult | None:
        preview = await self.preview(
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )
        if preview.status != "completed" or preview.result is None:
            return None

        # Risk Guard / Broker 연결 전이므로 주문 가능 상태로 오해하지 않게 PENDING 기록.
        self.store.append_cycle(
            preview.result,
            risk_status="PENDING",
            risk_reason="Risk Guard is not connected yet.",
        )
        return preview.result
