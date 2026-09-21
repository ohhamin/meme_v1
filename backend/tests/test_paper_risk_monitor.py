from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.paper_risk_monitor import PaperRiskMonitor


def make_monitor() -> PaperRiskMonitor:
    monitor = object.__new__(PaperRiskMonitor)
    monitor.config = SimpleNamespace(
        risk_hard_stop_loss_pct=5.0,
        risk_trailing_activation_pct=10.0,
        risk_trailing_stop_pct=5.0,
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
