import pytest

from backend.app.models.schemas import DecisionCycleResult
from backend.app.services.context_compactor import CompactDecisionContext
from backend.app.services.openai_decision import LLMDecisionClient


def context():
    return CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
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


def test_quant_buy_cannot_be_reversed_to_sell():
    ctx = CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
        market_snapshot={
            "instruments": [
                {
                    "market": "crypto",
                    "symbol": "KRW-BTC",
                    "features": {
                        "quant_action": "BUY",
                        "quant_score": 72,
                    },
                },
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )
    value = result(
        [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "SELL",
                "score": 30,
                "reason": "news concern",
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(
        context=ctx,
        result=value,
    )

    assert value.decisions[0].action == "BUY"
    assert value.decisions[0].score == 68


def test_stock_composite_uses_weighted_components():
    ctx = CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
        market_snapshot={
            "instruments": [
                {
                    "market": "stock",
                    "symbol": "005930",
                    "features": {
                        "quant_action": "BUY",
                        "quant_score": 68,
                    },
                },
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )
    value = result(
        [
            {
                "market": "stock",
                "symbol": "005930",
                "action": "BUY",
                "score": 95,
                "reason": "context confirms",
                "market_sector_score": 80,
                "fundamental_score": 80,
                "news_event_score": 80,
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(
        context=ctx,
        result=value,
    )

    assert value.decisions[0].action == "BUY"
    assert value.decisions[0].score == 75



def test_quant_hold_preserves_quant_score():
    ctx = CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
        market_snapshot={
            "instruments": [
                {
                    "market": "stock",
                    "symbol": "009150",
                    "features": {
                        "quant_action": "HOLD",
                        "quant_score": 47,
                    },
                },
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )
    value = result(
        [
            {
                "market": "stock",
                "symbol": "009150",
                "action": "HOLD",
                "score": 50,
                "reason": "context neutral",
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(
        context=ctx,
        result=value,
    )

    assert value.decisions[0].action == "HOLD"
    assert value.decisions[0].score == 49
    assert "종합 49/100" in value.decisions[0].reason



def test_crypto_composite_is_technical_80_news_20():
    ctx = CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
        market_snapshot={
            "instruments": [
                {
                    "market": "crypto",
                    "symbol": "KRW-BTC",
                    "features": {
                        "quant_action": "HOLD",
                        "quant_score": 60,
                    },
                },
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )
    value = result(
        [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "HOLD",
                "score": 50,
                "reason": "positive event",
                "news_event_score": 90,
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(context=ctx, result=value)

    assert value.decisions[0].score == 66
    assert value.decisions[0].action == "BUY"
    assert value.decisions[0].market_sector_score == 50
    assert value.decisions[0].fundamental_score == 50
