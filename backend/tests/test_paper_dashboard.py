from decimal import Decimal
from types import SimpleNamespace

import backend.app.services.paper_dashboard as dashboard_module
from backend.app.services.paper_dashboard import PaperDashboardService


def _portfolio(market, *, equity, cash, initial, day_start, daily_pnl, orders, positions):
    return SimpleNamespace(
        market=market,
        equity=Decimal(str(equity)),
        cash=Decimal(str(cash)),
        initial_cash=Decimal(str(initial)),
        day_start_equity=Decimal(str(day_start)),
        daily_pnl=Decimal(str(daily_pnl)),
        daily_pnl_pct=Decimal("0"),
        daily_order_count=orders,
        positions=positions,
    )


def _position(market, symbol, value, return_rate):
    return SimpleNamespace(
        market=market,
        symbol=symbol,
        name=symbol,
        quantity=Decimal("1"),
        average_price=Decimal("100"),
        last_price=Decimal("110"),
        invested_amount=Decimal("100"),
        market_value=Decimal(str(value)),
        return_rate=Decimal(str(return_rate)),
        realized_pnl=Decimal("0"),
        decision_score=70,
    )


def test_paper_dashboard_combines_accounts_and_drawdown(monkeypatch):
    portfolios = {
        "stock": _portfolio(
            "stock",
            equity=1050000,
            cash=900000,
            initial=1000000,
            day_start=1040000,
            daily_pnl=10000,
            orders=2,
            positions=[_position("stock", "005930", 150000, 5)],
        ),
        "crypto": _portfolio(
            "crypto",
            equity=980000,
            cash=880000,
            initial=1000000,
            day_start=1000000,
            daily_pnl=-20000,
            orders=3,
            positions=[_position("crypto", "KRW-BTC", 100000, -2)],
        ),
    }

    monkeypatch.setattr(
        dashboard_module,
        "PaperBroker",
        lambda market: SimpleNamespace(
            portfolio=lambda: portfolios[market]
        ),
    )

    service = PaperDashboardService()
    service.metrics.recent = lambda limit_days=7: [
        {
            "mode": "paper",
            "accounts": {
                "stock": {"equity": "1000000"},
                "crypto": {"equity": "1000000"},
            },
        },
        {
            "mode": "paper",
            "accounts": {
                "stock": {"equity": "950000"},
                "crypto": {"equity": "950000"},
            },
        },
    ]

    result = service.build()

    assert result["combined"]["equity"] == "2030000"
    assert result["combined"]["cash"] == "1780000"
    assert result["combined"]["invested"] == "250000"
    assert result["combined"]["cumulative_return_pct"] == "1.5000"
    assert result["combined"]["daily_order_count"] == 5
    assert result["combined"]["position_count"] == 2
    assert result["combined"]["max_drawdown_7d_pct"] == -5.0
    assert [item["symbol"] for item in result["positions"]] == [
        "005930",
        "KRW-BTC",
    ]
