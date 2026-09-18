from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.llm_budget import LLMBudgetService


@dataclass
class CompactDecisionContext:
    algorithm_markdown: str
    news_context: str
    decision_context: str
    market_snapshot: dict
    account_snapshot: dict
    estimated_input_tokens: int
    budget_mode: str


class CompactContextBuilder:
    """매 사이클마다 7일치 원문 전체를 보내지 않기 위한 context builder."""

    def __init__(self):
        self.config = get_settings()
        self.algorithms = AlgorithmService()
        self.news = DailyMarkdownStore("news")
        self.decisions = DailyMarkdownStore("decisions")
        self.budget = LLMBudgetService()
        self.context_dir: Path = self.config.data_path / "context"
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        *,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> CompactDecisionContext:
        budget_status = self.budget.status()

        news_context = self._read_compact_or_fallback(
            compact_name="news_rolling.md",
            store=self.news,
            max_chars=self.config.llm_context_news_chars,
        )
        decision_context = self._read_compact_or_fallback(
            compact_name="decision_rolling.md",
            store=self.decisions,
            max_chars=self.config.llm_context_decision_chars,
        )

        # 예산 절약 모드에서는 과거 context를 절반으로 축소한다.
        if budget_status["mode"] == "conserve":
            news_context = self._tail(
                news_context,
                max(2000, self.config.llm_context_news_chars // 2),
            )
            decision_context = self._tail(
                decision_context,
                max(1500, self.config.llm_context_decision_chars // 2),
            )

        algorithm = self.algorithms.current()

        rough_text = "\n".join(
            [
                algorithm,
                news_context,
                decision_context,
                str(market_snapshot),
                str(account_snapshot),
            ]
        )
        estimated = self.budget.estimate_tokens(rough_text)

        return CompactDecisionContext(
            algorithm_markdown=algorithm,
            news_context=news_context,
            decision_context=decision_context,
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
            estimated_input_tokens=estimated,
            budget_mode=budget_status["mode"],
        )

    def _read_compact_or_fallback(
        self,
        *,
        compact_name: str,
        store: DailyMarkdownStore,
        max_chars: int,
    ) -> str:
        compact_path = self.context_dir / compact_name
        if compact_path.exists():
            return self._tail(
                compact_path.read_text(encoding="utf-8"),
                max_chars,
            )

        chunks: list[str] = []
        for day in reversed(store.available_dates(limit=7)):
            try:
                chunks.append(store.read(day))
            except Exception:
                continue

        return self._tail("\n\n".join(chunks), max_chars)

    @staticmethod
    def _tail(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
