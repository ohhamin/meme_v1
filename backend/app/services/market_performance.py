from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.services.cycle_metrics import CycleMetricsStore
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_portfolio_snapshot import LivePortfolioSnapshotService
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.paper_order_journal import PaperOrderJournal
from backend.app.services.runtime_settings import RuntimeSettingsService


class MarketPerformanceService:
    """Seven-day, mode-aware market performance summary."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.runtime = RuntimeSettingsService()
        self.metrics = CycleMetricsStore()
        self.paper_orders = PaperOrderJournal()
        self.live_orders = LiveOrderJournal()
        self.live = LivePortfolioSnapshotService()

    async def build(self, market: str) -> dict:
        if market not in {"stock", "crypto"}:
            raise ValueError("market must be stock or crypto")

        mode = self.runtime.get().mode
        if mode == "paper":
            broker = PaperBroker(market)
            portfolio = broker.portfolio()
            orders = self.paper_orders.recent(
                limit=1000,
                days=7,
                market=market,
                session_id=broker.session_id,
            )
            trading = self._paper_trading(orders)
            session_id = broker.session_id
        else:
            portfolio = (
                await self.live.toss()
                if market == "stock"
                else await self.live.upbit()
            )
            trading = self._live_trading(market)
            session_id = None

        return {
            "mode": mode,
            "market": market,
            "window_days": 7,
            "session_id": session_id,
            "equity": str(portfolio.equity),
            "cash": str(portfolio.cash),
            "position_count": len(portfolio.positions),
            "daily_pnl_pct": str(portfolio.daily_pnl_pct),
            "return_7d_pct": self._equity_change(mode, market),
            **trading,
        }

    def _equity_change(self, mode: str, market: str) -> str | None:
        series: list[Decimal] = []
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
            if equity > 0:
                series.append(equity)

        if len(series) < 2 or series[0] <= 0:
            return None
        value = (series[-1] - series[0]) / series[0] * Decimal("100")
        return str(value.quantize(Decimal("0.01")))

    @staticmethod
    def _paper_trading(records: list[dict]) -> dict:
        sells: list[Decimal] = []
        for record in records:
            if record.get("side") != "sell":
                continue
            try:
                sells.append(Decimal(str(record.get("realized_pnl"))))
            except (TypeError, ValueError):
                continue

        wins = sum(1 for value in sells if value > 0)
        win_rate = (
            Decimal(wins) / Decimal(len(sells)) * Decimal("100")
            if sells
            else Decimal("0")
        )
        return {
            "order_count_7d": len(records),
            "closed_trades_7d": len(sells),
            "win_rate_7d_pct": str(win_rate.quantize(Decimal("0.01"))),
            "realized_pnl_7d": str(sum(sells, Decimal("0"))),
        }

    def _live_trading(self, market: str) -> dict:
        cutoff = datetime.now(self.tz) - timedelta(days=7)
        broker = "toss" if market == "stock" else "upbit"
        count = 0
        try:
            records = self.live_orders.list_records(limit=500)
        except Exception:
            records = []

        for record in records:
            if getattr(record, "broker", None) != broker:
                continue
            created = getattr(record, "created_at", None)
            if created is None:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=self.tz)
            if created.astimezone(self.tz) >= cutoff:
                count += 1

        return {
            "order_count_7d": count,
            "closed_trades_7d": None,
            "win_rate_7d_pct": None,
            "realized_pnl_7d": None,
        }
