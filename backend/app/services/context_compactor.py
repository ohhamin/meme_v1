from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.llm_budget import LLMBudgetService
from backend.app.services.macro_market_context import MacroMarketContextService


@dataclass
class CompactDecisionContext:
    algorithm_markdown: str
    news_context: str
    decision_context: str
    macro_context: dict
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
        self.macro = MacroMarketContextService()
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
        macro_context = self.macro.read()
        compact_market_snapshot = self._compact_market_snapshot(
            market_snapshot
        )
        compact_account_snapshot = self._compact_account_snapshot(
            account_snapshot
        )

        estimated = self._estimate(
            algorithm=algorithm,
            news_context=news_context,
            decision_context=decision_context,
            macro_context=macro_context,
            market_snapshot=compact_market_snapshot,
            account_snapshot=compact_account_snapshot,
        )

        # Optional historical context must never block an otherwise valid cycle.
        # Keep a safety margin for JSON/instruction overhead and trim the oldest
        # news/decision context until the request fits the configured cycle cap.
        cycle_limit = self.config.llm_cycle_input_token_limit
        target = max(1000, cycle_limit - 750) if cycle_limit > 0 else 0
        while target > 0 and estimated > target and (
            len(news_context) > 1000 or len(decision_context) > 750
        ):
            if len(news_context) >= len(decision_context) and len(news_context) > 1000:
                news_context = self._tail(
                    news_context,
                    max(1000, int(len(news_context) * 0.8)),
                )
            elif len(decision_context) > 750:
                decision_context = self._tail(
                    decision_context,
                    max(750, int(len(decision_context) * 0.8)),
                )

            estimated = self._estimate(
                algorithm=algorithm,
                news_context=news_context,
                decision_context=decision_context,
                macro_context=macro_context,
                market_snapshot=market_snapshot,
                account_snapshot=account_snapshot,
            )

        return CompactDecisionContext(
            algorithm_markdown=algorithm,
            news_context=news_context,
            decision_context=decision_context,
            macro_context=macro_context,
            market_snapshot=compact_market_snapshot,
            account_snapshot=compact_account_snapshot,
            estimated_input_tokens=estimated,
            budget_mode=budget_status["mode"],
        )

    @staticmethod
    def _compact_market_snapshot(snapshot: dict) -> dict:
        """Keep only decision-relevant per-instrument fields for the LLM.

        Full broker snapshots remain in the trading pipeline; this copy is only
        for prompt context. The deterministic quant score remains authoritative.
        """
        raw = snapshot.get("instruments")
        if not isinstance(raw, list):
            return snapshot

        feature_keys = (
            "features_available",
            "feature_interval",
            "feature_samples",
            "quant_model_version",
            "quant_score",
            "quant_action",
            "quant_risk_scale",
            "quant_penalty",
            "quant_components",
            "return_short_pct",
            "return_medium_pct",
            "return_long_pct",
            "positive_day_ratio_medium",
            "positive_day_ratio_long",
            "sma_short_gap_pct",
            "sma_long_gap_pct",
            "realized_volatility_pct",
            "volume_recent_ratio",
        )

        instruments: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            features = item.get("features")
            compact_features = {}
            if isinstance(features, dict):
                compact_features = {
                    key: features[key]
                    for key in feature_keys
                    if key in features
                }

            instruments.append(
                {
                    "market": item.get("market"),
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "data_age_seconds": item.get("data_age_seconds"),
                    "market_open": item.get("market_open"),
                    "features": compact_features,
                }
            )

        return {"instruments": instruments}

    @staticmethod
    def _compact_account_snapshot(snapshot: dict) -> dict:
        """Drop account fields that do not affect BUY/SELL/HOLD reasoning."""
        if not isinstance(snapshot, dict):
            return snapshot

        result: dict = {}
        for market in ("stock", "crypto"):
            account = snapshot.get(market)
            if not isinstance(account, dict):
                continue

            positions = account.get("positions")
            compact_positions: list[dict] = []
            if isinstance(positions, list):
                for position in positions:
                    if not isinstance(position, dict):
                        continue
                    compact_positions.append(
                        {
                            key: position.get(key)
                            for key in (
                                "symbol",
                                "name",
                                "quantity",
                                "average_price",
                                "last_price",
                                "market_value",
                                "return_rate",
                                "decision_score",
                            )
                            if key in position
                        }
                    )

            result[market] = {
                key: account.get(key)
                for key in (
                    "broker",
                    "cash",
                    "equity",
                    "daily_pnl_pct",
                    "daily_order_count",
                )
                if key in account
            }
            result[market]["positions"] = compact_positions

        policy = snapshot.get("portfolio_policy")
        if isinstance(policy, dict):
            result["portfolio_policy"] = policy

        return result

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

    def _estimate(
        self,
        *,
        algorithm: str,
        news_context: str,
        decision_context: str,
        macro_context: dict,
        market_snapshot: dict,
        account_snapshot: dict,
    ) -> int:
        rough_text = "\n".join(
            [
                algorithm,
                news_context,
                decision_context,
                str(macro_context),
                str(market_snapshot),
                str(account_snapshot),
            ]
        )
        return self.budget.estimate_tokens(rough_text)

    @staticmethod
    def _tail(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
