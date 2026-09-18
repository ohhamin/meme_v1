from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.routers import (
    algorithm,
    crypto,
    decisions,
    health,
    news,
    paper,
    risk,
    settings,
    stocks,
)
from backend.app.services.algorithm import AlgorithmService
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.push import PushService
from backend.app.services.scheduler import AdaptiveDecisionScheduler


scheduler = AdaptiveDecisionScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    RuntimeSettingsService().get()
    AlgorithmService()
    PushService().initialize()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="meme_v1 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(stocks.router)
app.include_router(crypto.router)
app.include_router(news.router)
app.include_router(decisions.router)
app.include_router(algorithm.router)
app.include_router(paper.router)
app.include_router(risk.router)
app.include_router(settings.router)
