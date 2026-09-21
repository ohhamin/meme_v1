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
                "market_regime_score": 80,
                "sector_relative_strength_score": 80,
                "macro_score": 80,
                "market_sector_confidence": 100,
                "market_sector_age_hours": 0,
                "earnings_revision_score": 80,
                "quality_score": 80,
                "valuation_score": 80,
                "balance_shareholder_score": 80,
                "fundamental_confidence": 100,
                "fundamental_age_hours": 0,
                "news_event_score": 80,
                "news_event_confidence": 100,
                "news_event_age_hours": 0,
                "news_event_horizon_hours": 24,
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
                "news_event_confidence": 100,
                "news_event_age_hours": 0,
                "news_event_horizon_hours": 24,
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(context=ctx, result=value)

    assert value.decisions[0].score == 66
    assert value.decisions[0].action == "BUY"
    assert value.decisions[0].market_sector_score == 50
    assert value.decisions[0].fundamental_score == 50



def test_context_score_is_shrunk_to_neutral_by_low_confidence():
    assert LLMDecisionClient._evidence_adjusted_score(
        raw_score=90,
        confidence=0,
        age_hours=0,
        half_life_hours=24,
    ) == 50


def test_news_score_half_life_moves_halfway_toward_neutral():
    assert LLMDecisionClient._evidence_adjusted_score(
        raw_score=90,
        confidence=100,
        age_hours=24,
        half_life_hours=24,
    ) == 70


def test_stock_subfactors_are_combined_deterministically():
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
                    "features": {"quant_score": 50},
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
                "action": "HOLD",
                "score": 50,
                "reason": "structured evidence",
                "market_regime_score": 70,
                "sector_relative_strength_score": 90,
                "macro_score": 50,
                "market_sector_confidence": 100,
                "market_sector_age_hours": 0,
                "earnings_revision_score": 100,
                "quality_score": 80,
                "valuation_score": 60,
                "balance_shareholder_score": 40,
                "fundamental_confidence": 100,
                "fundamental_age_hours": 0,
                "news_event_score": 50,
                "news_event_confidence": 0,
                "news_event_age_hours": None,
                "news_event_horizon_hours": None,
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(context=ctx, result=value)

    assert value.decisions[0].market_sector_score == 75
    assert value.decisions[0].fundamental_score == 77
    assert value.decisions[0].news_event_score == 50
    assert value.decisions[0].score == 63
    assert value.decisions[0].action == "HOLD"
