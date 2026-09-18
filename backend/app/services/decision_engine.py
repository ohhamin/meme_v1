from dataclasses import dataclass

from backend.app.core.config import get_settings
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.file_store import DailyMarkdownStore


@dataclass
class DecisionContext:
    algorithm_markdown: str
    news_by_date: dict[str, str]
    market_snapshot: dict
    account_snapshot: dict


class DecisionEngine:
    """LLM 연결 전 단계의 context builder.

    실제 BUY/SELL/HOLD 생성 및 주문 연결은 다음 구현 단계에서 추가한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.algorithms = AlgorithmService()
        self.news = DailyMarkdownStore("news")

    def build_context(
        self,
        *,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> DecisionContext:
        news_by_date: dict[str, str] = {}
        for day in self.news.available_dates(limit=7):
            news_by_date[day] = self.news.read(day)

        return DecisionContext(
            algorithm_markdown=self.algorithms.current(),
            news_by_date=news_by_date,
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot,
        )

    def clamp_next_check(self, proposed_minutes: int) -> int:
        return self.config.clamp_decision_interval(proposed_minutes)
