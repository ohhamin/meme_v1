from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.services.runtime_settings import RuntimeSettingsService


router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status():
    config = get_settings()
    runtime = RuntimeSettingsService().get()
    return {
        "app_env": config.app_env,
        "mode": runtime.mode,
        "kill_switch": runtime.kill_switch,
        "live_order_allowed": runtime.live_order_allowed,
        "scheduler_enabled": config.scheduler_enabled,
        "decision_interval": {
            "default": config.decision_default_interval_minutes,
            "min": config.decision_min_interval_minutes,
            "max": config.decision_max_interval_minutes,
        },
    }
