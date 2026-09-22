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
    assert value.decisions[0].score == 47
    assert "종합 47/100" in value.decisions[0].reason



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
    assert value.decisions[0].score == 65
    assert value.decisions[0].action == "BUY"
    assert "장세 BULL" in value.decisions[0].reason
    assert "목표투자 80%" in value.decisions[0].reason


def test_regime_policy_uses_raised_exposure_targets():
    bull = LLMDecisionClient._regime_exposure_policy(
        decision=result(
            [{
                "market": "crypto",
                "symbol": "KRW-BTC",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
                "market_regime_score": 80,
                "market_sector_confidence": 100,
                "market_sector_age_hours": 0,
            }]
        ).decisions[0],
        account_snapshot={"crypto": {"equity": "1000000", "cash": "420000"}},
    )
    neutral = LLMDecisionClient._regime_exposure_policy(
        decision=result(
            [{
                "market": "crypto",
                "symbol": "KRW-ETH",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
                "market_regime_score": 50,
                "market_sector_confidence": 100,
                "market_sector_age_hours": 0,
            }]
        ).decisions[0],
        account_snapshot={"crypto": {"equity": "1000000", "cash": "420000"}},
    )
    bear = LLMDecisionClient._regime_exposure_policy(
        decision=result(
            [{
                "market": "crypto",
                "symbol": "KRW-XRP",
                "action": "HOLD",
                "score": 50,
                "reason": "test",
                "market_regime_score": 20,
                "market_sector_confidence": 100,
                "market_sector_age_hours": 0,
            }]
        ).decisions[0],
        account_snapshot={"crypto": {"equity": "1000000", "cash": "420000"}},
    )

    assert bull["target_exposure_pct"] == 80
    assert neutral["target_exposure_pct"] == 60
    assert bear["target_exposure_pct"] == 35
    assert bull["buy_threshold"] < neutral["buy_threshold"] < bear["buy_threshold"]


def test_large_universe_uses_larger_output_budget(monkeypatch):
    client = LLMDecisionClient()

    class _FakeResponses:
        async def create(self, **kwargs):
            assert kwargs["max_output_tokens"] >= 12000
            class _Usage:
                input_tokens = 1
                output_tokens = 1
                total_tokens = 2
            class _Response:
                status = "completed"
                incomplete_details = None
                usage = _Usage()
                output_text = (
                    '{"decisions":['
                    + ",".join(
                        [
                            '{"market":"crypto","symbol":"KRW-X'
                            + str(i)
                            + '","name":"X","action":"HOLD","score":50,'
                            '"reason":"중립","technical_score":50,'
                            '"market_regime_score":50,'
                            '"sector_relative_strength_score":50,'
                            '"macro_score":50,'
                            '"market_sector_confidence":0,'
                            '"market_sector_age_hours":null,'
                            '"earnings_revision_score":50,'
                            '"quality_score":50,'
                            '"valuation_score":50,'
                            '"balance_shareholder_score":50,'
                            '"fundamental_confidence":0,'
                            '"fundamental_age_hours":null,'
                            '"news_event_score":50,'
                            '"news_event_confidence":0,'
                            '"news_event_age_hours":null,'
                            '"news_event_horizon_hours":null}'
                            for i in range(35)
                        ]
                    )
                    + '],"next_check_minutes":60,"cycle_summary":"중립"}'
                )
                _request_id = "test"
            return _Response()

    class _FakeClient:
        responses = _FakeResponses()

    client.client = _FakeClient()
    client.openai_usage.refresh = lambda: None

    async def _noop_refresh():
        return None

    client.openai_usage.refresh = _noop_refresh
    client.budget.record_usage = lambda **kwargs: None
    client.runtime.resume = lambda: None
    client.audit.write = lambda *args, **kwargs: None

    ctx = CompactDecisionContext(
        algorithm_markdown="test",
        news_context="",
        decision_context="",
        macro_context={},
        market_snapshot={
            "instruments": [
                {
                    "market": "crypto",
                    "symbol": f"KRW-X{i}",
                    "features": {"quant_score": 50},
                }
                for i in range(35)
            ]
        },
        account_snapshot={},
        estimated_input_tokens=100,
        budget_mode="normal",
    )

    import asyncio
    result_value = asyncio.run(client.decide(ctx))
    assert len(result_value.decisions) == 35



def test_stock_missing_context_does_not_drag_technical_score_to_50():
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
                    "features": {"quant_score": 72},
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
                "reason": "no verified context",
            }
        ]
    )

    LLMDecisionClient._apply_quant_guardrails(context=ctx, result=value)

    assert value.decisions[0].market_sector_confidence == 0
    assert value.decisions[0].fundamental_confidence == 0
    assert value.decisions[0].news_event_confidence == 0
    assert value.decisions[0].score == 72
    assert value.decisions[0].action == "BUY"
