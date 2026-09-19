from fastapi import APIRouter, Depends

from backend.app.core.config import get_settings
from backend.app.core.security import require_api_token
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.llm_budget import LLMBudgetService
from backend.app.services.llm_runtime import LLMRuntimeStateService
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.upbit_universe import UpbitUniverseService
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_order_service import LiveOrderService
from backend.app.services.device_tokens import DeviceTokenService
from backend.app.services.scheduler_state import SchedulerStateService
from backend.app.services.readiness import ReadinessService
from backend.app.services.external_readiness import ExternalReadinessService


router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status", dependencies=[Depends(require_api_token)])
async def status():
    config = get_settings()
    runtime = RuntimeSettingsService().get()
    return {
        "app_env": config.app_env,
        "mode": runtime.mode,
        "kill_switch": runtime.kill_switch,
        "live_order_allowed": runtime.live_order_allowed,
        "scheduler_enabled": config.scheduler_enabled,
        "next_decision_at": (
            SchedulerStateService().next_decision_at().isoformat()
            if SchedulerStateService().next_decision_at() is not None
            else None
        ),
        "news_collection_interval_hours": config.news_collection_interval_hours,
        "data_retention_days": config.data_retention_days,
        "llm_budget": LLMBudgetService().status(),
        "llm_runtime": LLMRuntimeStateService().status(),
        "risk_policy": RiskGuard().policy(),
        "live_orders": {
            "enablement": LiveOrderService().enablement(),
            "unresolved_count": len(
                LiveOrderJournal().unresolved(limit=200)
            ),
        },
        "push": DeviceTokenService().status(),
        "upbit": {
            "decision_universe": UpbitUniverseService().get(),
            "public_market_data": True,
            "private_account_api_configured": bool(
                config.upbit_access_key and config.upbit_secret_key
            ),
        },
        "toss": {
            "decision_universe": TossUniverseService().get(),
            "oauth_configured": bool(
                config.toss_client_id and config.toss_client_secret
            ),
            "account_seq_configured": config.toss_account_seq is not None,
            "live_orders_implemented": True,
        },
        "decision_interval": {
            "default": config.decision_default_interval_minutes,
            "min": config.decision_min_interval_minutes,
            "max": config.decision_max_interval_minutes,
        },
    }



@router.get("/readiness", dependencies=[Depends(require_api_token)])
async def readiness():
    return ReadinessService().status()



@router.get(
    "/readiness/external",
    dependencies=[Depends(require_api_token)],
)
async def external_readiness():
    """Read-only broker/connectivity checks. Never submits an order."""
    return await ExternalReadinessService().check()
