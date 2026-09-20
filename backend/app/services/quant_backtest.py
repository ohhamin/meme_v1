from __future__ import annotations

from math import prod
from statistics import fmean
from typing import Any

from backend.app.services.quant_signal import QuantSignalService
from backend.app.services.technical_features import TechnicalFeatureService


class QuantBacktestService:
    """No-lookahead validation of the deterministic quant core.

    A signal is calculated using data through day t and executed at day t+1
    open. This deliberately excludes the LLM veto layer and Position Sizer so
    the mathematical directional signal can be evaluated on its own.
    """

    @classmethod
    def simulate(
        cls,
        *,
        market: str,
        candles: list[dict[str, Any]],
        fee_bps: float = 5.0,
        slippage_bps: float = 5.0,
    ) -> dict[str, Any]:
        if market not in {"stock", "crypto"}:
            raise ValueError("market must be stock or crypto")

        ordered = sorted(
            candles,
            key=lambda item: str(item.get("timestamp") or ""),
        )
        cleaned = [
            item
            for item in ordered
            if cls._price(item, "open") > 0
            and cls._price(item, "close") > 0
        ]

        if market == "stock":
            short_period, medium_period, long_period = 5, 20, 60
            minimum = 62
        else:
            short_period, medium_period, long_period = 7, 21, 42
            minimum = 44

        if len(cleaned) < minimum:
            return {
                "status": "insufficient_history",
                "market": market,
                "samples": len(cleaned),
                "required_samples": minimum,
                "trade_count": 0,
            }

        fee = max(0.0, fee_bps) / 10000.0
        slippage = max(0.0, slippage_bps) / 10000.0

        position: dict[str, Any] | None = None
        trades: list[dict[str, Any]] = []

        # Signal at close t -> fill at open t+1, preventing same-bar lookahead.
        for index in range(long_period, len(cleaned) - 1):
            history = cleaned[: index + 1]
            close = cls._price(history[-1], "close")
            features = TechnicalFeatureService.compute(
                candles=history,
                current_price=close,
                short_period=short_period,
                medium_period=medium_period,
                long_period=long_period,
                interval_label="1d",
            )
            quant = QuantSignalService.enrich(
                market=market,
                features=features,
            )

            next_bar = cleaned[index + 1]
            next_open = cls._price(next_bar, "open")
            if next_open <= 0:
                continue

            action = str(quant.get("quant_action") or "HOLD")
            score = float(quant.get("quant_score") or 50)

            if position is None and action == "BUY":
                entry_price = next_open * (1.0 + slippage)
                position = {
                    "entry_index": index + 1,
                    "entry_time": str(next_bar.get("timestamp") or ""),
                    "entry_price": entry_price,
                    "entry_score": score,
                }
                continue

            if position is not None and action == "SELL":
                exit_price = next_open * (1.0 - slippage)
                trades.append(
                    cls._trade(
                        position=position,
                        exit_index=index + 1,
                        exit_time=str(next_bar.get("timestamp") or ""),
                        exit_price=exit_price,
                        exit_score=score,
                        fee=fee,
                    )
                )
                position = None

        # Mark an open trade to the final close so validation never silently
        # drops unresolved exposure.
        if position is not None:
            final_bar = cleaned[-1]
            exit_price = cls._price(final_bar, "close") * (1.0 - slippage)
            trades.append(
                cls._trade(
                    position=position,
                    exit_index=len(cleaned) - 1,
                    exit_time=str(final_bar.get("timestamp") or ""),
                    exit_price=exit_price,
                    exit_score=None,
                    fee=fee,
                    forced_exit=True,
                )
            )

        returns = [float(item["net_return_pct"]) / 100.0 for item in trades]
        max_drawdown = cls._max_mark_to_market_drawdown(
            candles=cleaned,
            trades=trades,
            fee=fee,
            slippage=slippage,
        )

        first_test_open = cls._price(cleaned[long_period + 1], "open")
        final_close = cls._price(cleaned[-1], "close")
        benchmark = (
            (final_close * (1.0 - slippage) * (1.0 - fee))
            / (first_test_open * (1.0 + slippage) * (1.0 + fee))
            - 1.0
            if first_test_open > 0
            else 0.0
        )

        return {
            "status": "completed",
            "market": market,
            "samples": len(cleaned),
            "signal_start": str(
                cleaned[long_period].get("timestamp") or ""
            ),
            "signal_end": str(cleaned[-1].get("timestamp") or ""),
            "fee_bps_each_side": round(fee_bps, 4),
            "slippage_bps_each_side": round(slippage_bps, 4),
            "trade_count": len(trades),
            "win_rate_pct": round(
                (
                    sum(1 for value in returns if value > 0)
                    / len(returns)
                    * 100
                )
                if returns
                else 0.0,
                4,
            ),
            "average_trade_return_pct": round(
                fmean(returns) * 100 if returns else 0.0,
                4,
            ),
            "compound_return_pct": round(
                (prod(1.0 + value for value in returns) - 1.0) * 100
                if returns
                else 0.0,
                4,
            ),
            "max_drawdown_pct": round(
                max_drawdown * 100,
                4,
            ),
            "average_holding_days": round(
                fmean(
                    float(item["holding_bars"])
                    for item in trades
                )
                if trades
                else 0.0,
                2,
            ),
            "buy_hold_return_pct": round(benchmark * 100, 4),
            "trades": [
                cls._public_trade(trade)
                for trade in trades
            ],
        }

    @staticmethod
    def _trade(
        *,
        position: dict[str, Any],
        exit_index: int,
        exit_time: str,
        exit_price: float,
        exit_score: float | None,
        fee: float,
        forced_exit: bool = False,
    ) -> dict[str, Any]:
        entry_price = float(position["entry_price"])
        gross = exit_price / entry_price - 1.0
        net_multiple = (
            exit_price * (1.0 - fee)
        ) / (
            entry_price * (1.0 + fee)
        )
        net = net_multiple - 1.0

        return {
            "entry_time": position["entry_time"],
            "exit_time": exit_time,
            "entry_score": round(float(position["entry_score"]), 2),
            "exit_score": (
                round(float(exit_score), 2)
                if exit_score is not None
                else None
            ),
            "gross_return_pct": round(gross * 100, 4),
            "net_return_pct": round(net * 100, 4),
            "holding_bars": max(
                0,
                exit_index - int(position["entry_index"]),
            ),
            "forced_exit": forced_exit,
            "_entry_index": int(position["entry_index"]),
            "_exit_index": exit_index,
            "_entry_price": entry_price,
        }

    @staticmethod
    def _max_mark_to_market_drawdown(
        *,
        candles: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        fee: float,
        slippage: float,
    ) -> float:
        wealth = 1.0
        peak = 1.0
        max_drawdown = 0.0

        for trade in trades:
            entry_index = int(trade["_entry_index"])
            exit_index = int(trade["_exit_index"])
            entry_price = float(trade["_entry_price"])
            entry_cost = entry_price * (1.0 + fee)

            for index in range(entry_index, exit_index + 1):
                close = QuantBacktestService._price(
                    candles[index],
                    "close",
                )
                liquidation = (
                    close
                    * (1.0 - slippage)
                    * (1.0 - fee)
                )
                marked = (
                    wealth * liquidation / entry_cost
                    if entry_cost > 0
                    else wealth
                )
                peak = max(peak, marked)
                if peak > 0:
                    max_drawdown = min(
                        max_drawdown,
                        marked / peak - 1.0,
                    )

            wealth *= 1.0 + (
                float(trade["net_return_pct"]) / 100.0
            )
            peak = max(peak, wealth)

        return max_drawdown

    @staticmethod
    def _public_trade(trade: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in trade.items()
            if not key.startswith("_")
        }

    @staticmethod
    def _price(item: dict[str, Any], key: str) -> float:
        try:
            return float(item.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0
