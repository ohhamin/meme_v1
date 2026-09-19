from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.app.services.cycle_metrics import CycleMetricsStore
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.paper_order_journal import PaperOrderJournal
from backend.app.services.runtime_settings import RuntimeSettingsService


class MarketPerformanceService:
    """Mode-aware 7-day performance summary for stock/crypto tabs."""

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.metrics = CycleMetricsStore()
        self.paper_orders = PaperOrderJournal()

    def build(self, market: str) -> dict:
        if market not in {"stock", "crypto"}:
            raise ValueError("market must be stock or crypto")

        mode = self.runtime.get().mode
        metric_rows = []
        for record in self.metrics.recent(limit_days=7):
            if record.get("mode") != mode:
                continue
            accounts = record.get("accounts")
            if not isinstance(accounts, dict):
                continue
            account = accounts.get(market)
            if not isinstance(account, dict):
                continue
            try:
                equity = Decimal(str(account.get("equity")))
            except (TypeError, ValueError):
                continue
            if equity <= 0:
                continue
            metric_rows.append((record, account, equity))

        start_equity = metric_rows[0][2] if metric_rows else None
        end_equity = metric_rows[-1][2] if metric_rows else None
        return_pct = None
        max_drawdown = None
        if start_equity is not None and end_equity is not None:
            return_pct = self._pct(end_equity - start_equity, start_equity)
            peak = start_equity
            dd = Decimal("0")
            for _, _, equity in metric_rows:
                peak = max(peak, equity)
                if peak > 0:
                    dd = min(dd, self._pct(equity - peak, peak))
            max_drawdown = dd

        order_count = sum(
            int(record.get("order_count") or 0)
            for record, _, _ in metric_rows
        )
        decision_count = sum(
            int(record.get("decision_count") or 0)
            for record, _, _ in metric_rows
        )

        realized_pnl = None
        win_rate = None
        sell_count = None
        if mode == "paper":
            broker = PaperBroker(market)
            orders = self.paper_orders.recent(
                limit=2000,
                days=7,
                market=market,
                session_id=broker.session_id(),
            )
            sells = []
            for item in orders:
                if item.get("side") != "sell":
                    continue
                raw = item.get("realized_pnl")
                if raw is None:
                    continue
                try:
                    sells.append(Decimal(str(raw)))
                except (TypeError, ValueError):
                    continue
            wins = [value for value in sells if value > 0]
            sell_count = len(sells)
            realized_pnl = sum(sells, Decimal("0"))
            win_rate = (
                Decimal(len(wins)) / Decimal(len(sells)) * Decimal("100")
                if sells else Decimal("0")
            )

        return {
            "mode": mode,
            "market": market,
            "window_days": 7,
            "sample_count": len(metric_rows),
            "start_equity": str(start_equity) if start_equity is not None else None,
            "end_equity": str(end_equity) if end_equity is not None else None,
            "return_pct": str(return_pct) if return_pct is not None else None,
            "max_drawdown_pct": str(max_drawdown) if max_drawdown is not None else None,
            "decision_count": decision_count,
            "order_count": order_count,
            "sell_count": sell_count,
            "win_rate_pct": str(win_rate.quantize(Decimal("0.01"))) if win_rate is not None else None,
            "realized_pnl": str(realized_pnl) if realized_pnl is not None else None,
        }

    @staticmethod
    def _pct(value: Decimal, total: Decimal) -> Decimal:
        if total <= 0:
            return Decimal("0")
        return (value / total * Decimal("100")).quantize(Decimal("0.0001"))
