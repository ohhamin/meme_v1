from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import CryptoManualOrderRequest
from backend.app.services.trading import TradingService


router = APIRouter(
    prefix="/crypto",
    tags=["crypto"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/positions")
async def positions():
    return TradingService().crypto_positions()


@router.post("/orders/manual")
async def manual_order(payload: CryptoManualOrderRequest):
    return TradingService().manual_crypto_order(
        symbol=payload.symbol,
        side=payload.side,
        amount_krw=payload.amount_krw,
    )
