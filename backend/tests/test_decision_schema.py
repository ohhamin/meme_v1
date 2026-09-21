import pytest
from pydantic import ValidationError

from backend.app.models.schemas import DecisionCycleResult, SymbolDecision


@pytest.mark.parametrize(
    ("action", "score"),
    [
        ("BUY", 60),
        ("BUY", 100),
        ("HOLD", 41),
        ("HOLD", 59),
        ("SELL", 0),
        ("SELL", 40),
    ],
)
def test_decision_action_score_valid(action, score):
    value = SymbolDecision(
        market="crypto",
        symbol="KRW-BTC",
        action=action,
        score=score,
        reason="test",
    )
    assert value.score == score


@pytest.mark.parametrize(
    ("action", "score"),
    [
        ("BUY", 59),
        ("HOLD", 70),
        ("HOLD", 31),
        ("SELL", 41),
    ],
)
def test_decision_score_can_represent_quant_prior_independently(action, score):
    value = SymbolDecision(
        market="crypto",
        symbol="KRW-BTC",
        action=action,
        score=score,
        reason="test",
    )
    assert value.action == action
    assert value.score == score


def test_decision_cycle_rejects_duplicate_symbol():
    item = {
        "market": "crypto",
        "symbol": "KRW-BTC",
        "action": "HOLD",
        "score": 50,
        "reason": "test",
    }

    with pytest.raises(ValidationError):
        DecisionCycleResult(
            decisions=[item, item],
            next_check_minutes=60,
            cycle_summary="test",
        )
