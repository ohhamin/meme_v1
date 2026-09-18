from fastapi import APIRouter, Depends, Query

from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    CryptoManualOrderRequest,
    PaperCycleResponse,
    UpbitMarketInfo,
    UpbitQuote,
)
from backend.app.services.trading import TradingService
from backend.app.services.upbit_paper_runner import UpbitPaperRunner


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
        idempotency_key=payload.idempotency_key,
    )


@router.get("/upbit/markets", response_model=list[UpbitMarketInfo])
async def upbit_markets():
    return await UpbitMarketDataAdapter().list_markets(
        quote_currency="KRW",
        details=True,
    )


@router.get("/upbit/quotes", response_model=list[UpbitQuote])
async def upbit_quotes(
    markets: str = Query(
        ...,
        description="Comma-separated KRW markets, e.g. KRW-BTC,KRW-ETH",
    ),
):
    selected = [
        value.strip()
        for value in markets.split(",")
        if value.strip()
    ]
    return await UpbitMarketDataAdapter().quotes(selected)


@router.post("/upbit/paper-run", response_model=PaperCycleResponse)
async def upbit_paper_run(
    markets: str | None = Query(
        None,
        description=(
            "Optional comma-separated markets. "
            "When omitted, UPBIT_DECISION_MARKETS is used."
        ),
    ),
):
    selected = (
        [
            value.strip()
            for value in markets.split(",")
            if value.strip()
        ]
        if markets
        else None
    )
    return await UpbitPaperRunner().run(selected)
