from decimal import Decimal

from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    PaperPortfolio,
    PaperPosition,
    SymbolDecision,
)
from backend.app.services.position_sizer import PositionSizer


def portfolio(with_position: bool = False, market: str = "crypto") -> PaperPortfolio:
    positions = []
    if with_position:
        positions.append(
            PaperPosition(
                market="crypto",
                symbol="BTC",
                name="Bitcoin",
                quantity=Decimal("0.01"),
                average_price=Decimal("90000000"),
                last_price=Decimal("100000000"),
                invested_amount=Decimal("900000"),
                market_value=Decimal("1000000"),
                return_rate=Decimal("11.11"),
                realized_pnl=Decimal("0"),
            )
        )

    return PaperPortfolio(
        market=market,
        date="2026-09-19",
        cash=Decimal("1000000"),
        initial_cash=Decimal("2000000"),
        day_start_equity=Decimal("2000000"),
        equity=Decimal("2000000"),
        positions=positions,
    )


def instrument(market: str = "crypto") -> MarketInstrumentSnapshot:
    return MarketInstrumentSnapshot(
        market=market,
        symbol="BTC" if market == "crypto" else "005930",
        name="Bitcoin" if market == "crypto" else "Samsung",
        price=Decimal("100000000") if market == "crypto" else Decimal("70000"),
    )


def test_buy_score_85_targets_fifteen_percent_of_equity():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="crypto",
        symbol="BTC",
        name="Bitcoin",
        action="BUY",
        score=85,
        reason="test",
    )
    result = sizer.size(
        decision=decision,
        instrument=instrument(),
        portfolio=portfolio(),
    )
    assert result.status == "ORDER"
    assert result.order_notional == Decimal("300000.00000000")


def test_buy_below_configured_sizing_threshold_creates_no_order():
    sizer = PositionSizer()
    old_threshold = sizer.config.position_buy_min_score

    try:
        sizer.config.position_buy_min_score = 70
        decision = SymbolDecision(
            market="crypto",
            symbol="BTC",
            action="BUY",
            score=65,
            reason="test",
        )
        result = sizer.size(
            decision=decision,
            instrument=instrument(),
            portfolio=portfolio(),
        )
        assert result.status == "NO_ORDER"
    finally:
        sizer.config.position_buy_min_score = old_threshold


def test_sell_very_low_score_sells_sixty_percent():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="crypto",
        symbol="BTC",
        action="SELL",
        score=15,
        reason="test",
    )
    result = sizer.size(
        decision=decision,
        instrument=instrument(),
        portfolio=portfolio(with_position=True),
    )
    assert result.status == "ORDER"
    assert result.order_quantity == Decimal("0.00600000")


def test_stock_buy_rounds_down_to_whole_share():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="stock",
        symbol="005930",
        name="Samsung",
        action="BUY",
        score=90,
        reason="test",
    )
    result = sizer.size(
        decision=decision,
        instrument=instrument("stock"),
        portfolio=portfolio(market="stock"),
    )
    assert result.status == "ORDER"
    assert result.order_quantity == Decimal("1")
    assert result.order_notional == Decimal("70000")


def test_buy_size_is_reduced_by_quant_volatility_scale():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="crypto",
        symbol="BTC",
        action="BUY",
        score=85,
        reason="test",
    )
    value = instrument()
    value.features = {"quant_risk_scale": 0.5}

    result = sizer.size(
        decision=decision,
        instrument=value,
        portfolio=portfolio(),
    )

    assert result.status == "ORDER"
    assert result.order_notional == Decimal("150000.00000000")



def test_stock_buy_creates_one_share_candidate_when_target_is_below_one_share():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="stock",
        symbol="000660",
        name="SK hynix",
        action="BUY",
        score=70,
        reason="test",
    )
    value = instrument("stock")
    value.symbol = "000660"
    value.price = Decimal("700000")

    result = sizer.size(
        decision=decision,
        instrument=value,
        portfolio=portfolio(market="stock"),
    )

    assert result.status == "ORDER"
    assert result.order_quantity == Decimal("1")
    assert result.order_notional == Decimal("700000")
    assert "최소 1주" in result.reason


def test_buy_only_fills_gap_to_target_position():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="crypto",
        symbol="BTC",
        name="Bitcoin",
        action="BUY",
        score=85,
        reason="test",
    )

    result = sizer.size(
        decision=decision,
        instrument=instrument(),
        portfolio=portfolio(with_position=True),
    )

    assert result.status == "NO_ORDER"
    assert "목표 비중 이상" in result.reason
