from fastapi import APIRouter, Depends, status

from backend.app.core.security import require_api_token
from backend.app.models.schemas import AlgorithmProposalCreate
from backend.app.services.algorithm import AlgorithmService


router = APIRouter(
    prefix="/algorithm",
    tags=["algorithm"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/current")
async def current():
    return {"markdown": AlgorithmService().current()}


@router.get("/proposals")
async def proposals():
    return {"items": AlgorithmService().list_pending()}


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def create_proposal(payload: AlgorithmProposalCreate):
    return AlgorithmService().create(payload)


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str):
    return {
        "status": "applied",
        "markdown": AlgorithmService().apply(proposal_id),
    }


@router.post("/proposals/{proposal_id}/cancel")
async def cancel_proposal(proposal_id: str):
    AlgorithmService().cancel(proposal_id)
    return {"status": "cancelled"}
