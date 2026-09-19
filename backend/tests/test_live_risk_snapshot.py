import asyncio
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.live_risk_snapshot import LiveRiskSnapshotService


def test_pending_live_buys_count_as_open_positions(monkeypatch):
    service = LiveRiskSnapshotService()

    async def fake_upbit_balances():
        return SimpleNamespace(
            assets=[
                SimpleNamespace(
                    currency="KRW",
                    unit_currency="KRW",
                    total=Decimal("1000000"),
                ),
                SimpleNamespace(
                    currency="BTC",
                    unit_currency="KRW",
                    total=Decimal("0.001"),
                ),
            ]
        )

    async def fake_toss_status():
        return SimpleNamespace(
            holdings=[
                SimpleNamespace(
                    symbol="005930",
                    quantity=Decimal("1"),
                )
            ]
        )

    monkeypatch.setattr(
        service.upbit_accounts,
        "balances",
        fake_upbit_balances,
    )
    monkeypatch.setattr(
        service.toss_accounts,
        "status",
        fake_toss_status,
    )
    monkeypatch.setattr(
        service.journal,
        "unresolved",
        lambda limit=500: [
            SimpleNamespace(
                side="buy",
                market="crypto",
                symbol="KRW-ETH",
                broker="upbit",
                notional=Decimal("100000"),
            ),
            # Existing held stock should not be double-counted.
            SimpleNamespace(
                side="buy",
                market="stock",
                symbol="005930",
                broker="toss",
                notional=Decimal("70000"),
            ),
        ],
    )

    count = asyncio.run(service.total_open_positions())

    assert count == 3
