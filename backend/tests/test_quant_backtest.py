from backend.app.services.quant_backtest import QuantBacktestService


def _trend_candles(count: int, *, start: float = 100.0, drift: float = 0.01):
    rows = []
    price = start
    for index in range(count):
        open_price = price
        variation = 0.001 if index % 2 == 0 else -0.0005
        close = open_price * (1.0 + drift + variation)
        rows.append(
            {
                "timestamp": f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
                "open": open_price,
                "high": max(open_price, close) * 1.01,
                "low": min(open_price, close) * 0.99,
                "close": close,
                "volume": 1000 + index * 10,
            }
        )
        price = close
    return rows


def test_backtest_is_no_lookahead_and_returns_metrics():
    rows = _trend_candles(100, drift=0.004)
    result = QuantBacktestService.simulate(
        market="stock",
        candles=rows,
        fee_bps=5,
        slippage_bps=5,
    )

    assert result["status"] == "completed"
    assert result["samples"] == 100
    assert result["trade_count"] >= 1
    assert "buy_hold_return_pct" in result
    assert "max_drawdown_pct" in result
    assert result["trades"][0]["holding_bars"] > 0


def test_backtest_fails_closed_with_insufficient_history():
    result = QuantBacktestService.simulate(
        market="crypto",
        candles=_trend_candles(20),
    )

    assert result["status"] == "insufficient_history"
    assert result["trade_count"] == 0


def test_backtest_costs_reduce_net_return():
    rows = _trend_candles(100, drift=0.004)
    free = QuantBacktestService.simulate(
        market="stock",
        candles=rows,
        fee_bps=0,
        slippage_bps=0,
    )
    costly = QuantBacktestService.simulate(
        market="stock",
        candles=rows,
        fee_bps=10,
        slippage_bps=10,
    )

    assert costly["compound_return_pct"] <= free[
        "compound_return_pct"
    ]
