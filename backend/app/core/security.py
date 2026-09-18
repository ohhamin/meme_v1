import secrets

from fastapi import Header, HTTPException, status

from backend.app.core.config import get_settings


async def require_api_token(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()

    # 로컬 개발에서는 기본 토큰일 때 인증을 생략한다.
    if settings.app_env == "local" and settings.api_token == "change-me":
        return

    expected = f"Bearer {settings.api_token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
