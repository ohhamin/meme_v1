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
        candidate_score=Decimal("82") if market == "stock" else None,
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
    service.orders.recent = lambda limit=500, days=30: [
        {
            "order_id": "paper-1",
            "market": "crypto",
            "symbol": "KRW-BTC",
            "side": "sell",
            "realized_pnl": "12000",
            "entry_score": "65",
            "realized_return_pct": "6.0",
            "decision_reason": "TRAILING_STOP: peak gain 12.00%, drawdown -5.20% <= -5.0%",
        },
        {
            "order_id": "paper-2",
            "market": "stock",
            "symbol": "005930",
            "side": "sell",
            "realized_pnl": "-4000",
            "entry_score": "75",
            "realized_return_pct": "-2.0",
            "candidate_score": "84",
            "decision_reason": "정량 SELL",
        },
        {
            "order_id": "paper-3",
            "market": "crypto",
            "symbol": "KRW-ETH",
            "side": "buy",
            "realized_pnl": None,
        },
    ]
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


    assert result["trading_30d"]["order_count"] == 3
    assert result["trading_30d"]["sell_count"] == 2
    assert result["trading_30d"]["win_count"] == 1
    assert result["trading_30d"]["loss_count"] == 1
    assert result["trading_30d"]["win_rate_pct"] == "50.00"
    assert result["trading_30d"]["realized_pnl"] == "8000"
    assert len(result["recent_orders"]) == 3

    stock_trading = result["trading_7d_by_market"]["stock"]
    crypto_trading = result["trading_7d_by_market"]["crypto"]
    assert stock_trading["sell_count"] == 1
    assert stock_trading["win_rate_pct"] == "0.00"
    assert stock_trading["realized_pnl"] == "-4000"
    assert crypto_trading["sell_count"] == 1
    assert crypto_trading["win_rate_pct"] == "100.00"
    assert crypto_trading["realized_pnl"] == "12000"

    stock_score = {
        item["bucket"]: item
        for item in result["score_performance_7d_by_market"]["stock"]
    }
    crypto_score = {
        item["bucket"]: item
        for item in result["score_performance_7d_by_market"]["crypto"]
    }
    assert stock_score["70-79"]["closed_trades"] == 1
    assert stock_score["70-79"]["positive_close_count"] == 0
    assert stock_score["70-79"]["negative_close_count"] == 1
    assert stock_score["70-79"]["average_return_pct"] == "-2.00"
    assert crypto_score["60-69"]["closed_trades"] == 1
    assert crypto_score["60-69"]["positive_close_count"] == 1
    assert crypto_score["60-69"]["negative_close_count"] == 0
    assert crypto_score["60-69"]["average_return_pct"] == "6.00"

    stock_exit = {
        item["key"]: item
        for item in result["exit_reason_performance_7d_by_market"]["stock"]
    }
    crypto_exit = {
        item["key"]: item
        for item in result["exit_reason_performance_7d_by_market"]["crypto"]
    }
    assert stock_exit["normal_sell"]["closed_trades"] == 1
    assert stock_exit["normal_sell"]["average_return_pct"] == "-2.00"
    assert stock_exit["hard_stop"]["closed_trades"] == 0
    assert crypto_exit["trailing_stop"]["closed_trades"] == 1
    assert crypto_exit["trailing_stop"]["average_return_pct"] == "6.00"


    score = {
        item["bucket"]: item
        for item in result["score_performance_30d"]
    }
    assert score["60-69"]["closed_trades"] == 1
    assert score["60-69"]["win_rate_pct"] == "100.00"
    assert score["60-69"]["average_return_pct"] == "6.00"
    assert score["70-79"]["closed_trades"] == 1
    assert score["70-79"]["win_rate_pct"] == "0.00"
    assert score["70-79"]["average_return_pct"] == "-2.00"
    assert score["80-100"]["closed_trades"] == 0

    candidate = {
        item["bucket"]: item
        for item in result["candidate_score_performance_7d"]
    }
    assert candidate["80-100"]["closed_trades"] == 1
    assert candidate["80-100"]["positive_close_count"] == 0
    assert candidate["80-100"]["negative_close_count"] == 1
    assert candidate["80-100"]["win_rate_pct"] == "0.00"
    assert candidate["80-100"]["average_return_pct"] == "-2.00"
    assert candidate["80-100"]["sample_sufficient"] is False
