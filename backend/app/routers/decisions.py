from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    DailyMarkdown,
    LatestDecisionResponse,
    DecisionPreviewRequest,
    DecisionPreviewResponse,
    PaperCycleRequest,
    PaperCycleResponse,
    LiveAutoCycleResponse,
)
from backend.app.services.file_store import DailyMarkdownStore
from backend.app.services.decision_cycle import DecisionCycleService
from backend.app.services.paper_auto_cycle import PaperAutoCycleService
from backend.app.services.combined_paper_runner import CombinedPaperRunner
from backend.app.services.live_auto_cycle import LiveAutoCycleService
from backend.app.services.latest_decision import LatestDecisionService
from backend.app.services.runtime_settings import RuntimeSettingsService


router = APIRouter(
    prefix="/decisions",
    tags=["decisions"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/dates")
async def dates():
    return {"dates": DailyMarkdownStore("decisions").available_dates(limit=7)}


@router.get("/latest", response_model=LatestDecisionResponse | None)
async def latest():
    mode = RuntimeSettingsService().get().mode
    return LatestDecisionService().get(mode=mode)


@router.get("/{day}", response_model=DailyMarkdown)
async def by_date(day: str):
    store = DailyMarkdownStore("decisions")
    mode = RuntimeSettingsService().get().mode
    markdown = LatestDecisionService().filter_markdown(
        store.read(day),
        mode,
    )
    return DailyMarkdown(date=day, markdown=markdown)


@router.post("/preview", response_model=DecisionPreviewResponse)
async def preview(payload: DecisionPreviewRequest):
    """Broker 연결 전 LLM 판단 파이프라인을 검증하는 무주문 preview."""
    return await DecisionCycleService().preview(
        market_snapshot=payload.market_snapshot,
        account_snapshot=payload.account_snapshot,
    )


@router.post("/paper-cycle", response_model=PaperCycleResponse)
async def paper_cycle(payload: PaperCycleRequest):
    """LLM -> Position Sizer -> Risk Guard -> Paper Broker 전체 사이클."""
    return await PaperAutoCycleService().run(
        instruments=payload.market_snapshot,
    )


@router.post("/market-paper-cycle", response_model=PaperCycleResponse)
async def market_paper_cycle():
    """Fetch Toss/Upbit market data and run one combined Paper cycle."""
    return await CombinedPaperRunner().run()


@router.post("/live-cycle", response_model=LiveAutoCycleResponse)
async def live_cycle():
    """Explicitly run one live automatic cycle; all env/runtime safety gates still apply."""
    return await LiveAutoCycleService().run()
