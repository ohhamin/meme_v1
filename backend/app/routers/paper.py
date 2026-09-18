from decimal import Decimal

from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import PaperPortfolio, PaperResetRequest
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.position_sizer import PositionSizer


router = APIRouter(
    prefix="/paper",
    tags=["paper"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/portfolio", response_model=PaperPortfolio)
async def portfolio():
    return PaperBroker().portfolio()


@router.post("/reset", response_model=PaperPortfolio)
async def reset(payload: PaperResetRequest):
    initial_cash = (
        Decimal(payload.initial_cash)
        if payload.initial_cash is not None
        else None
    )
    return PaperBroker().reset(initial_cash)


@router.get("/position-sizing-policy")
async def position_sizing_policy():
    return PositionSizer().policy()
