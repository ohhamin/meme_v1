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

    open_position_count: int = Field(default=0, ge=0)
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
    last_price_at: datetime | None = None
    last_market_open: bool = True
    invested_amount: Decimal = Field(default=Decimal("0"), ge=0)
    market_value: Decimal = Field(default=Decimal("0"), ge=0)
    return_rate: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    decision_score: int | None = Field(default=None, ge=0, le=100)


class PaperPortfolio(BaseModel):
    market: Literal["stock", "crypto"]
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
    portfolios: dict[str, PaperPortfolio] | None = None
    reason: str | None = None


class PaperResetRequest(BaseModel):
    market: Literal["stock", "crypto", "all"] = "all"
    initial_cash: Decimal | None = Field(default=None, gt=0)


class PaperAccountsResponse(BaseModel):
    stock: PaperPortfolio
    crypto: PaperPortfolio


class UpbitMarketInfo(BaseModel):
    market: str
    korean_name: str
    english_name: str
    warning: bool = False
    caution: bool = False


class UpbitQuote(BaseModel):
    market: str
    korean_name: str | None = None
    english_name: str | None = None
    trade_price: Decimal = Field(gt=0)
    signed_change_rate: Decimal | None = None
    acc_trade_price_24h: Decimal | None = None
    timestamp: datetime
    data_age_seconds: int = Field(ge=0)


class UpbitPaperRunRequest(BaseModel):
    markets: list[str] = Field(default_factory=list, max_length=100)


class UpbitPaperRunResponse(BaseModel):
    markets: list[str]
    cycle: PaperCycleResponse


class UpbitUniverseUpdate(BaseModel):
    markets: list[str] = Field(default_factory=list, max_length=100)


class UpbitUniverseResponse(BaseModel):
    markets: list[str]
    count: int = Field(ge=0)


class UpbitAccountAsset(BaseModel):
    currency: str
    balance: Decimal = Field(ge=0)
    locked: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)
    avg_buy_price: Decimal = Field(ge=0)
    unit_currency: str = "KRW"


class UpbitAccountStatus(BaseModel):
    configured: bool
    assets: list[UpbitAccountAsset] = Field(default_factory=list)


class TossStockInfo(BaseModel):
    symbol: str
    name: str
    english_name: str | None = None
    market: str
    security_type: str
    status: str
    currency: str
    nxt_supported: bool = False
    trading_suspended: bool = False


class TossQuote(BaseModel):
    symbol: str
    last_price: Decimal = Field(gt=0)
    currency: str
    timestamp: datetime | None = None
    data_age_seconds: int = Field(ge=0)


class TossAccount(BaseModel):
    account_seq: int
    account_type: str


class TossHolding(BaseModel):
    symbol: str
    name: str
    quantity: Decimal = Field(ge=0)
    last_price: Decimal = Field(ge=0)
    average_purchase_price: Decimal = Field(ge=0)
    purchase_amount: Decimal = Field(ge=0)
    market_value: Decimal = Field(ge=0)
    return_rate: Decimal = Decimal("0")


class TossAccountStatus(BaseModel):
    configured: bool
    account_seq: int | None = None
    cash_buying_power: Decimal = Decimal("0")
    holdings: list[TossHolding] = Field(default_factory=list)


class TossUniverseUpdate(BaseModel):
    symbols: list[str] = Field(default_factory=list, max_length=200)


class TossUniverseResponse(BaseModel):
    symbols: list[str]
    count: int = Field(ge=0)


class LiveOrderRecord(BaseModel):
    intent_id: str
    broker: Literal["upbit", "toss"]
    source: Literal["manual", "auto"]
    market: Literal["stock", "crypto"]
    symbol: str
    side: Literal["buy", "sell"]
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    notional: Decimal = Field(default=Decimal("0"), ge=0)
    reference_price: Decimal = Field(default=Decimal("0"), ge=0)
    client_order_id: str
    status: Literal[
        "CREATED",
        "PREFLIGHTED",
        "SUBMITTING",
        "SUBMITTED",
        "CONFIRMED",
        "REJECTED",
        "UNKNOWN",
    ]
    broker_order_id: str | None = None
    broker_status: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class LiveOrderPreflightResult(BaseModel):
    allowed: bool
    broker: Literal["upbit", "toss"]
    symbol: str
    side: Literal["buy", "sell"]
    reasons: list[str] = Field(default_factory=list)


class LiveOrderExecutionResult(BaseModel):
    status: Literal["submitted", "confirmed", "rejected", "unknown", "blocked"]
    record: LiveOrderRecord
    message: str


class LiveOrderReconcileResponse(BaseModel):
    updated: int = Field(ge=0)
    unresolved: int = Field(ge=0)
    records: list[LiveOrderRecord] = Field(default_factory=list)


class LiveOrderEnablement(BaseModel):
    trading_enabled: bool
    live_manual_order_enabled: bool
    live_auto_order_enabled: bool
    upbit_live_order_enabled: bool
    toss_live_order_enabled: bool


class LiveCycleExecutionItem(BaseModel):
    decision: SymbolDecision
    sizing: PositionSizeResult
    risk: RiskGuardResult | None = None
    live_order: LiveOrderRecord | None = None
    message: str | None = None


class LiveAutoCycleResponse(BaseModel):
    status: Literal["completed", "blocked"]
    next_check_minutes: int | None = None
    cycle_summary: str | None = None
    items: list[LiveCycleExecutionItem] = Field(default_factory=list)
    reason: str | None = None
