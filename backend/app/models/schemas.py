from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Side = Literal["buy", "sell"]
Mode = Literal["paper", "live"]


class Position(BaseModel):
    symbol: str
    name: str
    invested_amount: Decimal = Decimal("0")
    quantity: Decimal = Decimal("0")
    return_rate: Decimal = Decimal("0")
    decision_score: int | None = Field(default=None, ge=0, le=100)


class StockManualOrderRequest(BaseModel):
    symbol: str
    side: Side
    quantity: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CryptoManualOrderRequest(BaseModel):
    symbol: str
    side: Side
    amount_krw: Decimal = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class OrderResult(BaseModel):
    order_id: str
    symbol: str
    side: Side
    status: Literal["paper_filled", "submitted", "blocked"]
    message: str
    created_at: datetime


class RuntimeSettings(BaseModel):
    mode: Mode = "paper"
    kill_switch: bool = True
    live_order_allowed: bool = False


class ModeUpdate(BaseModel):
    mode: Mode


class KillSwitchUpdate(BaseModel):
    enabled: bool


class DailyMarkdown(BaseModel):
    date: str
    markdown: str


class AlgorithmProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)
    rule_text: str = Field(min_length=1, max_length=8000)


class AlgorithmProposal(BaseModel):
    id: str
    title: str
    markdown: str
    created_at: datetime | None = None


class DecisionResult(BaseModel):
    market: Literal["stock", "crypto"]
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]
    score: int = Field(ge=0, le=100)
    reason: str
    risk_blocked: bool
    risk_reason: str | None = None
    next_check_minutes: int = Field(ge=30, le=120)

    @model_validator(mode="after")
    def blocked_reason_required(self):
        if self.risk_blocked and not self.risk_reason:
            raise ValueError("risk_reason is required when risk_blocked=true")
        return self
