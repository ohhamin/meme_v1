from decimal import Decimal

from backend.app.services.paper_order_journal import PaperOrderJournal
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.trading import TradingService


class MarketPerformanceService:
    """Mode-aware 7-day performance summary for stock/crypto tabs."""

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.trading = TradingService()
        self.orders = PaperOrderJournal()

    async def build(self, market: str) -> dict:
        if market not in {"stock", "crypto"}:
            raise ValueError("market must be stock or crypto")

        runtime = self.runtime.get()
        positions = (
            await self.trading.stock_positions()
            if market == "stock"
            else await self.trading.crypto_positions()
        )

        invested = Decimal("0")
        market_value = Decimal("0")
        for item in positions:
            invested += self._decimal(item.get("invested_amount"))
            market_value += self._decimal(item.get("market_value"))

        unrealized = market_value - invested
        return_pct = (
            unrealized / invested * Decimal("100")
            if invested > 0
            else Decimal("0")
        )

        result = {
            "mode": runtime.mode,
            "market": market,
            "position_count": len(positions),
            "invested_amount": str(invested),
            "market_value": str(market_value),
            "unrealized_pnl": str(unrealized),
            "return_pct": str(return_pct.quantize(Decimal("0.01"))),
            "window_days": 7,
            "realized_pnl_7d": None,
            "closed_trades_7d": None,
            "win_rate_7d_pct": None,
        }

        if runtime.mode == "paper":
            rows = [
                row
                for row in self.orders.recent(limit=2000, days=7)
                if row.get("market") == market
                and row.get("side") == "sell"
                and row.get("realized_pnl") is not None
            ]
            pnls = [self._decimal(row.get("realized_pnl")) for row in rows]
            wins = [value for value in pnls if value > 0]
            result["realized_pnl_7d"] = str(sum(pnls, Decimal("0")))
            result["closed_trades_7d"] = len(pnls)
            result["win_rate_7d_pct"] = str(
                (
                    Decimal(len(wins))
                    / Decimal(len(pnls))
                    * Decimal("100")
                ).quantize(Decimal("0.01"))
                if pnls
                else Decimal("0.00")
            )

        return result

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")
