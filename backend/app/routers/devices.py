from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    DeviceTokenStatus,
    DeviceTokenUpdate,
)
from backend.app.services.device_tokens import DeviceTokenService


router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/push", response_model=DeviceTokenStatus)
async def push_status():
    return DeviceTokenService().status()


@router.put("/push", response_model=DeviceTokenStatus)
async def register_push(payload: DeviceTokenUpdate):
    service = DeviceTokenService()
    service.register(
        token=payload.token,
        platform=payload.platform,
    )
    return service.status()


@router.post("/push/clear", response_model=DeviceTokenStatus)
async def clear_push():
    service = DeviceTokenService()
    service.clear()
    return service.status()
