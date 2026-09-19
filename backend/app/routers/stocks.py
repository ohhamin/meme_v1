from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.brokers.toss_account import TossAccountAdapter
from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    PaperCycleResponse,
    StockManualOrderRequest,
    TossAccountStatus,
    TossQuote,
    TossStockInfo,
    TossUniverseResponse,
    TossUniverseUpdate,
)
from backend.app.services.toss_paper_runner import TossPaperRunner
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.trading import TradingService
from backend.app.services.market_performance import MarketPerformanceService


router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/positions")
async def positions():
    return await TradingService().stock_positions()

@router.get("/performance")
async def performance():
    return await MarketPerformanceService().build("stock")


@router.post("/orders/manual")
async def manual_order(payload: StockManualOrderRequest):
    return await TradingService().manual_stock_order(
        symbol=payload.symbol,
        side=payload.side,
        quantity=payload.quantity,
        idempotency_key=payload.idempotency_key,
    )


@router.get("/toss/prices", response_model=list[TossQuote])
async def toss_prices(
    symbols: str = Query(
        ...,
        description="Comma-separated Korean symbols, e.g. 005930,000660",
    ),
):
    selected = [
        value.strip()
        for value in symbols.split(",")
        if value.strip()
    ]
    return await TossMarketDataAdapter().quotes(selected)


@router.get("/toss/stocks", response_model=list[TossStockInfo])
async def toss_stocks(
    symbols: str = Query(
        ...,
        description="Comma-separated Korean symbols",
    ),
):
    selected = [
        value.strip()
        for value in symbols.split(",")
        if value.strip()
    ]
    return await TossMarketDataAdapter().stock_info(selected)


@router.get("/toss/accounts", response_model=TossAccountStatus)
async def toss_accounts():
    return await TossAccountAdapter().status()


@router.get("/toss/universe", response_model=TossUniverseResponse)
async def toss_universe():
    symbols = TossUniverseService().get()
    return TossUniverseResponse(
        symbols=symbols,
        count=len(symbols),
    )


@router.put("/toss/universe", response_model=TossUniverseResponse)
async def update_toss_universe(payload: TossUniverseUpdate):
    requested = [
        value.strip().upper()
        for value in payload.symbols
        if value.strip()
    ]

    adapter = TossMarketDataAdapter()
    if requested and adapter.configured:
        try:
            infos = await adapter.stock_info(requested)
        except (TossApiError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        valid = {
            item.symbol
            for item in infos
            if item.status == "ACTIVE"
            and item.currency == "KRW"
        }
        invalid = sorted(set(requested) - valid)
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        "Unknown or inactive Toss Korean symbols."
                    ),
                    "symbols": invalid,
                },
            )

    symbols = TossUniverseService().set(requested)
    return TossUniverseResponse(
        symbols=symbols,
        count=len(symbols),
    )


@router.post("/toss/paper-run", response_model=PaperCycleResponse)
async def toss_paper_run(
    symbols: str | None = Query(
        None,
        description=(
            "Optional comma-separated symbols. "
            "When omitted, saved Toss universe is used."
        ),
    ),
):
    selected = (
        [
            value.strip()
            for value in symbols.split(",")
            if value.strip()
        ]
        if symbols
        else None
    )
    return await TossPaperRunner().run(selected)
