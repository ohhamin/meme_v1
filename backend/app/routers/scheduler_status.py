from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import SchedulerToggleUpdate


router = APIRouter(
    prefix="/scheduler",
    tags=["scheduler"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/status")
async def scheduler_status():
    # Import lazily to avoid a circular import while main.py is creating the app.
    from backend.app.main import scheduler

    return scheduler.status()


@router.put("/enabled")
async def set_scheduler_enabled(payload: SchedulerToggleUpdate):
    # Import lazily to avoid a circular import while main.py is creating the app.
    from backend.app.main import scheduler

    return scheduler.set_enabled(payload.enabled)
