from collections import Counter, defaultdict
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.paper_order_journal import PaperOrderJournal
from backend.app.services.cycle_metrics import CycleMetricsStore


class AlgorithmMetricsService:
    """Build compact deterministic evidence for algorithm-review prompts.

    This service does not call an LLM and does not change trading behavior.
    """

    def __init__(self):
        self.config = get_settings()
        self.decisions = DailyMarkdownStore("decisions")
        self.live_orders = LiveOrderJournal()
        self.cycle_metrics = CycleMetricsStore()
        self.paper_orders = PaperOrderJournal()

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
            "performance": self._performance_summary(),
            "score_performance_30d": self._score_performance_30d(),
        }

    def _score_performance_30d(self) -> dict:
        records = self.paper_orders.recent(limit=1000, days=30)
        buckets = [
            ("60-69", 60, 70),
            ("70-79", 70, 80),
            ("80-100", 80, 101),
        ]
        result = {}
        total_closed = 0

        for label, lower, upper in buckets:
            rows = []
            for record in records:
                if record.get("side") != "sell":
                    continue
                try:
                    score = float(record.get("entry_score"))
                    pnl = float(record.get("realized_pnl"))
                    return_pct = float(record.get("realized_return_pct"))
                except (TypeError, ValueError):
                    continue
                if lower <= score < upper:
                    rows.append((pnl, return_pct))

            closed = len(rows)
            total_closed += closed
            wins = sum(1 for pnl, _ in rows if pnl > 0)
            losses = sum(1 for pnl, _ in rows if pnl < 0)
            realized = sum(pnl for pnl, _ in rows)
            average_return = (
                sum(value for _, value in rows) / closed
                if closed
                else 0.0
            )
            result[label] = {
                "closed_trades": closed,
                "wins": wins,
                "losses": losses,
                "win_rate_pct": round(wins / closed * 100, 2) if closed else 0.0,
                "realized_pnl": round(realized, 4),
                "average_return_pct": round(average_return, 4),
                "sample_sufficient": closed >= 10,
            }

        return {
            "window_days": 30,
            "total_closed_trades": total_closed,
            "minimum_bucket_sample_for_threshold_change": 10,
            "buckets": result,
        }

    def _performance_summary(self) -> dict:
        records = self.cycle_metrics.recent(limit_days=7)
        result: dict[str, dict] = {}

        for market in ("stock", "crypto"):
            series: list[float] = []
            for record in records:
                accounts = record.get("accounts")
                if not isinstance(accounts, dict):
                    continue
                account = accounts.get(market)
                if not isinstance(account, dict):
                    continue
                try:
                    equity = float(account.get("equity"))
                except (TypeError, ValueError):
                    continue
                if equity > 0:
                    series.append(equity)

            if not series:
                result[market] = {
                    "samples": 0,
                    "change_pct": None,
                    "max_drawdown_pct": None,
                }
                continue

            start = series[0]
            end = series[-1]
            change_pct = (
                (end - start) / start * 100
                if start > 0
                else 0.0
            )

            peak = series[0]
            max_drawdown = 0.0
            for value in series:
                peak = max(peak, value)
                if peak > 0:
                    drawdown = (
                        (value - peak)
                        / peak
                        * 100
                    )
                    max_drawdown = min(
                        max_drawdown,
                        drawdown,
                    )

            result[market] = {
                "samples": len(series),
                "start_equity": str(start),
                "end_equity": str(end),
                "change_pct": round(change_pct, 4),
                "max_drawdown_pct": round(max_drawdown, 4),
            }

        return result

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
