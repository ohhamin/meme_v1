from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import DailyMarkdown
from backend.app.services.file_store import DailyMarkdownStore


router = APIRouter(
    prefix="/news",
    tags=["news"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/dates")
async def dates():
    return {"dates": DailyMarkdownStore("news").available_dates(limit=7)}


@router.get("/{day}", response_model=DailyMarkdown)
async def by_date(day: str):
    store = DailyMarkdownStore("news")
    return DailyMarkdown(date=day, markdown=store.read(day))
