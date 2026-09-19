from decimal import Decimal

from backend.app.brokers.toss_account import TossAccountAdapter
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_account import UpbitAccountAdapter
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.services.live_daily_baseline import LiveDailyBaselineService
from backend.app.services.live_order_journal import LiveOrderJournal


class LiveRiskSnapshotError(RuntimeError):
    pass


class LiveRiskSnapshotService:
    """Builds broker-separated live account snapshots for deterministic Risk Guard."""

    def __init__(self):
        self.upbit_accounts = UpbitAccountAdapter()
        self.upbit_market = UpbitMarketDataAdapter()
        self.toss_accounts = TossAccountAdapter()
        self.toss_market = TossMarketDataAdapter()
        self.baselines = LiveDailyBaselineService()
        self.journal = LiveOrderJournal()

    def _pending_buy_records(self):
        return [
            record
            for record in self.journal.unresolved(limit=500)
            if record.side == "buy"
        ]

    async def total_open_positions(self) -> int:
        upbit = await self.upbit_accounts.balances()
        crypto_count = sum(
            1
            for asset in upbit.assets
            if asset.currency != "KRW"
            and asset.unit_currency == "KRW"
            and asset.total > 0
        )

        toss = await self.toss_accounts.status()
        held_keys = {
            (
                "crypto",
                f"KRW-{asset.currency}",
            )
            for asset in upbit.assets
            if asset.currency != "KRW"
            and asset.unit_currency == "KRW"
            and asset.total > 0
        }
        held_keys.update(
            (
                "stock",
                item.symbol,
            )
            for item in toss.holdings
            if item.quantity > 0
        )

        pending_keys = {
            (
                record.market,
                record.symbol.strip().upper(),
            )
            for record in self._pending_buy_records()
        }

        return len(held_keys | pending_keys)

    async def upbit(
        self,
        symbol: str,
    ) -> dict:
        market = symbol.strip().upper()
        status = await self.upbit_accounts.balances()
        if not status.configured:
            raise LiveRiskSnapshotError(
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
        available_cash = (
            krw.balance
            if krw is not None
            else Decimal("0")
        )
        krw_total = (
            krw.total
            if krw is not None
            else Decimal("0")
        )

        crypto_assets = [
            asset
            for asset in status.assets
            if asset.currency != "KRW"
            and asset.unit_currency == "KRW"
            and asset.total > 0
        ]
        markets = {
            f"KRW-{asset.currency}"
            for asset in crypto_assets
        }
        markets.add(market)

        quotes = await self.upbit_market.quotes(
            sorted(markets)
        )
        quote_map = {
            quote.market: quote
            for quote in quotes
        }

        missing_held = [
            f"KRW-{asset.currency}"
            for asset in crypto_assets
            if f"KRW-{asset.currency}" not in quote_map
        ]
        if missing_held:
            raise LiveRiskSnapshotError(
                "Cannot value all Upbit holdings: "
                + ", ".join(missing_held)
            )

        target_quote = quote_map.get(market)
        if target_quote is None:
            raise LiveRiskSnapshotError(
                f"Upbit quote is unavailable: {market}"
            )

        market_value = Decimal("0")
        for asset in crypto_assets:
            quote = quote_map[f"KRW-{asset.currency}"]
            market_value += (
                asset.total * quote.trade_price
            )

        equity = krw_total + market_value
        if equity <= 0:
            raise LiveRiskSnapshotError(
                "Upbit account equity is not positive."
            )

        base_currency = market.split("-", 1)[1]
        target_asset = next(
            (
                asset
                for asset in crypto_assets
                if asset.currency == base_currency
            ),
            None,
        )
        position_total = (
            target_asset.total
            if target_asset is not None
            else Decimal("0")
        )
        position_value = (
            position_total * target_quote.trade_price
        )
        pending_buy_notional = sum(
            (
                record.notional
                for record in self._pending_buy_records()
                if record.broker == "upbit"
                and record.symbol.strip().upper() == market
            ),
            Decimal("0"),
        )
        reserved_cash = sum(
            (
                record.notional
                for record in self._pending_buy_records()
                if record.broker == "upbit"
            ),
            Decimal("0"),
        )

        return {
            "broker": "upbit",
            "market": "crypto",
            "symbol": market,
            "price": target_quote.trade_price,
            "data_age_seconds": target_quote.data_age_seconds,
            "market_open": True,
            "portfolio_equity": equity,
            "available_cash": max(
                Decimal("0"),
                available_cash - reserved_cash,
            ),
            "position_value": position_value + pending_buy_notional,
            "position_quantity": position_total,
            "open_position_count": await self.total_open_positions(),
            "daily_pnl_pct": self.baselines.daily_pnl_pct(
                broker="upbit",
                equity=equity,
            ),
            "daily_order_count": self.journal.count_today(
                broker="upbit"
            ),
        }

    async def toss(
        self,
        symbol: str,
    ) -> dict:
        normalized = symbol.strip().upper()
        status = await self.toss_accounts.status()
        if not status.configured:
            raise LiveRiskSnapshotError(
                "Toss client credentials are not configured."
            )

        snapshots = await self.toss_market.snapshots(
            [normalized]
        )
        if len(snapshots) != 1:
            raise LiveRiskSnapshotError(
                f"Toss market snapshot is unavailable: {normalized}"
            )
        instrument = snapshots[0]

        equity = status.cash_buying_power + sum(
            (
                item.market_value
                for item in status.holdings
            ),
            Decimal("0"),
        )
        if equity <= 0:
            raise LiveRiskSnapshotError(
                "Toss account equity is not positive."
            )

        holding = next(
            (
                item
                for item in status.holdings
                if item.symbol == normalized
            ),
            None,
        )

        pending_buy_notional = sum(
            (
                record.notional
                for record in self._pending_buy_records()
                if record.broker == "toss"
                and record.symbol.strip().upper() == normalized
            ),
            Decimal("0"),
        )
        reserved_cash = sum(
            (
                record.notional
                for record in self._pending_buy_records()
                if record.broker == "toss"
            ),
            Decimal("0"),
        )

        return {
            "broker": "toss",
            "market": "stock",
            "symbol": normalized,
            "price": instrument.price,
            "data_age_seconds": instrument.data_age_seconds,
            "market_open": instrument.market_open,
            "portfolio_equity": equity,
            "available_cash": max(
                Decimal("0"),
                status.cash_buying_power - reserved_cash,
            ),
            "position_value": (
                (
                    holding.market_value
                    if holding is not None
                    else Decimal("0")
                )
                + pending_buy_notional
            ),
            "position_quantity": (
                holding.quantity
                if holding is not None
                else Decimal("0")
            ),
            "open_position_count": await self.total_open_positions(),
            "daily_pnl_pct": self.baselines.daily_pnl_pct(
                broker="toss",
                equity=equity,
            ),
            "daily_order_count": self.journal.count_today(
                broker="toss"
            ),
        }
