from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import StockManualOrderRequest
from backend.app.services.trading import TradingService


router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/positions")
async def positions():
    return TradingService().stock_positions()


@router.post("/orders/manual")
async def manual_order(payload: StockManualOrderRequest):
    return TradingService().manual_stock_order(
        symbol=payload.symbol,
        side=payload.side,
        quantity=payload.quantity,
    )
