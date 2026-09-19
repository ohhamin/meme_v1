import pytest

from backend.app.models.schemas import DecisionCycleResult
from backend.app.services.context_compactor import CompactDecisionContext
from backend.app.services.openai_decision import LLMDecisionClient


def context():
    return CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        market_snapshot={
            "instruments": [
                {
                    "market": "crypto",
                    "symbol": "KRW-BTC",
                },
                {
                    "market": "stock",
                    "symbol": "005930",
                },
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )


def result(decisions):
    return DecisionCycleResult(
        decisions=decisions,
        next_check_minutes=60,
        cycle_summary="test",
    )


def test_decision_coverage_accepts_exact_universe():
    value = result(
        [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
            },
            {
                "market": "stock",
                "symbol": "005930",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
            },
        ]
    )

    LLMDecisionClient._validate_decision_coverage(
        context=context(),
        result=value,
    )


def test_decision_coverage_rejects_missing_symbol():
    value = result(
        [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
            }
        ]
    )

    with pytest.raises(ValueError):
        LLMDecisionClient._validate_decision_coverage(
            context=context(),
            result=value,
        )


def test_decision_coverage_rejects_hallucinated_symbol():
    value = result(
        [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
            },
            {
                "market": "stock",
                "symbol": "000660",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
            },
        ]
    )

    with pytest.raises(ValueError):
        LLMDecisionClient._validate_decision_coverage(
            context=context(),
            result=value,
        )
