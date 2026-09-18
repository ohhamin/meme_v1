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


class SymbolDecision(BaseModel):
    market: Literal["stock", "crypto"]
    symbol: str
    name: str | None = None
    action: Literal["BUY", "SELL", "HOLD"]
    score: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=1000)


class DecisionCycleResult(BaseModel):
    decisions: list[SymbolDecision]
    next_check_minutes: int = Field(ge=30, le=120)
    cycle_summary: str = Field(min_length=1, max_length=1200)


class DecisionPreviewRequest(BaseModel):
    market_snapshot: dict
    account_snapshot: dict


class DecisionPreviewResponse(BaseModel):
    status: Literal["completed", "blocked"]
    mode: str
    estimated_input_tokens: int
    result: DecisionCycleResult | None = None
    reason: str | None = None


class RiskOrderIntent(BaseModel):
    source: Literal["auto", "manual"] = "auto"
    market: Literal["stock", "crypto"]
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]

    # 주문 예정 값. Risk Guard는 값을 계산하지 않고 검증만 한다.
    order_notional: Decimal = Field(default=Decimal("0"), ge=0)
    order_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    price: Decimal = Field(default=Decimal("0"), ge=0)

    # 주문 시점 계좌/시장 snapshot.
    portfolio_equity: Decimal = Field(gt=0)
    available_cash: Decimal = Field(ge=0)
    position_value: Decimal = Field(default=Decimal("0"), ge=0)
    position_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    market_exposure_value: Decimal = Field(default=Decimal("0"), ge=0)

    daily_pnl_pct: Decimal = Decimal("0")
    daily_order_count: int = Field(default=0, ge=0)
    data_age_seconds: int = Field(default=0, ge=0)
    market_open: bool = True
    same_cycle_duplicate: bool = False


class RiskGuardResult(BaseModel):
    status: Literal["PASS", "BLOCK", "NO_ORDER"]
    reasons: list[str] = Field(default_factory=list)
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]


class MarketInstrumentSnapshot(BaseModel):
    market: Literal["stock", "crypto"]
    symbol: str
    name: str | None = None
    price: Decimal = Field(gt=0)
    data_age_seconds: int = Field(default=0, ge=0)
    market_open: bool = True


class PositionSizeResult(BaseModel):
    status: Literal["ORDER", "NO_ORDER"]
    market: Literal["stock", "crypto"]
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]
    score: int = Field(ge=0, le=100)
    order_notional: Decimal = Field(default=Decimal("0"), ge=0)
    order_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    reason: str


class PaperPosition(BaseModel):
    market: Literal["stock", "crypto"]
    symbol: str
    name: str
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    average_price: Decimal = Field(default=Decimal("0"), ge=0)
    last_price: Decimal = Field(default=Decimal("0"), ge=0)
    invested_amount: Decimal = Field(default=Decimal("0"), ge=0)
    market_value: Decimal = Field(default=Decimal("0"), ge=0)
    return_rate: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    decision_score: int | None = Field(default=None, ge=0, le=100)


class PaperPortfolio(BaseModel):
    date: str
    cash: Decimal = Field(ge=0)
    initial_cash: Decimal = Field(gt=0)
    day_start_equity: Decimal = Field(gt=0)
    equity: Decimal = Field(gt=0)
    daily_pnl: Decimal = Decimal("0")
    daily_pnl_pct: Decimal = Decimal("0")
    daily_order_count: int = Field(default=0, ge=0)
    positions: list[PaperPosition] = Field(default_factory=list)


class PaperOrderExecution(BaseModel):
    order_id: str
    market: Literal["stock", "crypto"]
    symbol: str
    side: Literal["buy", "sell"]
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    notional: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    status: Literal["paper_filled"]
    created_at: datetime


class CycleExecutionItem(BaseModel):
    decision: SymbolDecision
    sizing: PositionSizeResult
    risk: RiskGuardResult | None = None
    order: PaperOrderExecution | None = None


class PaperCycleRequest(BaseModel):
    market_snapshot: list[MarketInstrumentSnapshot]


class PaperCycleResponse(BaseModel):
    status: Literal["completed", "blocked"]
    next_check_minutes: int | None = None
    cycle_summary: str | None = None
    items: list[CycleExecutionItem] = Field(default_factory=list)
    portfolio: PaperPortfolio | None = None
    reason: str | None = None
