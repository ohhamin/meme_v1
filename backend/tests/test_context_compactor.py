from backend.app.services.context_compactor import CompactContextBuilder


def test_market_snapshot_keeps_only_compact_quant_summary():
    snapshot = {
        "instruments": [
            {
                "market": "crypto",
                "symbol": "KRW-BTC",
                "name": "비트코인",
                "price": "100000000",
                "data_age_seconds": 2,
                "market_open": True,
                "features": {
                    "features_available": 1,
                    "feature_interval": "1d",
                    "feature_samples": 64,
                    "quant_model_version": "v0.4",
                    "quant_score": 72.5,
                    "quant_action": "BUY",
                    "quant_risk_scale": 0.8,
                    "quant_penalty": 1.2,
                    "quant_components": "21일 모멘텀 70 · 추세 68",
                    "return_short_pct": 8.1,
                    "return_medium_pct": 15.2,
                    "sma_long_gap_pct": 4.3,
                    "realized_volatility_pct": 3.2,
                    "range_long_pct": 30.0,
                    "volume_recent_ratio": 1.4,
                },
            }
        ]
    }

    compact = CompactContextBuilder._compact_market_snapshot(snapshot)
    item = compact["instruments"][0]

    assert item["symbol"] == "KRW-BTC"
    assert item["price"] == "100000000"
    assert item["features"]["quant_score"] == 72.5
    assert item["features"]["quant_components"].startswith("21일")
    assert "return_short_pct" not in item["features"]
    assert "sma_long_gap_pct" not in item["features"]
    assert "realized_volatility_pct" not in item["features"]


def test_account_snapshot_keeps_holdings_but_drops_execution_only_fields():
    snapshot = {
        "crypto": {
            "broker": "paper",
            "cash": "400000",
            "equity": "1000000",
            "daily_pnl_pct": "1.2",
            "daily_order_count": 3,
            "positions": [
                {
                    "symbol": "KRW-BTC",
                    "name": "비트코인",
                    "quantity": "0.001",
                    "average_price": "90000000",
                    "last_price": "100000000",
                    "market_value": "100000",
                    "return_rate": "11.11",
                    "decision_score": 70,
                    "realized_pnl": "1234",
                    "highest_price_since_entry": "102000000",
                }
            ],
        },
        "portfolio_policy": {"accounts_are_separate": True},
    }

    compact = CompactContextBuilder._compact_account_snapshot(snapshot)
    position = compact["crypto"]["positions"][0]

    assert position["symbol"] == "KRW-BTC"
    assert position["average_price"] == "90000000"
    assert position["return_rate"] == "11.11"
    assert "quantity" not in position
    assert "last_price" not in position
    assert "realized_pnl" not in position
    assert compact["portfolio_policy"]["accounts_are_separate"] is True


def test_compaction_reduces_prompt_payload_size_materially():
    raw_features = {
        "features_available": 1,
        "feature_interval": "1d",
        "feature_samples": 64,
        "quant_model_version": "v0.4",
        "quant_score": 70,
        "quant_action": "BUY",
        "quant_risk_scale": 0.9,
        "quant_penalty": 0,
        "quant_components": "모멘텀 70 · 추세 65",
        "return_short_pct": 1.1,
        "return_medium_pct": 2.2,
        "return_long_pct": 3.3,
        "positive_day_ratio_short": 55,
        "positive_day_ratio_medium": 60,
        "positive_day_ratio_long": 65,
        "sma_short_gap_pct": 1.2,
        "sma_medium_gap_pct": 2.3,
        "sma_long_gap_pct": 3.4,
        "realized_volatility_pct": 4.5,
        "range_long_pct": 20,
        "volume_recent_ratio": 1.5,
    }
    raw = {
        "instruments": [
            {
                "market": "crypto",
                "symbol": f"KRW-X{i}",
                "name": f"코인{i}",
                "price": 1000 + i,
                "data_age_seconds": 1,
                "market_open": True,
                "features": dict(raw_features),
            }
            for i in range(45)
        ]
    }

    compact = CompactContextBuilder._compact_market_snapshot(raw)

    assert len(str(compact)) < len(str(raw)) * 0.75
