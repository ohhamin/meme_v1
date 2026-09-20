from backend.app.services.technical_features import TechnicalFeatureService


def candles(count: int, *, start: float = 100.0, step: float = 1.0):
    result = []
    for index in range(count):
        close = start + (step * index)
        result.append(
            {
                "timestamp": f"2026-09-19T{index:02d}:00:00",
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 100 + index,
            }
        )
    return result


def test_technical_features_compute_returns_and_sma_gaps():
    raw = candles(25)
    result = TechnicalFeatureService.compute(
        candles=raw,
        current_price=124.0,
        short_period=1,
        medium_period=6,
        long_period=24,
        interval_label="60m",
    )

    assert result["features_available"] == 1
    assert result["feature_interval"] == "60m"
    assert result["feature_samples"] == 25
    assert result["return_short_pct"] == round((124 / 123 - 1) * 100, 4)
    assert result["return_medium_pct"] == round((124 / 118 - 1) * 100, 4)
    assert result["return_long_pct"] == 24.0
    assert result["positive_day_ratio_short"] == 100.0
    assert result["positive_day_ratio_medium"] == 100.0
    assert result["positive_day_ratio_long"] == 100.0
    assert result["realized_volatility_pct"] >= 0
    assert result["range_long_pct"] is not None
    assert result["volume_recent_ratio"] is not None


def test_technical_features_are_order_independent():
    raw = candles(25)
    forward = TechnicalFeatureService.compute(
        candles=raw,
        current_price=124.0,
        short_period=1,
        medium_period=6,
        long_period=24,
        interval_label="60m",
    )
    backward = TechnicalFeatureService.compute(
        candles=list(reversed(raw)),
        current_price=124.0,
        short_period=1,
        medium_period=6,
        long_period=24,
        interval_label="60m",
    )

    assert forward == backward


def test_technical_features_fail_closed_when_history_is_insufficient():
    result = TechnicalFeatureService.compute(
        candles=[
            {
                "timestamp": "2026-09-19T00:00:00",
                "close": 100,
                "high": 101,
                "low": 99,
                "volume": 100,
            }
        ],
        current_price=100.0,
        short_period=1,
        medium_period=6,
        long_period=24,
        interval_label="60m",
    )

    assert result["features_available"] == 0
    assert result["feature_samples"] == 1
