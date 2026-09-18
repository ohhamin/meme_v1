from decimal import Decimal

from backend.app.brokers.upbit_private import (
    UpbitPrivateClient,
    UpbitPrivateRequestError,
)
from backend.app.models.schemas import (
    UpbitAccountAsset,
    UpbitAccountStatus,
)


class UpbitAccountError(RuntimeError):
    pass


class UpbitAccountAdapter:
    """Read-only authenticated Upbit account adapter."""

    def __init__(self):
        self.client = UpbitPrivateClient()

    @property
    def configured(self) -> bool:
        return self.client.configured

    @property
    def config(self):
        # Compatibility for existing status/tests.
        return self.client.config

    async def balances(self) -> UpbitAccountStatus:
        if not self.configured:
            return UpbitAccountStatus(
                configured=False,
                assets=[],
            )

        try:
            raw = await self.client.get("/accounts")
        except UpbitPrivateRequestError as exc:
            raise UpbitAccountError(str(exc)) from exc

        assets: list[UpbitAccountAsset] = []

        for item in raw:
            currency = str(item.get("currency") or "").upper()
            if not currency:
                continue

            balance = self._decimal(item.get("balance"))
            locked = self._decimal(item.get("locked"))
            avg_buy_price = self._decimal(
                item.get("avg_buy_price")
            )
            unit_currency = str(
                item.get("unit_currency") or "KRW"
            ).upper()

            assets.append(
                UpbitAccountAsset(
                    currency=currency,
                    balance=balance,
                    locked=locked,
                    total=balance + locked,
                    avg_buy_price=avg_buy_price,
                    unit_currency=unit_currency,
                )
            )

        assets.sort(
            key=lambda asset: (
                asset.currency != "KRW",
                asset.currency,
            )
        )

        return UpbitAccountStatus(
            configured=True,
            assets=assets,
        )

    def _create_token(self, query_payload: dict | None = None) -> str:
        return self.client._create_token(query_payload)

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")
