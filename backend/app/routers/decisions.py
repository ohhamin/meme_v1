from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import DailyMarkdown
from backend.app.services.file_store import DailyMarkdownStore


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
