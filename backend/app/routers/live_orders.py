from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    LiveOrderEnablement,
    LiveOrderReconcileResponse,
)
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_order_reconciler import LiveOrderReconciler
from backend.app.services.live_order_service import LiveOrderService


router = APIRouter(
    prefix="/live-orders",
    tags=["live-orders"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/enablement", response_model=LiveOrderEnablement)
async def enablement():
    return LiveOrderService().enablement()


@router.get("")
async def list_orders(
    limit: int = Query(50, ge=1, le=200),
):
    return {
        "items": LiveOrderJournal().list_records(limit=limit),
    }


@router.get("/unresolved")
async def unresolved(
    limit: int = Query(50, ge=1, le=200),
):
    return {
        "items": LiveOrderJournal().unresolved(limit=limit),
    }


@router.post("/reconcile", response_model=LiveOrderReconcileResponse)
async def reconcile(
    intent_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    if intent_id:
        try:
            LiveOrderJournal().get(intent_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Live order intent not found.",
            ) from exc

    return await LiveOrderReconciler().reconcile(
        intent_id=intent_id,
        limit=limit,
    )
