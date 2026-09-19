from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import (
    KillSwitchUpdate,
    ModeUpdate,
    RuntimeSettings,
    SchedulerUpdate,
)
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.llm_runtime import LLMRuntimeStateService


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(require_api_token)],
)


@router.get("", response_model=RuntimeSettings)
async def get_runtime_settings():
    return RuntimeSettingsService().get()


@router.put("/mode", response_model=RuntimeSettings)
async def update_mode(payload: ModeUpdate):
    return RuntimeSettingsService().set_mode(payload.mode)


@router.put("/kill-switch", response_model=RuntimeSettings)
async def update_kill_switch(payload: KillSwitchUpdate):
    return RuntimeSettingsService().set_kill_switch(payload.enabled)


@router.post("/llm/resume")
async def resume_llm():
    """API key/quota 문제를 해결한 뒤 사용자가 명시적으로 LLM을 재개한다."""
    return LLMRuntimeStateService().resume()


@router.put("/scheduler")
async def update_scheduler(payload: SchedulerUpdate):
    """Pause/resume all scheduled automation, including news and trading AI."""
    from backend.app.main import scheduler

    return scheduler.set_enabled(payload.enabled)
