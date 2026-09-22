from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.paper_risk_monitor import PaperRiskMonitor


def make_monitor() -> PaperRiskMonitor:
    monitor = object.__new__(PaperRiskMonitor)
    monitor.config = SimpleNamespace(
        risk_hard_stop_loss_pct=5.0,
        risk_trailing_activation_pct=10.0,
        risk_trailing_stop_pct=5.0,
        risk_crypto_hard_stop_loss_pct=7.0,
        risk_crypto_trailing_activation_pct=7.0,
        risk_crypto_trailing_min_pct=4.0,
        risk_crypto_trailing_max_pct=7.0,
        risk_crypto_trailing_vol_multiplier=1.25,
    )
    return monitor


def position(*, average, last, peak):
    return SimpleNamespace(
        average_price=Decimal(str(average)),
        last_price=Decimal(str(last)),
        highest_price_since_entry=Decimal(str(peak)),
    )


def test_hard_stop_triggers_at_minus_five_percent():
    reason = make_monitor()._exit_reason(
        position(average=100, last=95, peak=103)
    )
    assert reason is not None
    assert reason.startswith("HARD_STOP")


def test_trailing_stop_is_inactive_before_ten_percent_gain():
    reason = make_monitor()._exit_reason(
        position(average=100, last=103, peak=109)
    )
    assert reason is None


def test_trailing_stop_triggers_after_activation_and_five_percent_drawdown():
    reason = make_monitor()._exit_reason(
        position(average=100, last=104.5, peak=110)
    )
    assert reason is not None
    assert reason.startswith("TRAILING_STOP")


def test_trailing_stop_does_not_trigger_while_drawdown_is_small():
    reason = make_monitor()._exit_reason(
        position(average=100, last=107, peak=110)
    )
    assert reason is None



def instrument(volatility):
    return SimpleNamespace(
        features={"realized_volatility_pct": volatility},
    )


def test_crypto_hard_stop_triggers_at_minus_seven_percent():
    reason = make_monitor()._exit_reason(
        position(average=100, last=93, peak=104),
        market="crypto",
        instrument=instrument(4.0),
    )
    assert reason is not None
    assert reason.startswith("HARD_STOP")


def test_crypto_trailing_activates_at_seven_percent():
    reason = make_monitor()._exit_reason(
        position(average=100, last=102.5, peak=108),
        market="crypto",
        instrument=instrument(4.0),
    )
    assert reason is not None
    assert reason.startswith("TRAILING_STOP")


def test_crypto_trailing_width_scales_with_volatility_and_is_capped():
    monitor = make_monitor()
    assert monitor._crypto_trailing_stop(instrument(2.0)) == Decimal("4.00")
    assert monitor._crypto_trailing_stop(instrument(4.0)) == Decimal("5.00")
    assert monitor._crypto_trailing_stop(instrument(8.0)) == Decimal("7.00")
