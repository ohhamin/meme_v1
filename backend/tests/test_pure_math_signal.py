from backend.app.services.pure_math_signal import PureMathSignalService


def test_pure_math_stock_buy_requires_strong_positive_evidence():
    features = {
        "features_available": 1,
        "realized_volatility_pct": 1.5,
        "positive_day_ratio_long": 70.0,
        "positive_day_ratio_medium": 70.0,
        "return_medium_pct": 12.0,
    }

    result = PureMathSignalService.enrich(
        market="stock",
        features=features,
    )

    assert result["math_action"] == "BUY"
    assert result["math_score"] > 90
    assert result["math_z"] >= PureMathSignalService.Z_90


def test_pure_math_crypto_hold_when_evidence_is_mixed():
    features = {
        "features_available": 1,
        "realized_volatility_pct": 4.0,
        "return_short_pct": 8.0,
        "return_medium_pct": -2.0,
        "positive_day_ratio_medium": 52.0,
    }

    result = PureMathSignalService.enrich(
        market="crypto",
        features=features,
    )

    assert result["math_action"] == "HOLD"


def test_pure_math_missing_data_is_neutral():
    result = PureMathSignalService.enrich(
        market="stock",
        features={"features_available": 0},
    )

    assert result["math_action"] == "HOLD"
    assert result["math_score"] == 50.0
