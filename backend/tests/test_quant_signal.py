from backend.app.services.quant_signal import QuantSignalService


def test_stock_positive_medium_momentum_can_create_buy_prior():
    features = {
        "features_available": 1,
        "return_short_pct": 4.0,
        "return_medium_pct": 12.0,
        "return_long_pct": 28.0,
        "positive_day_ratio_medium": 65.0,
        "positive_day_ratio_long": 63.0,
        "sma_short_gap_pct": 3.0,
        "sma_long_gap_pct": 8.0,
        "realized_volatility_pct": 1.6,
        "volume_recent_ratio": 1.4,
    }

    result = QuantSignalService.enrich(
        market="stock",
        features=features,
    )

    assert result["quant_model_version"] == "v0.4.1"
    assert result["quant_score"] >= 65
    assert result["quant_action"] == "BUY"
    assert 0.35 <= result["quant_risk_scale"] <= 1.0


def test_crypto_missing_features_is_neutral_hold():
    result = QuantSignalService.enrich(
        market="crypto",
        features={"features_available": 0},
    )

    assert result["quant_score"] == 50.0
    assert result["quant_action"] == "HOLD"
    assert result["quant_risk_scale"] == 0.5


def test_high_volatility_only_reduces_exposure():
    features = {
        "features_available": 1,
        "return_short_pct": 10.0,
        "return_medium_pct": 20.0,
        "return_long_pct": 30.0,
        "sma_short_gap_pct": 4.0,
        "sma_long_gap_pct": 8.0,
        "realized_volatility_pct": 10.0,
        "volume_recent_ratio": 1.0,
    }

    result = QuantSignalService.enrich(
        market="crypto",
        features=features,
    )

    assert result["quant_risk_scale"] < 1.0
    assert result["quant_risk_scale"] >= 0.35



def test_momentum_score_no_longer_hits_100_at_z_two():
    score = QuantSignalService._momentum_score(
        return_pct=20.0,
        daily_vol_pct=5.0,
        horizon=4,
    )

    # z == 2.0 used to saturate at 100. The smoothed curve keeps
    # headroom so 90+ remains an unusually strong signal.
    assert 85 < score < 90
