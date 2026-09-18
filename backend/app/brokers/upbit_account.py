import uuid
from decimal import Decimal

import httpx
import jwt

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    UpbitAccountAsset,
    UpbitAccountStatus,
)


class UpbitAccountError(RuntimeError):
    pass


class UpbitAccountAdapter:
    """Read-only authenticated Upbit account adapter.

    This adapter only calls GET /accounts and never places orders.
    """

    def __init__(self):
        self.config = get_settings()
        self.base_url = self.config.upbit_api_base_url.rstrip("/")
        self.timeout = self.config.upbit_http_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(
            self.config.upbit_access_key
            and self.config.upbit_secret_key
        )

    async def balances(self) -> UpbitAccountStatus:
        if not self.configured:
            return UpbitAccountStatus(
                configured=False,
                assets=[],
            )

        token = self._create_token()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            ) as client:
                response = await client.get(
                    self.base_url + "/accounts"
                )
                response.raise_for_status()
                raw = response.json()
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
            ValueError,
        ) as exc:
            raise UpbitAccountError(
                f"Upbit account request failed: {type(exc).__name__}"
            ) from exc

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

    def _create_token(self) -> str:
        if not self.configured:
            raise UpbitAccountError(
                "Upbit API keys are not configured."
            )

        payload = {
            "access_key": self.config.upbit_access_key,
            "nonce": str(uuid.uuid4()),
        }

        token = jwt.encode(
            payload,
            self.config.upbit_secret_key,
            algorithm="HS512",
        )
        return (
            token
            if isinstance(token, str)
            else token.decode("utf-8")
        )

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")
