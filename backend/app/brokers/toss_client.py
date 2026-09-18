import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.app.core.config import get_settings


class TossApiError(RuntimeError):
    pass


class TossApiClient:
    """OAuth2 client-credentials client for Toss Securities Open API.

    GET requests may refresh the token once on 401.
    No mutation/order endpoint is implemented in this client.
    """

    _token: str | None = None
    _expires_at: datetime | None = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.config = get_settings()
        self.base_url = self.config.toss_api_base_url.rstrip("/")
        self.timeout = self.config.toss_http_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(
            self.config.toss_client_id
            and self.config.toss_client_secret
        )

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        account_seq: int | None = None,
    ) -> dict:
        return await self._get(
            path,
            params=params,
            account_seq=account_seq,
            retry_on_401=True,
        )

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None,
        account_seq: int | None,
        retry_on_401: bool,
    ) -> dict:
        token = await self._access_token()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if account_seq is not None:
            headers["X-Tossinvest-Account"] = str(account_seq)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            ) as client:
                response = await client.get(
                    self.base_url + path,
                    params=params,
                )

            if response.status_code == 401 and retry_on_401:
                self._invalidate_token()
                return await self._get(
                    path,
                    params=params,
                    account_seq=account_seq,
                    retry_on_401=False,
                )

            response.raise_for_status()
            data = response.json()
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
            ValueError,
        ) as exc:
            raise TossApiError(
                f"Toss API request failed: {type(exc).__name__}"
            ) from exc

        if not isinstance(data, dict):
            raise TossApiError("Toss API returned a non-object response.")

        if "error" in data:
            error = data.get("error") or {}
            code = error.get("code") if isinstance(error, dict) else None
            raise TossApiError(
                f"Toss API error: {code or 'unknown'}"
            )

        return data

    async def _access_token(self) -> str:
        if not self.configured:
            raise TossApiError(
                "Toss client credentials are not configured."
            )

        now = datetime.now(timezone.utc)
        if (
            self.__class__._token
            and self.__class__._expires_at
            and now < self.__class__._expires_at
        ):
            return self.__class__._token

        async with self.__class__._lock:
            now = datetime.now(timezone.utc)
            if (
                self.__class__._token
                and self.__class__._expires_at
                and now < self.__class__._expires_at
            ):
                return self.__class__._token

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"Accept": "application/json"},
                ) as client:
                    response = await client.post(
                        self.base_url + "/oauth2/token",
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.config.toss_client_id,
                            "client_secret": self.config.toss_client_secret,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.HTTPStatusError,
                ValueError,
            ) as exc:
                raise TossApiError(
                    f"Toss OAuth token request failed: {type(exc).__name__}"
                ) from exc

            token = str(payload.get("access_token") or "")
            if not token:
                raise TossApiError(
                    "Toss OAuth response has no access_token."
                )

            try:
                expires_in = int(payload.get("expires_in") or 3600)
            except (TypeError, ValueError):
                expires_in = 3600

            # Refresh a little before actual expiry.
            ttl = max(1, expires_in - 60)
            self.__class__._token = token
            self.__class__._expires_at = (
                datetime.now(timezone.utc)
                + timedelta(seconds=ttl)
            )
            return token

    @classmethod
    def _invalidate_token(cls) -> None:
        cls._token = None
        cls._expires_at = None
