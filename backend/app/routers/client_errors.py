from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.security import require_api_token
from backend.app.services.client_errors import ClientErrorStore


router = APIRouter(
    prefix="/client-errors",
    tags=["client-errors"],
    dependencies=[Depends(require_api_token)],
)


class ClientErrorReport(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    stack: str = Field(default="", max_length=12000)
    library: str = Field(default="", max_length=500)
    context: str = Field(default="", max_length=1000)


class ClientErrorImprovedUpdate(BaseModel):
    improved: bool = True


@router.get("")
async def list_client_errors():
    return {"items": ClientErrorStore().list_items()}


@router.post("")
async def report_client_error(payload: ClientErrorReport):
    return ClientErrorStore().report(
        message=payload.message,
        stack=payload.stack,
        library=payload.library,
        context=payload.context,
    )


@router.put("/{error_id}/improved")
async def mark_client_error_improved(
    error_id: str,
    payload: ClientErrorImprovedUpdate,
):
    try:
        return ClientErrorStore().mark_improved(
            error_id,
            payload.improved,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client error not found.",
        ) from exc
