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
