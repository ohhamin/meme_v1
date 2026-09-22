from decimal import Decimal

from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    PaperAccountsResponse,
    PaperResetRequest,
)
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.position_sizer import PositionSizer
from backend.app.services.paper_dashboard import PaperDashboardService
from backend.app.services.paper_order_journal import PaperOrderJournal


router = APIRouter(
    prefix="/paper",
    tags=["paper"],
    dependencies=[Depends(require_api_token)],
)


def _accounts() -> PaperAccountsResponse:
    return PaperAccountsResponse(
        stock=PaperBroker("stock").portfolio(),
        crypto=PaperBroker("crypto").portfolio(),
    )


@router.get("/portfolio", response_model=PaperAccountsResponse)
async def portfolio():
    return _accounts()


@router.get("/dashboard")
async def dashboard():
    return PaperDashboardService().build()


@router.post("/reset", response_model=PaperAccountsResponse)
async def reset(payload: PaperResetRequest):
    initial_cash = (
        Decimal(payload.initial_cash)
        if payload.initial_cash is not None
        else None
    )

    journal = PaperOrderJournal()

    if payload.market in {"stock", "all"}:
        PaperBroker("stock").reset(initial_cash)
        journal.reset_market("stock")

    if payload.market in {"crypto", "all"}:
        PaperBroker("crypto").reset(initial_cash)
        journal.reset_market("crypto")

    return _accounts()


@router.get("/position-sizing-policy")
async def position_sizing_policy():
    return PositionSizer().policy()
