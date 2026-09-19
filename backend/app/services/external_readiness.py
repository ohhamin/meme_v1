from pathlib import Path

import httpx

from backend.app.brokers.toss_account import TossAccountAdapter
from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.upbit_account import (
    UpbitAccountAdapter,
    UpbitAccountError,
)
from backend.app.brokers.upbit_market_data import (
    UpbitMarketDataAdapter,
    UpbitMarketDataError,
)
from backend.app.core.config import get_settings


class ExternalReadinessService:
    """Read-only connectivity diagnostics. Never creates or mutates an order."""

    def __init__(self):
        self.config = get_settings()
        self.upbit_account = UpbitAccountAdapter()
        self.upbit_market = UpbitMarketDataAdapter()
        self.toss_account = TossAccountAdapter()

    async def check(self) -> dict:
        return {
            "openai": self._configured(
                bool(self.config.openai_api_key)
            ),
            "firebase": self._firebase(),
            "upbit_public_market": await self._upbit_public(),
            "upbit_account": await self._upbit_account(),
            "toss_account": await self._toss_account(),
            "krx_market": await self._krx_market(),
            "mutation_performed": False,
        }

    async def _upbit_public(self) -> dict:
        try:
            quotes = await self.upbit_market.quotes(
                ["KRW-BTC"]
            )
            if not quotes:
                return self._failed(
                    "Upbit public quotation returned no BTC price."
                )
            return {
                "status": "ok",
                "configured": True,
                "detail": "Public KRW-BTC quotation is reachable.",
            }
        except (UpbitMarketDataError, ValueError) as exc:
            return self._failed(str(exc))

    async def _upbit_account(self) -> dict:
        if not self.upbit_account.configured:
            return self._not_configured()

        try:
            result = await self.upbit_account.balances()
            return {
                "status": "ok",
                "configured": True,
                "detail": (
                    f"Authenticated account read succeeded "
                    f"({len(result.assets)} asset rows)."
                ),
            }
        except UpbitAccountError as exc:
            return self._failed(str(exc), configured=True)

    async def _toss_account(self) -> dict:
        if not self.toss_account.configured:
            return self._not_configured()

        try:
            accounts = await self.toss_account.accounts()
            if not accounts:
                return self._failed(
                    "Toss authentication succeeded but no eligible account was found.",
                    configured=True,
                )

            # Resolve selection as well so multi-account configuration mistakes
            # are detected before Live mode is considered ready.
            selected = await self.toss_account.selected_account_seq()
            return {
                "status": "ok",
                "configured": True,
                "detail": (
                    f"Authenticated account read succeeded "
                    f"(selected accountSeq={selected})."
                ),
            }
        except TossApiError as exc:
            return self._failed(str(exc), configured=True)

    async def _krx_market(self) -> dict:
        if not self.config.krx_api_key:
            return self._not_configured()

        try:
            async with httpx.AsyncClient(
                timeout=self.config.krx_http_timeout_seconds,
            ) as client:
                response = await client.get(
                    f"{self.config.krx_api_base_url}/idx/kospi_dd_trd",
                    params={"basDd": "20260918"},
                    headers={"AUTH_KEY": self.config.krx_api_key},
                )
                response.raise_for_status()
                rows = response.json().get("OutBlock_1", [])
                if not rows:
                    return self._failed(
                        "KRX authentication succeeded but no index rows were returned.",
                        configured=True,
                    )
                return {
                    "status": "ok",
                    "configured": True,
                    "detail": (
                        "Authenticated KRX index read succeeded "
                        f"({len(rows)} rows)."
                    ),
                }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            return self._failed(
                f"KRX read failed: {type(exc).__name__}: {exc}",
                configured=True,
            )

    def _firebase(self) -> dict:
        raw = self.config.firebase_credentials_path.strip()
        if not raw:
            return self._not_configured()

        path = Path(raw)
        if not path.exists():
            return self._failed(
                "Firebase credentials file does not exist.",
                configured=True,
            )

        return {
            "status": "ok",
            "configured": True,
            "detail": "Firebase credentials file exists.",
        }

    @staticmethod
    def _configured(value: bool) -> dict:
        return {
            "status": "configured" if value else "not_configured",
            "configured": value,
        }

    @staticmethod
    def _not_configured() -> dict:
        return {
            "status": "not_configured",
            "configured": False,
        }

    @staticmethod
    def _failed(
        detail: str,
        *,
        configured: bool = True,
    ) -> dict:
        return {
            "status": "failed",
            "configured": configured,
            "detail": detail,
        }
