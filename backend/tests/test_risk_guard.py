from decimal import Decimal
from types import SimpleNamespace

from backend.app.models.schemas import RiskOrderIntent
from backend.app.services.risk_guard import RiskGuard


def make_guard() -> RiskGuard:
    guard = RiskGuard()
    guard.runtime.get = lambda: SimpleNamespace(kill_switch=False)
    guard.audit.write = lambda *args, **kwargs: None
    return guard


def make_intent(**overrides) -> RiskOrderIntent:
    data = {
        "source": "auto",
        "market": "crypto",
        "symbol": "BTC",
        "action": "BUY",
        "order_notional": Decimal("30000"),
        "order_quantity": Decimal("0.0003"),
        "price": Decimal("100000000"),
        "portfolio_equity": Decimal("1000000"),
        "available_cash": Decimal("500000"),
        "position_value": Decimal("20000"),
        "position_quantity": Decimal("0.0002"),
        "daily_pnl_pct": Decimal("-1.0"),
        "daily_order_count": 3,
        "data_age_seconds": 30,
        "market_open": True,
        "same_cycle_duplicate": False,
    }
    data.update(overrides)
    return RiskOrderIntent(**data)


def test_hold_creates_no_order():
    result = make_guard().evaluate(make_intent(action="HOLD"))
    assert result.status == "NO_ORDER"


def test_buy_passes_when_within_hard_limits():
    result = make_guard().evaluate(make_intent())
    assert result.status == "PASS"
    assert result.reasons == []


def test_buy_blocks_when_snapshot_is_stale():
    result = make_guard().evaluate(make_intent(data_age_seconds=999))
    assert result.status == "BLOCK"
    assert any("stale" in reason for reason in result.reasons)


def test_buy_blocks_after_daily_loss_limit():
    result = make_guard().evaluate(make_intent(daily_pnl_pct=Decimal("-3.5")))
    assert result.status == "BLOCK"
    assert any("Daily loss" in reason for reason in result.reasons)


def test_buy_blocks_concentrated_position():
    result = make_guard().evaluate(
        make_intent(
            position_value=Decimal("390000"),
            order_notional=Decimal("30000"),
        )
    )
    assert result.status == "BLOCK"
    assert any("Position exposure" in reason for reason in result.reasons)


def test_sell_is_allowed_to_reduce_risk_even_after_daily_loss():
    result = make_guard().evaluate(
        make_intent(
            action="SELL",
            order_notional=Decimal("20000"),
            order_quantity=Decimal("0.0001"),
            position_quantity=Decimal("0.0002"),
            daily_pnl_pct=Decimal("-9"),
            daily_order_count=999,
            available_cash=Decimal("0"),
        )
    )
    assert result.status == "PASS"


def test_sell_blocks_when_quantity_exceeds_holding():
    result = make_guard().evaluate(
        make_intent(
            action="SELL",
            order_notional=Decimal("30000"),
            order_quantity=Decimal("0.001"),
            position_quantity=Decimal("0.0002"),
        )
    )
    assert result.status == "BLOCK"
    assert any("exceeds current position" in reason for reason in result.reasons)


def test_large_single_order_is_allowed_when_position_ratio_is_safe():
    result = make_guard().evaluate(
        make_intent(
            position_value=Decimal("0"),
            position_quantity=Decimal("0"),
            order_notional=Decimal("300000"),
            order_quantity=Decimal("0.003"),
            available_cash=Decimal("500000"),
        )
    )
    assert result.status == "PASS"


def test_new_position_is_blocked_when_ten_are_already_open():
    result = make_guard().evaluate(
        make_intent(
            position_value=Decimal("0"),
            position_quantity=Decimal("0"),
            open_position_count=10,
        )
    )
    assert result.status == "BLOCK"
    assert any("Maximum open position count" in reason for reason in result.reasons)


def test_existing_position_can_be_added_to_when_ten_are_open():
    result = make_guard().evaluate(
        make_intent(
            position_value=Decimal("20000"),
            position_quantity=Decimal("0.0002"),
            open_position_count=10,
        )
    )
    assert result.status == "PASS"



def test_auto_symbol_cooldown_blocks_repeat_order():
    result = make_guard().evaluate(
        make_intent(
            source="auto",
            seconds_since_last_auto_order=1800,
        )
    )

    assert result.status == "BLOCK"
    assert any(
        "cooldown" in reason.lower()
        for reason in result.reasons
    )


def test_manual_order_is_not_blocked_by_auto_symbol_cooldown():
    result = make_guard().evaluate(
        make_intent(
            source="manual",
            seconds_since_last_auto_order=60,
        )
    )

    assert result.status == "PASS"
