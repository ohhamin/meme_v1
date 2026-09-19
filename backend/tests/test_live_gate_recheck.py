import asyncio
from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app.models.schemas import (
    LiveOrderPreflightResult,
    RiskGuardResult,
)
from backend.app.services.live_order_service import LiveOrderService


def test_live_order_rechecks_safety_gates_after_preflight(
    tmp_path,
    monkeypatch,
):
    service = LiveOrderService()
    service.journal.base_dir = tmp_path / "live_orders"
    service.journal.base_dir.mkdir(parents=True, exist_ok=True)
    service.idempotency.path = tmp_path / "idempotency.json"

    monkeypatch.setattr(
        service.journal,
        "has_unresolved",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        service.risk,
        "evaluate",
        lambda intent: RiskGuardResult(
            status="PASS",
            symbol=intent.symbol,
            action=intent.action,
            reasons=[],
        ),
    )

    async def fake_preflight(**kwargs):
        return LiveOrderPreflightResult(
            allowed=True,
            broker="upbit",
            symbol=kwargs["symbol"],
            side=kwargs["side"],
            reasons=[],
        )

    submit_called = False

    async def fake_submit(**kwargs):
        nonlocal submit_called
        submit_called = True
        return {"uuid": "should-not-submit"}

    monkeypatch.setattr(
        service.upbit,
        "preflight",
        fake_preflight,
    )
    monkeypatch.setattr(
        service.upbit,
        "submit_market_order",
        fake_submit,
    )

    def changed_gate(_broker):
        raise HTTPException(
            status_code=423,
            detail="Kill switch is enabled.",
        )

    monkeypatch.setattr(
        service,
        "_require_live_manual",
        changed_gate,
    )

    snapshot = {
        "market": "crypto",
        "price": Decimal("100000000"),
        "portfolio_equity": Decimal("1000000"),
        "available_cash": Decimal("900000"),
        "position_value": Decimal("100000"),
        "position_quantity": Decimal("0.001"),
        "open_position_count": 1,
        "daily_pnl_pct": Decimal("0"),
        "daily_order_count": 0,
        "data_age_seconds": 1,
        "market_open": True,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service._execute(
                broker="upbit",
                source="manual",
                symbol="KRW-BTC",
                side="buy",
                quantity=Decimal("0.001"),
                notional=Decimal("100000"),
                snapshot=snapshot,
                idempotency_key="gate-recheck-test",
            )
        )

    assert exc.value.status_code == 423
    assert submit_called is False
    records = service.journal.list_records(limit=10)
    assert len(records) == 1
    assert records[0].status == "REJECTED"
    assert "Safety gates changed" in (records[0].reason or "")
