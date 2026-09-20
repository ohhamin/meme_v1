from backend.app.services.inverse_volatility_allocator import (
    InverseVolatilityAllocator,
)


def test_inverse_volatility_weights_sum_to_one():
    result = InverseVolatilityAllocator.allocate(
        [
            {"symbol": "A", "realized_volatility_pct": 1.0},
            {"symbol": "B", "realized_volatility_pct": 2.0},
            {"symbol": "C", "realized_volatility_pct": 4.0},
        ],
        max_weight=0.8,
    )

    assert round(sum(item["weight"] for item in result), 8) == 1.0
    assert result[0]["weight"] > result[1]["weight"] > result[2]["weight"]


def test_inverse_volatility_cap_is_respected_when_feasible():
    result = InverseVolatilityAllocator.allocate(
        [
            {"symbol": "A", "realized_volatility_pct": 0.5},
            {"symbol": "B", "realized_volatility_pct": 2.0},
            {"symbol": "C", "realized_volatility_pct": 2.0},
            {"symbol": "D", "realized_volatility_pct": 2.0},
        ],
        max_weight=0.4,
    )

    assert max(item["weight"] for item in result) <= 0.40000001
    assert round(sum(item["weight"] for item in result), 8) == 1.0


def test_inverse_volatility_skips_invalid_volatility():
    result = InverseVolatilityAllocator.allocate(
        [
            {"symbol": "A", "realized_volatility_pct": 0},
            {"symbol": "B", "realized_volatility_pct": None},
            {"symbol": "C", "realized_volatility_pct": 3.0},
        ]
    )

    assert result == [
        {
            "symbol": "C",
            "volatility_pct": 3.0,
            "weight": 1.0,
            "risk_proxy": 3.0,
        }
    ]
