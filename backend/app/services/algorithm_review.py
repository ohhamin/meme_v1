import json
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from backend.app.core.config import get_settings
from backend.app.models.schemas import AlgorithmProposalCreate
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.audit import AuditLogger
from backend.app.services.llm_budget import LLMBudgetService
from backend.app.services.llm_runtime import LLMRuntimeStateService
from backend.app.services.openai_usage_sync import OpenAIUsageSyncService
from backend.app.services.push import PushService
from backend.app.services.algorithm_metrics import AlgorithmMetricsService


_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "proposal_needed": {"type": "boolean"},
        "title": {"type": "string"},
        "reason": {"type": "string"},
        "rule_text": {"type": "string"},
    },
    "required": [
        "proposal_needed",
        "title",
        "reason",
        "rule_text",
    ],
    "additionalProperties": False,
}


class AlgorithmReviewService:
    """운영 데이터를 하루 단위로 검토해 전략 변경 '제안'만 만든다.

    제안은 pending MD로 저장될 뿐 자동 적용되지 않는다.
    """

    def __init__(self):
        self.config = get_settings()
        self.algorithms = AlgorithmService()
        self.audit = AuditLogger()
        self.budget = LLMBudgetService()
        self.runtime = LLMRuntimeStateService()
        self.openai_usage = OpenAIUsageSyncService()
        self.push = PushService()
        self.metrics = AlgorithmMetricsService()
        self.context_dir: Path = self.config.data_path / "context"
        self.client = (
            AsyncOpenAI(
                api_key=self.config.openai_api_key,
                max_retries=0,
                timeout=60.0,
            )
            if self.config.openai_api_key
            else None
        )

    def propose(
        self,
        *,
        title: str,
        reason: str,
        rule_text: str,
    ):
        return self.algorithms.create(
            AlgorithmProposalCreate(
                title=title,
                reason=reason,
                rule_text=rule_text,
            )
        )

    async def review(self) -> bool:
        # 사용자가 아직 검토하지 않은 제안이 있으면 새 제안을 쌓지 않는다.
        if self.algorithms.list_pending():
            return self._skip("pending_proposal_exists")

        if self.client is None:
            return self._skip("missing_api_key")

        runtime = self.runtime.status()
        if runtime["mode"] != "normal":
            return self._skip(f"llm_runtime_{runtime['mode']}")

        decision_context = self._read_context(
            "decision_rolling.md",
            self.config.llm_context_decision_chars,
        )
        if len(decision_context.strip()) < 300:
            return self._skip("not_enough_decision_history")

        news_context = self._read_context(
            "news_rolling.md",
            min(self.config.llm_context_news_chars, 8000),
        )
        current_algorithm = self.algorithms.current()
        metrics = self.metrics.build()

        if (
            metrics.get("decision_count", 0)
            < self.config.algorithm_review_min_decisions
        ):
            return self._skip("not_enough_decision_samples")

        payload = json.dumps(
            {
                "current_algorithm": current_algorithm,
                "recent_decisions": decision_context,
                "recent_news_context": news_context,
                "deterministic_metrics": metrics,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

        estimated = self.budget.estimate_tokens(payload)
        if not self.budget.can_start_cycle(estimated):
            return self._skip("llm_budget_blocked")

        try:
            response = await self.client.responses.create(
                model=self.config.openai_decision_model,
                instructions=(
                    "Review the trading algorithm conservatively using the supplied operating history. "
                    "Only propose a change when there is repeated, concrete evidence of a structural issue. "
                    "Use deterministic_metrics as the primary evidence for repeated blocks, churn, order outcomes, "
                    "and score_performance_30d. "
                    "The deterministic quant score, its weights, BUY/SELL thresholds, volatility targets, "
                    "Position Sizer, and Risk Guard are implemented in tested server code. Do NOT propose changing "
                    "those numeric rules through Markdown because a Markdown proposal cannot change executable math. "
                    "A proposal may only refine the AI veto/context layer: for example, when supplied news, macro data, "
                    "or data-quality conflicts should conservatively downgrade a quant BUY/SELL signal to HOLD. "
                    "Do not optimize from a single trade or a small sample. "
                    "Never propose removing or weakening kill switch, fail-closed behavior, "
                    "idempotency, token-budget controls, or hard risk limits. "
                    "A proposal must be a Markdown AI-veto/context rule, never executable code. "
                    "If evidence is insufficient, set proposal_needed=false and return empty strings "
                    "for title, reason, and rule_text."
                ),
                input=payload,
                reasoning={"effort": "medium"},
                max_output_tokens=1800,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "meme_v1_algorithm_review",
                        "strict": True,
                        "schema": _REVIEW_SCHEMA,
                    },
                    "verbosity": "low",
                },
                prompt_cache_key="meme_v1_algorithm_review_v1",
                store=False,
            )
        except RateLimitError as exc:
            self.runtime.handle_api_failure(
                kind="rate_limit",
                retry_after_seconds=self._retry_after_seconds(exc),
            )
            return self._error("rate_limit", exc)
        except (APITimeoutError, APIConnectionError) as exc:
            self.runtime.handle_api_failure(
                kind="transient",
                retry_after_seconds=60,
            )
            return self._error("connection_or_timeout", exc)
        except APIStatusError as exc:
            if exc.status_code >= 500:
                self.runtime.handle_api_failure(
                    kind="transient",
                    retry_after_seconds=60,
                )
                reason = "server_error"
            elif exc.status_code in {401, 403}:
                self.runtime.handle_api_failure(kind="auth")
                reason = "auth"
            else:
                self.runtime.handle_api_failure(kind="api_error")
                reason = f"http_{exc.status_code}"
            return self._error(reason, exc)

        if response.usage is not None:
            self.budget.record_usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        await self.openai_usage.refresh()

        try:
            data = json.loads(response.output_text)
        except (json.JSONDecodeError, TypeError):
            self.runtime.backoff(
                reason="invalid_algorithm_review",
                retry_after_seconds=60,
            )
            return self._skip("invalid_algorithm_review")

        if not data.get("proposal_needed"):
            self.runtime.resume()
            self.audit.write(
                "system",
                {
                    "event": "algorithm_review_completed",
                    "proposal_needed": False,
                    "model": self.config.openai_decision_model,
                },
            )
            return False

        title = str(data.get("title") or "").strip()
        reason = str(data.get("reason") or "").strip()
        rule_text = str(data.get("rule_text") or "").strip()
        if not title or not reason or not rule_text:
            return self._skip("incomplete_algorithm_proposal")

        proposal = self.propose(
            title=title,
            reason=reason,
            rule_text=rule_text,
        )
        self.runtime.resume()

        self.audit.write(
            "system",
            {
                "event": "algorithm_review_completed",
                "proposal_needed": True,
                "proposal_id": proposal.id,
                "model": self.config.openai_decision_model,
            },
        )
        self.push.send(
            title="알고리즘 개선 제안",
            body=proposal.title,
            data={
                "type": "algorithm_proposal",
                "proposal_id": proposal.id,
            },
        )
        return True

    def _read_context(self, name: str, max_chars: int) -> str:
        path = self.context_dir / name
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        return text[-max_chars:]

    def _skip(self, reason: str) -> bool:
        self.audit.write(
            "system",
            {
                "event": "algorithm_review_skipped",
                "reason": reason,
            },
        )
        return False

    def _error(self, reason: str, exc: Exception) -> bool:
        self.audit.write(
            "system",
            {
                "event": "algorithm_review_failed",
                "reason": reason,
                "error_type": type(exc).__name__,
            },
        )
        return False

    @staticmethod
    def _retry_after_seconds(exc: RateLimitError) -> int:
        try:
            raw = exc.response.headers.get("retry-after")
            if raw:
                return max(1, int(float(raw)))
        except (AttributeError, TypeError, ValueError):
            pass
        return 60
