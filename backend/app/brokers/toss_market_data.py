import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from backend.app.brokers.toss_client import TossApiClient, TossApiError
from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    TossQuote,
    TossStockInfo,
)
from backend.app.services.technical_features import TechnicalFeatureService


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

            nxt_supported = bool(detail.get("nxtSupported"))
            krx_suspended = bool(
                detail.get("krxTradingSuspended")
            )
            nxt_suspended = bool(
                detail.get("nxtTradingSuspended")
            )
            # Treat the symbol as fully suspended only when there is no
            # available Korean venue for it.
            suspended = (
                krx_suspended
                and (
                    not nxt_supported
                    or nxt_suspended
                )
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
                    nxt_supported=nxt_supported,
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

    async def candles(
        self,
        symbol: str,
        *,
        interval: str = "1m",
        count: int = 121,
    ) -> list[dict]:
        normalized = self._normalize_symbols([symbol])[0]
        if interval not in {"1m", "1d"}:
            raise ValueError("Unsupported Toss candle interval.")

        payload = await self.client.get(
            "/api/v1/candles",
            params={
                "symbol": normalized,
                "interval": interval,
                "count": max(2, min(count, 200)),
                "adjusted": True,
            },
        )
        result = payload.get("result") or {}
        raw = result.get("candles") or []

        candles: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                close = float(item.get("closePrice") or 0)
                open_price = float(item.get("openPrice") or 0)
                high = float(item.get("highPrice") or 0)
                low = float(item.get("lowPrice") or 0)
                volume = float(item.get("volume") or 0)
            except (TypeError, ValueError):
                continue

            if close <= 0:
                continue

            candles.append(
                {
                    "timestamp": str(item.get("timestamp") or ""),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )

        return candles

    async def snapshots(
        self,
        symbols: Iterable[str],
        *,
        with_features: bool = False,
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

            features: dict[str, float | int | str | None] = {}
            if with_features and market_open:
                try:
                    candles = await self.candles(
                        symbol,
                        interval="1m",
                        count=121,
                    )
                    features = TechnicalFeatureService.compute(
                        candles=candles,
                        current_price=float(quote.last_price),
                        short_period=5,
                        medium_period=30,
                        long_period=120,
                        interval_label="1m",
                    )
                except Exception:
                    features = {
                        "features_available": 0,
                        "feature_interval": "1m",
                        "feature_samples": 0,
                    }

                if symbol != normalized[-1]:
                    await asyncio.sleep(0.11)

            snapshots.append(
                MarketInstrumentSnapshot(
                    market="stock",
                    symbol=symbol,
                    name=info.name,
                    price=quote.last_price,
                    data_age_seconds=quote.data_age_seconds,
                    market_open=market_open,
                    features=features,
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
