from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.core.security import require_api_token
from backend.app.services.backend_errors import BackendErrorStore


router = APIRouter(
    prefix="/backend-errors",
    tags=["backend-errors"],
    dependencies=[Depends(require_api_token)],
)


class BackendErrorImprovedUpdate(BaseModel):
    improved: bool = True


@router.get("")
async def list_backend_errors():
    return {"items": BackendErrorStore().list_items()}


@router.put("/{error_id}/improved")
async def mark_backend_error_improved(
    error_id: str,
    payload: BackendErrorImprovedUpdate,
):
    try:
        return BackendErrorStore().mark_improved(
            error_id,
            payload.improved,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backend error not found.",
        ) from exc
