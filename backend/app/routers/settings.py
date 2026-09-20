from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import KillSwitchUpdate, LLMDailyTokenBudgetUpdate, ModeUpdate, RuntimeSettings
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


@router.put("/llm/daily-token-budget", response_model=RuntimeSettings)
async def update_llm_daily_token_budget(payload: LLMDailyTokenBudgetUpdate):
    return RuntimeSettingsService().set_llm_daily_token_budget(payload.tokens)


@router.post("/llm/usage/refresh")
async def refresh_llm_usage():
    from backend.app.services.openai_usage_sync import OpenAIUsageSyncService
    return await OpenAIUsageSyncService().refresh()


@router.post("/llm/resume")
async def resume_llm():
    """API key/quota 문제를 해결한 뒤 사용자가 명시적으로 LLM을 재개한다."""
    return LLMRuntimeStateService().resume()
