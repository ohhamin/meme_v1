from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    DailyMarkdown,
    DecisionPreviewRequest,
    DecisionPreviewResponse,
)
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.decision_cycle import DecisionCycleService


router = APIRouter(
    prefix="/decisions",
    tags=["decisions"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/dates")
async def dates():
    return {"dates": DailyMarkdownStore("decisions").available_dates(limit=7)}


@router.get("/{day}", response_model=DailyMarkdown)
async def by_date(day: str):
    store = DailyMarkdownStore("decisions")
    return DailyMarkdown(date=day, markdown=store.read(day))


@router.post("/preview", response_model=DecisionPreviewResponse)
async def preview(payload: DecisionPreviewRequest):
    """Broker 연결 전 LLM 판단 파이프라인을 검증하는 무주문 preview."""
    return await DecisionCycleService().preview(
        market_snapshot=payload.market_snapshot,
        account_snapshot=payload.account_snapshot,
    )
