from fastapi import APIRouter, Depends

from backend.app.core.security import require_api_token
from backend.app.models.schemas import RiskGuardResult, RiskOrderIntent
from backend.app.services.risk_guard import RiskGuard


router = APIRouter(
    prefix="/risk",
    tags=["risk"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/policy")
async def policy():
    return RiskGuard().policy()


@router.post("/preview", response_model=RiskGuardResult)
async def preview(payload: RiskOrderIntent):
    """주문 없이 Risk Guard 규칙만 검증한다."""
    return RiskGuard().evaluate(payload)
