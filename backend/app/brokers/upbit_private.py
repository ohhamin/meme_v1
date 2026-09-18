import hashlib
import uuid
from urllib.parse import urlencode

import httpx
import jwt

from backend.app.core.config import get_settings


class UpbitPrivateRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        ambiguous: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.ambiguous = ambiguous
        self.status_code = status_code


class UpbitPrivateClient:
    """Authenticated Upbit Exchange API client.

    POST/DELETE requests are never automatically retried because a network
    failure may occur after the exchange accepted the mutation.
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

    async def get(
        self,
        path: str,
        *,
        params: dict | None = None,
    ):
        return await self._request(
            "GET",
            path,
            params=params,
            body=None,
        )

    async def post(
        self,
        path: str,
        *,
        body: dict,
    ):
        return await self._request(
            "POST",
            path,
            params=None,
            body=body,
        )

    async def delete(
        self,
        path: str,
        *,
        params: dict,
    ):
        return await self._request(
            "DELETE",
            path,
            params=params,
            body=None,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None,
        body: dict | None,
    ):
        query_payload = params if params is not None else body
        token = self._create_token(query_payload)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            ) as client:
                response = await client.request(
                    method,
                    self.base_url + path,
                    params=params,
                    json=body,
                )
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
        ) as exc:
            raise UpbitPrivateRequestError(
                f"Upbit {method} request transport failure: {type(exc).__name__}",
                ambiguous=method in {"POST", "DELETE"},
            ) from exc

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text

            error_name = None
            if isinstance(detail, dict):
                error = detail.get("error")
                if isinstance(error, dict):
                    error_name = error.get("name") or error.get("message")

            ambiguous = (
                method in {"POST", "DELETE"}
                and response.status_code >= 500
            )
            raise UpbitPrivateRequestError(
                f"Upbit API error {response.status_code}: "
                f"{error_name or 'request_failed'}",
                ambiguous=ambiguous,
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UpbitPrivateRequestError(
                "Upbit returned invalid JSON.",
                ambiguous=method in {"POST", "DELETE"},
                status_code=response.status_code,
            ) from exc

    def _create_token(
        self,
        query_payload: dict | None = None,
    ) -> str:
        if not self.configured:
            raise UpbitPrivateRequestError(
                "Upbit API keys are not configured."
            )

        payload = {
            "access_key": self.config.upbit_access_key,
            "nonce": str(uuid.uuid4()),
        }

        if query_payload:
            query_string = urlencode(
                [
                    (key, value)
                    for key, raw in query_payload.items()
                    for value in (
                        raw if isinstance(raw, list) else [raw]
                    )
                    if value is not None
                ],
                doseq=True,
            )
            query_hash = hashlib.sha512(
                query_string.encode("utf-8")
            ).hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

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
