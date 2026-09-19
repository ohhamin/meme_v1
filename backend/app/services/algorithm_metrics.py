from collections import Counter, defaultdict
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.paper_broker import PaperBroker


class AlgorithmMetricsService:
    """Build compact deterministic evidence for algorithm-review prompts.

    This service does not call an LLM and does not change trading behavior.
    """

    def __init__(self):
        self.config = get_settings()
        self.decisions = DailyMarkdownStore("decisions")
        self.live_orders = LiveOrderJournal()

    def build(self) -> dict:
        action_counts: Counter[str] = Counter()
        risk_counts: Counter[str] = Counter()
        block_reasons: Counter[str] = Counter()
        execution_modes: Counter[str] = Counter()
        symbol_actions: defaultdict[str, list[str]] = defaultdict(list)
        cycle_count = 0
        decision_count = 0
        days = 0

        for day in reversed(self.decisions.available_dates(limit=7)):
            try:
                text = self.decisions.read(day)
            except Exception:
                continue
            days += 1

            current_symbol: str | None = None
            for raw_line in text.splitlines():
                line = raw_line.strip()

                if line.startswith("## ") and "Decision Cycle" in line:
                    cycle_count += 1
                    current_symbol = None
                    continue

                if line.startswith("### "):
                    current_symbol = line.removeprefix("### ").strip()
                    continue

                if line.startswith("- Execution Mode:"):
                    execution_modes[
                        line.split(":", 1)[1].strip().upper()
                    ] += 1
                    continue

                if line.startswith("- Action:"):
                    action = line.split(":", 1)[1].strip().upper()
                    if action in {"BUY", "SELL", "HOLD"}:
                        action_counts[action] += 1
                        decision_count += 1
                        if current_symbol:
                            symbol_actions[current_symbol].append(action)
                    continue

                if line.startswith("- Risk Guard:"):
                    value = line.split(":", 1)[1].strip().upper()
                    risk_counts[value] += 1
                    continue

                if line.startswith("- Block Reason:"):
                    reason = line.split(":", 1)[1].strip()
                    for item in reason.split("|"):
                        value = item.strip()
                        if value:
                            block_reasons[value] += 1

        reversals = Counter()
        for symbol, actions in symbol_actions.items():
            previous_direction: str | None = None
            for action in actions:
                if action not in {"BUY", "SELL"}:
                    continue
                if (
                    previous_direction is not None
                    and previous_direction != action
                ):
                    reversals[symbol] += 1
                previous_direction = action

        live_statuses = Counter(
            record.status
            for record in self.live_orders.list_records(limit=500)
        )

        return {
            "window_days_with_decisions": days,
            "decision_cycles": cycle_count,
            "decision_count": decision_count,
            "actions": dict(action_counts),
            "risk_guard": dict(risk_counts),
            "execution_modes": dict(execution_modes),
            "top_block_reasons": [
                {
                    "reason": reason,
                    "count": count,
                }
                for reason, count in block_reasons.most_common(10)
            ],
            "direction_reversals": [
                {
                    "symbol": symbol,
                    "count": count,
                }
                for symbol, count in reversals.most_common(10)
            ],
            "paper_accounts": {
                "stock": self._paper_summary("stock"),
                "crypto": self._paper_summary("crypto"),
            },
            "live_order_journal": {
                "statuses": dict(live_statuses),
                "unresolved": len(
                    self.live_orders.unresolved(limit=500)
                ),
            },
        }

    @staticmethod
    def _paper_summary(market: str) -> dict:
        portfolio = PaperBroker(market).portfolio()
        return {
            "equity": str(portfolio.equity),
            "cash": str(portfolio.cash),
            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
            "daily_order_count": portfolio.daily_order_count,
            "position_count": len(portfolio.positions),
        }
