from decimal import Decimal, ROUND_DOWN

from backend.app.brokers.toss_account import TossAccountAdapter
from backend.app.brokers.toss_client import TossApiClient, TossApiError
from backend.app.models.schemas import LiveOrderPreflightResult


class TossOrderAdapter:
    """Toss Securities KR live-order adapter with deterministic preflight."""

    def __init__(self):
        self.client = TossApiClient()
        self.accounts = TossAccountAdapter()
        self.config = self.client.config

    @property
    def configured(self) -> bool:
        return self.client.configured

    @property
    def enabled(self) -> bool:
        return (
            self.config.trading_enabled
            and self.config.toss_live_order_enabled
        )

    async def preflight(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        client_order_id: str,
    ) -> LiveOrderPreflightResult:
        reasons: list[str] = []

        if not self.configured:
            reasons.append("Toss client credentials are not configured.")
        if not self.config.toss_live_order_enabled:
            reasons.append("TOSS_LIVE_ORDER_ENABLED=false.")

        normalized = symbol.strip().upper()
        if len(normalized) != 6 or not normalized.isdigit():
            reasons.append(
                "Only 6-digit Korean stock symbols are supported."
            )

        qty = quantity.quantize(
            Decimal("1"),
            rounding=ROUND_DOWN,
        )
        if qty <= 0:
            reasons.append("Order quantity must be at least 1 share.")
        if quantity != qty:
            reasons.append("Korean stock quantity must be an integer.")

        if (
            notional >= Decimal(
                str(self.config.toss_high_value_order_threshold_krw)
            )
            and not self.config.toss_confirm_high_value_orders
        ):
            reasons.append(
                "High-value Toss order requires explicit "
                "TOSS_CONFIRM_HIGH_VALUE_ORDERS=true."
            )

        if reasons:
            return LiveOrderPreflightResult(
                allowed=False,
                broker="toss",
                symbol=symbol,
                side=side,
                reasons=reasons,
            )

        try:
            account_seq = await self.accounts.selected_account_seq()

            if side == "buy":
                buying_power = await self.accounts.buying_power(
                    account_seq=account_seq
                )
                if notional > buying_power:
                    reasons.append(
                        "Toss cash buying power is insufficient."
                    )
            elif side == "sell":
                payload = await self.client.get(
                    "/api/v1/sellable-quantity",
                    params={"symbol": normalized},
                    account_seq=account_seq,
                )
                result = payload.get("result") or {}
                sellable = Decimal(
                    str(result.get("sellableQuantity") or "0")
                )
                if qty > sellable:
                    reasons.append(
                        "Toss sellable quantity is insufficient."
                    )
            else:
                reasons.append("side must be buy or sell")
        except (TossApiError, ValueError) as exc:
            reasons.append(str(exc))

        return LiveOrderPreflightResult(
            allowed=not reasons,
            broker="toss",
            symbol=symbol,
            side=side,
            reasons=reasons,
        )

    def build_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        client_order_id: str,
    ) -> dict:
        normalized = symbol.strip().upper()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError(
                "Only 6-digit Korean stock symbols are supported."
            )
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        qty = quantity.quantize(
            Decimal("1"),
            rounding=ROUND_DOWN,
        )
        if qty <= 0 or qty != quantity:
            raise ValueError(
                "Korean stock quantity must be a positive integer."
            )

        body = {
            "clientOrderId": client_order_id,
            "symbol": normalized,
            "side": "BUY" if side == "buy" else "SELL",
            "orderType": "MARKET",
            "quantity": str(qty),
        }
        if (
            notional
            >= Decimal(
                str(self.config.toss_high_value_order_threshold_krw)
            )
            and self.config.toss_confirm_high_value_orders
        ):
            body["confirmHighValueOrder"] = True

        return body

    async def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        client_order_id: str,
    ) -> dict:
        if not self.enabled:
            raise TossApiError(
                "Toss live ordering is disabled."
            )

        account_seq = await self.accounts.selected_account_seq()
        body = self.build_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            client_order_id=client_order_id,
        )

        return await self.client.post(
            "/api/v1/orders",
            body=body,
            account_seq=account_seq,
        )

    async def get_order(
        self,
        order_id: str,
    ) -> dict:
        account_seq = await self.accounts.selected_account_seq()
        return await self.client.get(
            f"/api/v1/orders/{order_id}",
            account_seq=account_seq,
        )
