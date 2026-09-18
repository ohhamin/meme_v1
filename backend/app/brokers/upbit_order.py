from decimal import Decimal, ROUND_DOWN

from backend.app.brokers.upbit_private import (
    UpbitPrivateClient,
    UpbitPrivateRequestError,
)
from backend.app.models.schemas import LiveOrderPreflightResult


class UpbitOrderAdapter:
    """Upbit live-order adapter with test-create preflight and identifier lookup."""

    def __init__(self):
        self.client = UpbitPrivateClient()
        self.config = self.client.config

    @property
    def configured(self) -> bool:
        return self.client.configured

    @property
    def enabled(self) -> bool:
        return (
            self.config.trading_enabled
            and self.config.upbit_live_order_enabled
        )

    def build_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        identifier: str,
    ) -> dict:
        market = symbol.strip().upper()
        if not market.startswith("KRW-"):
            raise ValueError(
                "Only Upbit KRW markets are supported."
            )

        if side == "buy":
            amount = notional.quantize(
                Decimal("1"),
                rounding=ROUND_DOWN,
            )
            if amount <= 0:
                raise ValueError("BUY notional must be positive.")
            return {
                "market": market,
                "side": "bid",
                "price": str(amount),
                "ord_type": "price",
                "identifier": identifier,
            }

        if side == "sell":
            volume = quantity.quantize(
                Decimal("0.00000001"),
                rounding=ROUND_DOWN,
            )
            if volume <= 0:
                raise ValueError("SELL quantity must be positive.")
            return {
                "market": market,
                "side": "ask",
                "volume": format(volume, "f"),
                "ord_type": "market",
                "identifier": identifier,
            }

        raise ValueError("side must be buy or sell")

    async def preflight(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        identifier: str,
    ) -> LiveOrderPreflightResult:
        reasons: list[str] = []
        if not self.configured:
            reasons.append("Upbit API keys are not configured.")
        if not self.config.upbit_live_order_enabled:
            reasons.append("UPBIT_LIVE_ORDER_ENABLED=false.")

        if reasons:
            return LiveOrderPreflightResult(
                allowed=False,
                broker="upbit",
                symbol=symbol,
                side=side,
                reasons=reasons,
            )

        try:
            body = self.build_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                notional=notional,
                identifier=identifier,
            )
            await self.client.post(
                "/orders/test",
                body=body,
            )
        except (
            ValueError,
            UpbitPrivateRequestError,
        ) as exc:
            reasons.append(str(exc))

        return LiveOrderPreflightResult(
            allowed=not reasons,
            broker="upbit",
            symbol=symbol,
            side=side,
            reasons=reasons,
        )

    async def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        identifier: str,
    ) -> dict:
        if not self.enabled:
            raise UpbitPrivateRequestError(
                "Upbit live ordering is disabled."
            )

        body = self.build_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            identifier=identifier,
        )
        return await self.client.post(
            "/orders",
            body=body,
        )

    async def get_order(
        self,
        *,
        identifier: str | None = None,
        order_id: str | None = None,
    ) -> dict:
        if not identifier and not order_id:
            raise ValueError(
                "identifier or order_id is required."
            )

        params = (
            {"uuid": order_id}
            if order_id
            else {"identifier": identifier}
        )
        return await self.client.get(
            "/order",
            params=params,
        )
