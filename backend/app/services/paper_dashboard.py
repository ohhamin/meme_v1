from decimal import Decimal

from backend.app.services.cycle_metrics import CycleMetricsStore
from backend.app.services.paper_broker import PaperBroker


class PaperDashboardService:
    """Build a read-only Paper performance snapshot from persisted state."""

    def __init__(self):
        self.metrics = CycleMetricsStore()

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

        cumulative_return_pct = self._pct(
            total_equity - total_initial,
            total_initial,
        )
        daily_pnl_pct = self._pct(
            total_daily_pnl,
            total_day_start,
        )

        positions = []
        for portfolio in accounts:
            for position in portfolio.positions:
                positions.append(
                    {
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
                    }
                )

        positions.sort(
            key=lambda item: Decimal(item["market_value"]),
            reverse=True,
        )

        return {
            "combined": {
                "equity": str(total_equity),
                "cash": str(total_cash),
                "invested": str(invested),
                "initial_cash": str(total_initial),
                "cumulative_return_pct": str(cumulative_return_pct),
                "daily_pnl": str(total_daily_pnl),
                "daily_pnl_pct": str(daily_pnl_pct),
                "daily_order_count": sum(
                    item.daily_order_count for item in accounts
                ),
                "position_count": len(positions),
                "max_drawdown_7d_pct": self._combined_drawdown_7d(),
            },
            "accounts": {
                "stock": self._account(stock),
                "crypto": self._account(crypto),
            },
            "positions": positions,
        }

    @staticmethod
    def _account(portfolio) -> dict:
        initial = portfolio.initial_cash
        cumulative = PaperDashboardService._pct(
            portfolio.equity - initial,
            initial,
        )
        return {
            "market": portfolio.market,
            "equity": str(portfolio.equity),
            "cash": str(portfolio.cash),
            "initial_cash": str(initial),
            "cumulative_return_pct": str(cumulative),
            "daily_pnl": str(portfolio.daily_pnl),
            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
            "daily_order_count": portfolio.daily_order_count,
            "position_count": len(portfolio.positions),
        }

    def _combined_drawdown_7d(self) -> float | None:
        series: list[Decimal] = []
        for record in self.metrics.recent(limit_days=7):
            if record.get("mode") != "paper":
                continue
            accounts = record.get("accounts")
            if not isinstance(accounts, dict):
                continue
            try:
                stock = Decimal(str(accounts["stock"]["equity"]))
                crypto = Decimal(str(accounts["crypto"]["equity"]))
            except (KeyError, TypeError, ValueError):
                continue
            total = stock + crypto
            if total > 0:
                series.append(total)

        if not series:
            return None

        peak = series[0]
        max_drawdown = Decimal("0")
        for value in series:
            peak = max(peak, value)
            if peak > 0:
                drawdown = (value - peak) / peak * Decimal("100")
                max_drawdown = min(max_drawdown, drawdown)

        return round(float(max_drawdown), 4)

    @staticmethod
    def _pct(value: Decimal, total: Decimal) -> Decimal:
        if total <= 0:
            return Decimal("0")
        return (value / total * Decimal("100")).quantize(
            Decimal("0.0001")
        )
