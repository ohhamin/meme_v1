from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

import httpx

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    UpbitMarketInfo,
    UpbitQuote,
)


class UpbitMarketDataError(RuntimeError):
    pass


class UpbitMarketDataAdapter:
    """Read-only Upbit Quotation API adapter.

    No API key is required for the public quotation endpoints used here.
    This adapter never calls order/account endpoints.
    """

    def __init__(self):
        self.config = get_settings()
        self.base_url = self.config.upbit_api_base_url.rstrip("/")
        self.timeout = self.config.upbit_http_timeout_seconds
        self._market_cache: dict[str, UpbitMarketInfo] | None = None

    async def list_markets(
        self,
        *,
        quote_currency: str = "KRW",
        details: bool = True,
    ) -> list[UpbitMarketInfo]:
        raw = await self._get(
            "/market/all",
            params={"is_details": str(details).lower()},
        )

        result: list[UpbitMarketInfo] = []
        prefix = quote_currency.upper() + "-"

        for item in raw:
            market = str(item.get("market") or "").upper()
            if not market.startswith(prefix):
                continue

            event = item.get("market_event") or {}
            caution_raw = event.get("caution") or {}
            caution = any(bool(value) for value in caution_raw.values())

            warning_raw = event.get("warning")
            if warning_raw is None:
                warning_raw = item.get("market_warning")
            warning = bool(
                warning_raw is True
                or str(warning_raw).upper() not in {"", "NONE", "FALSE", "0"}
            )

            result.append(
                UpbitMarketInfo(
                    market=market,
                    korean_name=str(item.get("korean_name") or market),
                    english_name=str(item.get("english_name") or market),
                    warning=warning,
                    caution=caution,
                )
            )

        result.sort(key=lambda x: x.market)
        self._market_cache = {item.market: item for item in result}
        return result

    async def quotes(
        self,
        markets: Iterable[str],
    ) -> list[UpbitQuote]:
        normalized = self._normalize_markets(markets)
        if not normalized:
            return []

        # Upbit ticker accepts comma-separated markets in one request.
        raw = await self._get(
            "/ticker",
            params={"markets": ",".join(normalized)},
        )

        names = await self._market_names()
        now = datetime.now(timezone.utc)
        result: list[UpbitQuote] = []

        for item in raw:
            market = str(item.get("market") or "").upper()
            price = Decimal(str(item.get("trade_price") or "0"))
            if price <= 0:
                continue

            timestamp_ms = (
                item.get("timestamp")
                or item.get("trade_timestamp")
            )
            timestamp = self._timestamp(timestamp_ms)
            age = max(0, int((now - timestamp).total_seconds()))
            info = names.get(market)

            result.append(
                UpbitQuote(
                    market=market,
                    korean_name=info.korean_name if info else None,
                    english_name=info.english_name if info else None,
                    trade_price=price,
                    signed_change_rate=self._optional_decimal(
                        item.get("signed_change_rate")
                    ),
                    acc_trade_price_24h=self._optional_decimal(
                        item.get("acc_trade_price_24h")
                    ),
                    timestamp=timestamp,
                    data_age_seconds=age,
                )
            )

        by_market = {item.market: item for item in result}
        return [
            by_market[market]
            for market in normalized
            if market in by_market
        ]

    async def snapshots(
        self,
        markets: Iterable[str],
    ) -> list[MarketInstrumentSnapshot]:
        quotes = await self.quotes(markets)
        return [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol=quote.market,
                name=quote.korean_name or quote.market,
                price=quote.trade_price,
                data_age_seconds=quote.data_age_seconds,
                market_open=True,
            )
            for quote in quotes
        ]

    async def _market_names(self) -> dict[str, UpbitMarketInfo]:
        if self._market_cache is None:
            await self.list_markets(
                quote_currency="KRW",
                details=True,
            )
        return self._market_cache or {}

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str],
    ):
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            ) as client:
                response = await client.get(
                    self.base_url + path,
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
            ValueError,
        ) as exc:
            raise UpbitMarketDataError(
                f"Upbit quotation request failed: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _normalize_markets(markets: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in markets:
            market = str(value).strip().upper()
            if not market:
                continue
            if not market.startswith("KRW-"):
                raise ValueError(
                    f"Only KRW markets are supported for now: {market}"
                )
            if market not in seen:
                seen.add(market)
                result.append(market)

        return result

    @staticmethod
    def _timestamp(value) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)

        try:
            raw = int(value)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)

        # Upbit timestamps are milliseconds since epoch.
        if raw > 10_000_000_000:
            raw = raw / 1000

        return datetime.fromtimestamp(raw, tz=timezone.utc)

    @staticmethod
    def _optional_decimal(value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
