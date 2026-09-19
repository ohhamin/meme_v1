from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.brokers.upbit_account import UpbitAccountAdapter
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    CryptoManualOrderRequest,
    PaperCycleResponse,
    UpbitAccountStatus,
    UpbitMarketInfo,
    UpbitQuote,
    UpbitUniverseResponse,
    UpbitUniverseUpdate,
)
from backend.app.services.trading import TradingService
from backend.app.services.market_performance import MarketPerformanceService
from backend.app.services.upbit_paper_runner import UpbitPaperRunner
from backend.app.services.upbit_universe import UpbitUniverseService
from backend.app.services.upbit_universe_selector import UpbitUniverseSelector


router = APIRouter(
    prefix="/crypto",
    tags=["crypto"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/performance")
async def performance():
    return await MarketPerformanceService().build("crypto")


@router.get("/positions")
async def positions():
    return await TradingService().crypto_positions()


@router.post("/orders/manual")
async def manual_order(payload: CryptoManualOrderRequest):
    return await TradingService().manual_crypto_order(
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


@router.get("/upbit/universe", response_model=UpbitUniverseResponse)
async def upbit_universe():
    markets = UpbitUniverseService().get()
    return UpbitUniverseResponse(
        markets=markets,
        count=len(markets),
    )


@router.post("/upbit/universe/auto", response_model=UpbitUniverseResponse)
async def auto_upbit_universe(limit: int = Query(10, ge=1, le=50)):
    markets = await UpbitUniverseSelector().select(limit=limit)
    return UpbitUniverseResponse(markets=markets, count=len(markets))


@router.put("/upbit/universe", response_model=UpbitUniverseResponse)
async def update_upbit_universe(payload: UpbitUniverseUpdate):
    available = await UpbitMarketDataAdapter().list_markets(
        quote_currency="KRW",
        details=True,
    )
    available_codes = {item.market for item in available}
    requested = [
        value.strip().upper()
        for value in payload.markets
        if value.strip()
    ]
    invalid = sorted(set(requested) - available_codes)

    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Unknown Upbit KRW markets.",
                "markets": invalid,
            },
        )

    markets = UpbitUniverseService().set(requested)
    return UpbitUniverseResponse(
        markets=markets,
        count=len(markets),
    )


@router.get("/upbit/accounts", response_model=UpbitAccountStatus)
async def upbit_accounts():
    return await UpbitAccountAdapter().balances()
