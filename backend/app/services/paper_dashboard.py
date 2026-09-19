from collections import defaultdict
from decimal import Decimal

from backend.app.services.cycle_metrics import CycleMetricsStore
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.paper_order_journal import PaperOrderJournal


class PaperDashboardService:
    """Build a read-only Paper performance snapshot from persisted state."""

    def __init__(self):
        self.metrics = CycleMetricsStore()
        self.orders = PaperOrderJournal()

    def build(self) -> dict:
        stock = PaperBroker("stock").portfolio()
        crypto = PaperBroker("crypto").portfolio()
        accounts = [stock, crypto]

        total_equity = sum((item.equity for item in accounts), Decimal("0"))
        total_cash = sum((item.cash for item in accounts), Decimal("0"))
        total_initial = sum((item.initial_cash for item in accounts), Decimal("0"))
        total_day_start = sum((item.day_start_equity for item in accounts), Decimal("0"))
        total_daily_pnl = sum((item.daily_pnl for item in accounts), Decimal("0"))
        invested = max(Decimal("0"), total_equity - total_cash)

        positions = []
        for portfolio in accounts:
            for position in portfolio.positions:
                positions.append({
                    "market": position.market,
                    "symbol": position.symbol,
                    "name": position.name,
                    "quantity": str(position.quantity),
                    "average_price": str(position.average_price),
                    "last_price": str(position.last_price),
                    "invested_amount": str(position.invested_amount),
                    "market_value": str(position.market_value),
                    "return_rate": str(position.return_rate),
                    "realized_pnl": str(position.realized_pnl),
                    "decision_score": position.decision_score,
                })
        positions.sort(key=lambda item: Decimal(item["market_value"]), reverse=True)

        journal = self.orders.recent(limit=500, days=7)
        trading = self._trading_stats(journal)
        score_performance = self._score_performance(journal)
        recent_orders = journal[:10]

        return {
            "combined": {
                "equity": str(total_equity),
                "cash": str(total_cash),
                "invested": str(invested),
                "initial_cash": str(total_initial),
                "cumulative_return_pct": str(self._pct(total_equity - total_initial, total_initial)),
                "daily_pnl": str(total_daily_pnl),
                "daily_pnl_pct": str(self._pct(total_daily_pnl, total_day_start)),
                "daily_order_count": sum(item.daily_order_count for item in accounts),
                "position_count": len(positions),
                "max_drawdown_7d_pct": self._combined_drawdown_7d(),
            },
            "accounts": {
                "stock": self._account(stock),
                "crypto": self._account(crypto),
            },
            "positions": positions,
            "trading_7d": trading,
            "score_performance_7d": score_performance,
            # Backward-compatible aliases; values use the same 7-day window.
            "trading_30d": trading,
            "score_performance_30d": score_performance,
            "recent_orders": recent_orders,
        }

    @staticmethod
    def _account(portfolio) -> dict:
        initial = portfolio.initial_cash
        return {
            "market": portfolio.market,
            "equity": str(portfolio.equity),
            "cash": str(portfolio.cash),
            "initial_cash": str(initial),
            "cumulative_return_pct": str(
                PaperDashboardService._pct(portfolio.equity - initial, initial)
            ),
            "daily_pnl": str(portfolio.daily_pnl),
            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
            "daily_order_count": portfolio.daily_order_count,
            "position_count": len(portfolio.positions),
        }

    @staticmethod
    def _trading_stats(records: list[dict]) -> dict:
        sells = []
        by_symbol: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for record in records:
            if record.get("side") != "sell":
                continue
            raw = record.get("realized_pnl")
            if raw is None:
                continue
            try:
                pnl = Decimal(str(raw))
            except (ValueError, TypeError):
                continue
            sells.append(pnl)
            symbol = str(record.get("symbol") or "")
            if symbol:
                by_symbol[symbol] += pnl

        wins = [value for value in sells if value > 0]
        losses = [value for value in sells if value < 0]
        win_rate = (
            Decimal(len(wins)) / Decimal(len(sells)) * Decimal("100")
            if sells
            else Decimal("0")
        )
        avg_win = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")
        avg_loss = sum(losses, Decimal("0")) / len(losses) if losses else Decimal("0")

        symbols = [
            {"symbol": symbol, "realized_pnl": str(pnl)}
            for symbol, pnl in sorted(
                by_symbol.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        return {
            "order_count": len(records),
            "sell_count": len(sells),
            "win_count": len(wins),
            "loss_count": len(losses),
            "breakeven_count": len(sells) - len(wins) - len(losses),
            "win_rate_pct": str(win_rate.quantize(Decimal("0.01"))),
            "realized_pnl": str(sum(sells, Decimal("0"))),
            "average_win": str(avg_win),
            "average_loss": str(avg_loss),
            "symbols": symbols,
        }

    @staticmethod
    def _score_performance(records: list[dict]) -> list[dict]:
        buckets = [
            ("60-69", Decimal("60"), Decimal("70")),
            ("70-79", Decimal("70"), Decimal("80")),
            ("80-100", Decimal("80"), Decimal("101")),
        ]
        result = []

        for label, lower, upper in buckets:
            rows = []
            for record in records:
                if record.get("side") != "sell":
                    continue
                try:
                    score = Decimal(str(record.get("entry_score")))
                    pnl = Decimal(str(record.get("realized_pnl")))
                    return_pct = Decimal(
                        str(record.get("realized_return_pct"))
                    )
                except (ValueError, TypeError):
                    continue
                if lower <= score < upper:
                    rows.append((pnl, return_pct))

            wins = [row for row in rows if row[0] > 0]
            win_rate = (
                Decimal(len(wins)) / Decimal(len(rows)) * Decimal("100")
                if rows
                else Decimal("0")
            )
            realized_pnl = sum((row[0] for row in rows), Decimal("0"))
            avg_return = (
                sum((row[1] for row in rows), Decimal("0"))
                / Decimal(len(rows))
                if rows
                else Decimal("0")
            )

            result.append(
                {
                    "bucket": label,
                    "closed_trades": len(rows),
                    "wins": len(wins),
                    "win_rate_pct": str(
                        win_rate.quantize(Decimal("0.01"))
                    ),
                    "realized_pnl": str(realized_pnl),
                    "average_return_pct": str(
                        avg_return.quantize(Decimal("0.01"))
                    ),
                }
            )

        return result

    def _combined_drawdown_7d(self) -> float | None:
        series: list[Decimal] = []
        for record in self.metrics.recent(limit_days=7):
            if record.get("mode") != "paper":
                continue
            accounts = record.get("accounts")
            if not isinstance(accounts, dict):
                continue
            try:
                total = (
                    Decimal(str(accounts["stock"]["equity"]))
                    + Decimal(str(accounts["crypto"]["equity"]))
                )
            except (KeyError, TypeError, ValueError):
                continue
            if total > 0:
                series.append(total)

        if not series:
            return None

        peak = series[0]
        max_drawdown = Decimal("0")
        for value in series:
            peak = max(peak, value)
            if peak > 0:
                max_drawdown = min(
                    max_drawdown,
                    (value - peak) / peak * Decimal("100"),
                )
        return round(float(max_drawdown), 4)

    @staticmethod
    def _pct(value: Decimal, total: Decimal) -> Decimal:
        if total <= 0:
            return Decimal("0")
        return (value / total * Decimal("100")).quantize(Decimal("0.0001"))
