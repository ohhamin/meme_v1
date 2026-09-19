from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.routers import (
    algorithm,
    crypto,
    decisions,
    devices,
    health,
    live_orders,
    news,
    paper,
    risk,
    scheduler_status,
    settings,
    stocks,
)
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.push import PushService
from backend.app.services.scheduler import AdaptiveDecisionScheduler
from backend.app.services.startup_maintenance import StartupMaintenanceService
from backend.app.services.safety_config import SafetyConfigValidator
from backend.app.services.audit import AuditLogger


scheduler = AdaptiveDecisionScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    safety = SafetyConfigValidator().require_safe_startup()
    for warning in safety.warnings:
        AuditLogger().write(
            "system",
            {
                "event": "startup_safety_warning",
                "warning": warning,
            },
        )

    RuntimeSettingsService().get()
    AlgorithmService()
    PushService().initialize()
    await StartupMaintenanceService().run()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="meme_v1 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(devices.router)
app.include_router(live_orders.router)
app.include_router(stocks.router)
app.include_router(crypto.router)
app.include_router(news.router)
app.include_router(decisions.router)
app.include_router(algorithm.router)
app.include_router(paper.router)
app.include_router(risk.router)
app.include_router(scheduler_status.router)
app.include_router(settings.router)
