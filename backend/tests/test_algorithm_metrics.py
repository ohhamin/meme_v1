from types import SimpleNamespace

from backend.app.services.algorithm_metrics import AlgorithmMetricsService


def test_algorithm_metrics_summarizes_decisions_and_churn(monkeypatch):
    service = AlgorithmMetricsService()

    markdown = """# 2026-09-19 Decisions

## 10:00 Decision Cycle
- Execution Mode: PAPER

### BTC
- Action: BUY
- Score: 70
- Risk Guard: PASS

### ETH
- Action: HOLD
- Score: 50
- Risk Guard: NO_ORDER

## 11:00 Decision Cycle
- Execution Mode: PAPER

### BTC
- Action: SELL
- Score: 30
- Risk Guard: BLOCK
- Block Reason: Daily loss limit reached | stale data
"""

    monkeypatch.setattr(
        service.decisions,
        "available_dates",
        lambda limit=7: ["2026-09-19"],
    )
    monkeypatch.setattr(
        service.decisions,
        "read",
        lambda day: markdown,
    )
    monkeypatch.setattr(
        service,
        "_paper_summary",
        lambda market: {
            "equity": "1000000",
            "cash": "500000",
            "daily_pnl_pct": "0",
            "daily_order_count": 0,
            "position_count": 1,
        },
    )
    monkeypatch.setattr(
        service.paper_orders,
        "recent",
        lambda limit=1000, days=30: [
            {
                "market": "stock",
                "side": "sell",
                "entry_score": "65",
                "candidate_score": "82",
                "realized_pnl": "-1000",
                "realized_return_pct": "-1.5",
            },
            {
                "side": "sell",
                "entry_score": "75",
                "realized_pnl": "2000",
                "realized_return_pct": "2.0",
            },
        ],
    )
    monkeypatch.setattr(
        service.live_orders,
        "list_records",
        lambda limit=500: [
            SimpleNamespace(status="CONFIRMED"),
            SimpleNamespace(status="UNKNOWN"),
        ],
    )
    monkeypatch.setattr(
        service.live_orders,
        "unresolved",
        lambda limit=500: [
            SimpleNamespace(status="UNKNOWN"),
        ],
    )

    result = service.build()

    assert result["decision_cycles"] == 2
    assert result["decision_count"] == 3
    assert result["actions"] == {
        "BUY": 1,
        "HOLD": 1,
        "SELL": 1,
    }
    assert result["risk_guard"]["BLOCK"] == 1
    assert result["direction_reversals"][0]["count"] == 1
    assert result["top_block_reasons"][0]["count"] == 1
    assert result["live_order_journal"]["unresolved"] == 1


    assert result["score_performance_30d"]["total_closed_trades"] == 2
    assert (
        result["score_performance_30d"]["buckets"]["60-69"]["closed_trades"]
        == 1
    )
    assert (
        result["score_performance_30d"]["buckets"]["70-79"]["win_rate_pct"]
        == 100.0
    )
    assert (
        result["score_performance_30d"]["buckets"]["60-69"]["sample_sufficient"]
        is False
    )
    assert result["score_performance_7d"]["window_days"] == 7
    assert (
        result["candidate_score_performance_7d"]["buckets"]["80-100"][
            "closed_trades"
        ]
        == 1
    )
