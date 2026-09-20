from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.security import require_api_token
from backend.app.models.schemas import AlgorithmProposalCreate
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.algorithm_review import AlgorithmReviewService
from backend.app.services.quant_backtest import QuantBacktestService
from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter


router = APIRouter(
    prefix="/algorithm",
    tags=["algorithm"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/current")
async def current():
    return {"markdown": AlgorithmService().current()}


@router.get("/proposals")
async def proposals():
    return {"items": AlgorithmService().list_pending()}


@router.post("/backtest")
async def backtest(
    market: str = Query(..., pattern="^(stock|crypto)$"),
    symbol: str = Query(..., min_length=3, max_length=30),
    fee_bps: float = Query(5.0, ge=0, le=100),
    slippage_bps: float = Query(5.0, ge=0, le=100),
):
    try:
        if market == "stock":
            normalized = symbol.strip().upper()
            candles = await TossMarketDataAdapter().candles(
                normalized,
                interval="1d",
                count=200,
            )
        else:
            normalized = symbol.strip().upper()
            candles = await UpbitMarketDataAdapter().daily_candles(
                normalized,
                count=200,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Historical market data could not be loaded: "
                f"{type(exc).__name__}"
            ),
        ) from exc

    result = QuantBacktestService.simulate(
        market=market,
        candles=candles,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    result["symbol"] = normalized
    result["note"] = (
        "정량 방향 신호만 검증하며 AI veto, 포트폴리오 동시보유, "
        "실제 체결 지연은 포함하지 않습니다."
    )
    return result


@router.post("/review")
async def review_now():
    created = await AlgorithmReviewService().review()
    return {
        "status": "completed",
        "proposal_created": created,
    }


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def create_proposal(payload: AlgorithmProposalCreate):
    return AlgorithmService().create(payload)


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str):
    return {
        "status": "applied",
        "markdown": AlgorithmService().apply(proposal_id),
    }


@router.post("/proposals/{proposal_id}/cancel")
async def cancel_proposal(proposal_id: str):
    AlgorithmService().cancel(proposal_id)
    return {"status": "cancelled"}
