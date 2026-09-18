from decimal import Decimal

from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    PaperPortfolio,
    PaperPosition,
    SymbolDecision,
)
from backend.app.services.position_sizer import PositionSizer


def portfolio(with_position: bool = False) -> PaperPortfolio:
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
        market="crypto",
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


def test_buy_score_85_sizes_three_percent_of_equity():
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
    assert result.order_notional == Decimal("60000.00000000")


def test_buy_below_threshold_creates_no_order():
    sizer = PositionSizer()
    decision = SymbolDecision(
        market="crypto",
        symbol="BTC",
        action="BUY",
        score=55,
        reason="test",
    )
    result = sizer.size(
        decision=decision,
        instrument=instrument(),
        portfolio=portfolio(),
    )
    assert result.status == "NO_ORDER"


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
        portfolio=portfolio(),
    )
    assert result.status == "ORDER"
    assert result.order_quantity == Decimal("1")
    assert result.order_notional == Decimal("70000")
