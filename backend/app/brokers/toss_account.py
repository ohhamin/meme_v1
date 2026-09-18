from decimal import Decimal

from backend.app.brokers.toss_client import TossApiClient, TossApiError
from backend.app.models.schemas import (
    TossAccount,
    TossAccountStatus,
    TossHolding,
)


class TossAccountAdapter:
    """Read-only Toss Securities account adapter.

    Only account list, holdings, and buying power are queried.
    No order endpoint is implemented here.
    """

    def __init__(self):
        self.client = TossApiClient()

    @property
    def configured(self) -> bool:
        return self.client.configured

    async def accounts(self) -> list[TossAccount]:
        if not self.configured:
            return []

        payload = await self.client.get(
            "/api/v1/accounts"
        )
        raw = payload.get("result") or []

        result: list[TossAccount] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            try:
                account_seq = int(item.get("accountSeq"))
            except (TypeError, ValueError):
                continue

            result.append(
                TossAccount(
                    account_seq=account_seq,
                    account_type=str(
                        item.get("accountType") or "UNKNOWN"
                    ),
                )
            )

        return result

    async def selected_account_seq(self) -> int:
        accounts = await self.accounts()
        if not accounts:
            raise TossApiError(
                "No eligible Toss Securities account was found."
            )

        configured = self.client.config.toss_account_seq
        if configured is not None:
            available = {
                account.account_seq
                for account in accounts
            }
            if configured not in available:
                raise TossApiError(
                    "Configured TOSS_ACCOUNT_SEQ is not available."
                )
            return configured

        if len(accounts) == 1:
            return accounts[0].account_seq

        raise TossApiError(
            "Multiple Toss accounts exist. Set TOSS_ACCOUNT_SEQ explicitly."
        )

    async def status(self) -> TossAccountStatus:
        if not self.configured:
            return TossAccountStatus(
                configured=False,
                account_seq=None,
                cash_buying_power=Decimal("0"),
                holdings=[],
            )

        account_seq = await self.selected_account_seq()
        holdings = await self.holdings(
            account_seq=account_seq
        )
        cash = await self.buying_power(
            account_seq=account_seq
        )

        return TossAccountStatus(
            configured=True,
            account_seq=account_seq,
            cash_buying_power=cash,
            holdings=holdings,
        )

    async def holdings(
        self,
        *,
        account_seq: int | None = None,
    ) -> list[TossHolding]:
        seq = (
            account_seq
            if account_seq is not None
            else await self.selected_account_seq()
        )

        payload = await self.client.get(
            "/api/v1/holdings",
            account_seq=seq,
        )
        overview = payload.get("result") or {}
        raw = overview.get("items") or []

        result: list[TossHolding] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            if (
                str(item.get("marketCountry") or "").upper()
                != "KR"
            ):
                continue
            if (
                str(item.get("currency") or "").upper()
                != "KRW"
            ):
                continue

            market_value = item.get("marketValue") or {}
            profit_loss = item.get("profitLoss") or {}

            rate = self._decimal(
                profit_loss.get("rate")
            )

            result.append(
                TossHolding(
                    symbol=str(
                        item.get("symbol") or ""
                    ).upper(),
                    name=str(item.get("name") or ""),
                    quantity=self._decimal(
                        item.get("quantity")
                    ),
                    last_price=self._decimal(
                        item.get("lastPrice")
                    ),
                    average_purchase_price=self._decimal(
                        item.get("averagePurchasePrice")
                    ),
                    purchase_amount=self._decimal(
                        market_value.get("purchaseAmount")
                    ),
                    market_value=self._decimal(
                        market_value.get("amount")
                    ),
                    # Toss holdings rate is a ratio (0.1077 = 10.77%).
                    return_rate=rate * Decimal("100"),
                )
            )

        return [
            item
            for item in result
            if item.symbol and item.quantity > 0
        ]

    async def buying_power(
        self,
        *,
        account_seq: int | None = None,
    ) -> Decimal:
        seq = (
            account_seq
            if account_seq is not None
            else await self.selected_account_seq()
        )

        payload = await self.client.get(
            "/api/v1/buying-power",
            params={"currency": "KRW"},
            account_seq=seq,
        )
        result = payload.get("result") or {}
        return self._decimal(
            result.get("cashBuyingPower")
        )

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")
