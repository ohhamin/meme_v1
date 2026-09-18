from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from backend.app.brokers.toss_client import TossApiClient, TossApiError
from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    TossQuote,
    TossStockInfo,
)


class TossMarketDataAdapter:
    """Read-only Toss Securities market-data adapter for Korean stocks."""

    def __init__(self):
        self.client = TossApiClient()

    @property
    def configured(self) -> bool:
        return self.client.configured

    async def stock_info(
        self,
        symbols: Iterable[str],
    ) -> list[TossStockInfo]:
        normalized = self._normalize_symbols(symbols)
        if not normalized:
            return []

        payload = await self.client.get(
            "/api/v1/stocks",
            params={"symbols": ",".join(normalized)},
        )
        raw = payload.get("result") or []

        result: list[TossStockInfo] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            currency = str(item.get("currency") or "").upper()
            market = str(item.get("market") or "").upper()
            symbol = str(item.get("symbol") or "").upper()
            detail = item.get("koreanMarketDetail") or {}

            if currency != "KRW":
                continue

            suspended = bool(
                detail.get("krxTradingSuspended")
                or detail.get("nxtTradingSuspended")
            )

            result.append(
                TossStockInfo(
                    symbol=symbol,
                    name=str(item.get("name") or symbol),
                    english_name=(
                        str(item.get("englishName"))
                        if item.get("englishName") is not None
                        else None
                    ),
                    market=market,
                    security_type=str(
                        item.get("securityType") or "UNKNOWN"
                    ),
                    status=str(item.get("status") or "UNKNOWN"),
                    currency=currency,
                    nxt_supported=bool(detail.get("nxtSupported")),
                    trading_suspended=suspended,
                )
            )

        by_symbol = {item.symbol: item for item in result}
        return [
            by_symbol[symbol]
            for symbol in normalized
            if symbol in by_symbol
        ]

    async def quotes(
        self,
        symbols: Iterable[str],
    ) -> list[TossQuote]:
        normalized = self._normalize_symbols(symbols)
        if not normalized:
            return []

        payload = await self.client.get(
            "/api/v1/prices",
            params={"symbols": ",".join(normalized)},
        )
        raw = payload.get("result") or []
        now = datetime.now(timezone.utc)

        result: list[TossQuote] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            symbol = str(item.get("symbol") or "").upper()
            price = Decimal(str(item.get("lastPrice") or "0"))
            if not symbol or price <= 0:
                continue

            timestamp = self._parse_datetime(
                item.get("timestamp")
            )
            age = (
                max(0, int((now - timestamp).total_seconds()))
                if timestamp is not None
                else self.client.config.risk_max_data_age_seconds + 1
            )

            result.append(
                TossQuote(
                    symbol=symbol,
                    last_price=price,
                    currency=str(
                        item.get("currency") or "KRW"
                    ).upper(),
                    timestamp=timestamp,
                    data_age_seconds=age,
                )
            )

        by_symbol = {item.symbol: item for item in result}
        return [
            by_symbol[symbol]
            for symbol in normalized
            if symbol in by_symbol
        ]

    async def market_is_open(
        self,
        *,
        nxt_supported: bool,
        now: datetime | None = None,
    ) -> bool:
        payload = await self.client.get(
            "/api/v1/market-calendar/KR"
        )
        result = payload.get("result") or {}
        today = result.get("today") or {}
        integrated = today.get("integrated")

        if not isinstance(integrated, dict):
            return False

        current = now or datetime.now().astimezone()

        regular = integrated.get("regularMarket")
        if self._inside_session(current, regular):
            return True

        if nxt_supported:
            for key in ("preMarket", "afterMarket"):
                if self._inside_session(
                    current,
                    integrated.get(key),
                ):
                    return True

        return False

    async def snapshots(
        self,
        symbols: Iterable[str],
    ) -> list[MarketInstrumentSnapshot]:
        normalized = self._normalize_symbols(symbols)
        if not normalized:
            return []

        infos = await self.stock_info(normalized)
        quotes = await self.quotes(normalized)

        info_map = {item.symbol: item for item in infos}
        quote_map = {item.symbol: item for item in quotes}

        # Calendar is the same for all Korean stocks. Evaluate both session
        # modes once and combine with each stock's NXT support.
        regular_open = await self.market_is_open(
            nxt_supported=False
        )
        integrated_open = (
            regular_open
            or await self.market_is_open(
                nxt_supported=True
            )
        )

        snapshots: list[MarketInstrumentSnapshot] = []
        for symbol in normalized:
            info = info_map.get(symbol)
            quote = quote_map.get(symbol)

            if info is None or quote is None:
                continue
            if info.status != "ACTIVE":
                continue

            market_open = (
                integrated_open
                if info.nxt_supported
                else regular_open
            )
            if info.trading_suspended:
                market_open = False

            snapshots.append(
                MarketInstrumentSnapshot(
                    market="stock",
                    symbol=symbol,
                    name=info.name,
                    price=quote.last_price,
                    data_age_seconds=quote.data_age_seconds,
                    market_open=market_open,
                )
            )

        return snapshots

    @staticmethod
    def _normalize_symbols(
        symbols: Iterable[str],
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for raw in symbols:
            symbol = str(raw).strip().upper()
            if not symbol:
                continue
            if (
                len(symbol) != 6
                or not symbol.isdigit()
            ):
                raise ValueError(
                    f"Only 6-digit Korean symbols are supported: {symbol}"
                )
            if symbol not in seen:
                seen.add(symbol)
                result.append(symbol)

        if len(result) > 200:
            raise ValueError(
                "Toss market-data request supports up to 200 symbols."
            )

        return result

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def _inside_session(
        cls,
        now: datetime,
        session,
    ) -> bool:
        if not isinstance(session, dict):
            return False

        start = cls._parse_datetime(session.get("startTime"))
        end = cls._parse_datetime(session.get("endTime"))
        if start is None or end is None:
            return False

        current = now
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        else:
            current = current.astimezone(timezone.utc)

        return start <= current <= end
