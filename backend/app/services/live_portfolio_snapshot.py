from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from backend.app.brokers.toss_account import TossAccountAdapter
from backend.app.brokers.upbit_account import UpbitAccountAdapter
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.core.config import get_settings
from backend.app.models.schemas import PaperPortfolio, PaperPosition
from backend.app.services.live_daily_baseline import LiveDailyBaselineService
from backend.app.services.live_order_journal import LiveOrderJournal


class LivePortfolioSnapshotService:
    """Normalizes real broker accounts into the PositionSizer portfolio shape."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.upbit_accounts = UpbitAccountAdapter()
        self.upbit_market = UpbitMarketDataAdapter()
        self.toss_accounts = TossAccountAdapter()
        self.baselines = LiveDailyBaselineService()
        self.journal = LiveOrderJournal()

    async def upbit(self) -> PaperPortfolio:
        status = await self.upbit_accounts.balances()
        if not status.configured:
            raise RuntimeError(
                "Upbit API keys are not configured."
            )

        krw = next(
            (
                asset
                for asset in status.assets
                if asset.currency == "KRW"
            ),
            None,
        )
        cash = (
            krw.balance
            if krw is not None
            else Decimal("0")
        )
        krw_total = (
            krw.total
            if krw is not None
            else Decimal("0")
        )

        assets = [
            asset
            for asset in status.assets
            if asset.currency != "KRW"
            and asset.unit_currency == "KRW"
            and asset.total > 0
        ]
        markets = [
            f"KRW-{asset.currency}"
            for asset in assets
        ]
        quotes = (
            await self.upbit_market.quotes(markets)
            if markets
            else []
        )
        quote_map = {
            quote.market: quote
            for quote in quotes
        }

        positions: list[PaperPosition] = []
        market_value_total = Decimal("0")

        for asset in assets:
            market = f"KRW-{asset.currency}"
            quote = quote_map.get(market)
            if quote is None:
                raise RuntimeError(
                    f"Cannot value Upbit holding: {market}"
                )
            market_value = (
                asset.total * quote.trade_price
            )
            market_value_total += market_value
            invested = (
                asset.total * asset.avg_buy_price
            )
            return_rate = (
                (
                    (quote.trade_price - asset.avg_buy_price)
                    / asset.avg_buy_price
                    * Decimal("100")
                )
                if asset.avg_buy_price > 0
                else Decimal("0")
            )
            positions.append(
                PaperPosition(
                    market="crypto",
                    symbol=market,
                    name=quote.korean_name or market,
                    quantity=asset.balance,
                    average_price=asset.avg_buy_price,
                    last_price=quote.trade_price,
                    last_price_at=quote.timestamp,
                    last_market_open=True,
                    invested_amount=invested,
                    market_value=market_value,
                    return_rate=return_rate,
                    realized_pnl=Decimal("0"),
                )
            )

        equity = krw_total + market_value_total
        if equity <= 0:
            raise RuntimeError(
                "Upbit account equity is not positive."
            )
        baseline = self.baselines.get_or_create(
            broker="upbit",
            equity=equity,
        )
        daily_pnl = equity - baseline
        daily_pnl_pct = (
            daily_pnl / baseline * Decimal("100")
            if baseline > 0
            else Decimal("0")
        )

        return PaperPortfolio(
            market="crypto",
            date=datetime.now(self.tz).date().isoformat(),
            cash=cash,
            initial_cash=equity,
            day_start_equity=baseline,
            equity=equity,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            daily_order_count=self.journal.count_today(
                broker="upbit"
            ),
            positions=positions,
        )

    async def toss(self) -> PaperPortfolio:
        status = await self.toss_accounts.status()
        if not status.configured:
            raise RuntimeError(
                "Toss client credentials are not configured."
            )

        positions = [
            PaperPosition(
                market="stock",
                symbol=item.symbol,
                name=item.name,
                quantity=item.quantity,
                average_price=item.average_purchase_price,
                last_price=item.last_price,
                last_market_open=True,
                invested_amount=item.purchase_amount,
                market_value=item.market_value,
                return_rate=item.return_rate,
                realized_pnl=Decimal("0"),
            )
            for item in status.holdings
            if item.quantity > 0
        ]

        equity = status.cash_buying_power + sum(
            (
                item.market_value
                for item in status.holdings
            ),
            Decimal("0"),
        )
        if equity <= 0:
            raise RuntimeError(
                "Toss account equity is not positive."
            )

        baseline = self.baselines.get_or_create(
            broker="toss",
            equity=equity,
        )
        daily_pnl = equity - baseline
        daily_pnl_pct = (
            daily_pnl / baseline * Decimal("100")
            if baseline > 0
            else Decimal("0")
        )

        return PaperPortfolio(
            market="stock",
            date=datetime.now(self.tz).date().isoformat(),
            cash=status.cash_buying_power,
            initial_cash=equity,
            day_start_equity=baseline,
            equity=equity,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            daily_order_count=self.journal.count_today(
                broker="toss"
            ),
            positions=positions,
        )
