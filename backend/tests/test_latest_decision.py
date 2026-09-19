from backend.app.services.latest_decision import LatestDecisionService


def test_latest_decision_returns_last_cycle_only():
    markdown = """# 2026-09-19 Decisions

## 10:00 Decision Cycle

- Execution Mode: PAPER

### 비트코인 (KRW-BTC)
- Market: crypto
- Action: HOLD
- Score: 50
- Reason: old
- Risk Guard: NO_ORDER
- Next Check: 60m

> Cycle Summary: old summary

## 11:00 Decision Cycle

- Execution Mode: PAPER

### 삼성전자 (005930)
- Market: stock
- Action: BUY
- Score: 72
- Reason: breakout
- Risk Guard: PASS
- Order: BUY
- Order Quantity: 1
- Order Notional: 70000
- Next Check: 45m

### 비트코인 (KRW-BTC)
- Market: crypto
- Action: HOLD
- Score: 52
- Reason: mixed
- Risk Guard: NO_ORDER
- Next Check: 45m

> Cycle Summary: latest summary
"""

    service = LatestDecisionService()
    cycles = service._cycles(markdown)

    assert len(cycles) == 2
    latest = cycles[-1]
    assert latest["time"] == "11:00"
    assert latest["execution_mode"] == "PAPER"
    assert latest["cycle_summary"] == "latest summary"
    assert [item.symbol for item in latest["items"]] == ["005930", "KRW-BTC"]
    assert latest["items"][0].action == "BUY"
    assert latest["items"][0].order_notional == "70000"
