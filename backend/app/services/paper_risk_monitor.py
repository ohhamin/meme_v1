from decimal import Decimal

from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.models.schemas import RiskOrderIntent
from backend.app.services.audit import AuditLogger
from backend.app.services.auto_trade_activity import AutoTradeActivityService
from backend.app.services.decision_store import DecisionMarkdownStore
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.runtime_settings import RuntimeSettingsService


class PaperRiskMonitor:
    """Fast deterministic protection loop for Paper positions.

    This service does not call the LLM and does not create BUY orders.
    It only refreshes prices for held positions and can fully exit a position
    when a configured hard-stop or activated trailing-stop is breached.
    """

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.config = self.runtime.config
        self.risk = RiskGuard()
        self.brokers = {
            "stock": PaperBroker("stock"),
            "crypto": PaperBroker("crypto"),
        }
        self.upbit = UpbitMarketDataAdapter()
        self.toss = TossMarketDataAdapter()
        self.activity = AutoTradeActivityService()
        self.audit = AuditLogger()
        self.store = DecisionMarkdownStore()

    async def run(self) -> dict:
        runtime = self.runtime.get()
        if runtime.mode != "paper":
            return {"status": "skipped", "reason": "Paper mode is not active."}
        if runtime.kill_switch:
            return {"status": "skipped", "reason": "Trading kill switch is enabled."}

        exits: list[dict] = []
        failures: list[str] = []

        for market in ("crypto", "stock"):
            broker = self.brokers[market]
            portfolio = broker.portfolio()
            symbols = [p.symbol for p in portfolio.positions]
            if not symbols:
                continue

            try:
                if market == "crypto":
                    snapshots = await self.upbit.snapshots(
                        symbols,
                        with_features=False,
                    )
                else:
                    if not self.toss.configured:
                        failures.append(
                            "Toss credentials are not configured for risk monitor."
                        )
                        continue
                    snapshots = await self.toss.snapshots(
                        symbols,
                        with_features=False,
                    )
            except Exception as exc:
                failures.append(f"{market}: {exc}")
                continue

            by_symbol = {item.symbol: item for item in snapshots}
            broker.update_prices(snapshots)

            for symbol in symbols:
                instrument = by_symbol.get(symbol)
                position = broker.position(symbol)
                if instrument is None or position is None:
                    continue
                exit_reason = self._exit_reason(position)
                if exit_reason is None:
                    continue

                fresh_portfolio = broker.portfolio()
                intent = RiskOrderIntent(
                    source="auto",
                    market=market,
                    symbol=symbol,
                    action="SELL",
                    order_notional=position.quantity * instrument.price,
                    order_quantity=position.quantity,
                    price=instrument.price,
                    portfolio_equity=fresh_portfolio.equity,
                    available_cash=fresh_portfolio.cash,
                    position_value=position.market_value,
                    position_quantity=position.quantity,
                    open_position_count=sum(
                        len(item.portfolio().positions)
                        for item in self.brokers.values()
                    ),
                    daily_pnl_pct=fresh_portfolio.daily_pnl_pct,
                    daily_order_count=fresh_portfolio.daily_order_count,
                    daily_buy_order_count=(
                        fresh_portfolio.daily_buy_order_count
                    ),
                    data_age_seconds=instrument.data_age_seconds,
                    market_open=instrument.market_open,
                    same_cycle_duplicate=False,
                )
                safety = self.risk.evaluate(intent)
                if safety.status != "ALLOW":
                    failures.append(
                        f"{market}:{symbol}: exit blocked by system safety: "
                        + " | ".join(safety.reasons)
                    )
                    continue

                order = broker.execute(
                    symbol=symbol,
                    name=position.name,
                    side="sell",
                    quantity=position.quantity,
                    market_price=instrument.price,
                    decision_score=position.decision_score,
                    decision_reason=exit_reason,
                    source="risk_monitor",
                    market_open=instrument.market_open,
                )
                self.activity.record(
                    mode="paper",
                    market=market,
                    symbol=symbol,
                    side="sell",
                    at=order.created_at,
                )
                self.activity.record(
                    mode="paper",
                    market=market,
                    symbol=symbol,
                    event="stop_exit",
                    at=order.created_at,
                )

                payload = {
                    "market": market,
                    "symbol": symbol,
                    "reason": exit_reason,
                    "quantity": str(order.quantity),
                    "price": str(order.price),
                    "order_id": order.order_id,
                }
                exits.append(payload)
                try:
                    self.store.append_risk_exit(
                        market=market,
                        symbol=symbol,
                        name=position.name,
                        score=position.decision_score,
                        reason=exit_reason,
                        quantity=order.quantity,
                        price=order.price,
                        notional=order.notional,
                        order_id=order.order_id,
                        created_at=order.created_at,
                    )
                except Exception as exc:
                    failures.append(
                        f"{market}:{symbol}: risk exit decision log failed: {exc}"
                    )

                self.audit.write(
                    "system",
                    {
                        "event": "risk_guard_force_exit",
                        "mode": "paper",
                        "risk_status": "FORCE_EXIT",
                        **payload,
                    },
                )

        result = {
            "status": "completed",
            "force_exit_count": len(exits),
            "exits": exits,
            "failures": failures,
        }
        self.audit.write(
            "system",
            {
                "event": "paper_risk_monitor_completed",
                "force_exit_count": len(exits),
                "failure_count": len(failures),
            },
        )
        return result

    def _exit_reason(self, position) -> str | None:
        if position.average_price <= 0 or position.last_price <= 0:
            return None

        pnl_pct = (
            (position.last_price - position.average_price)
            / position.average_price
            * Decimal("100")
        )
        hard_stop = Decimal(str(self.config.risk_hard_stop_loss_pct))
        if pnl_pct <= -hard_stop:
            return (
                f"HARD_STOP: return {pnl_pct:.2f}% <= -{hard_stop}%"
            )

        peak = max(
            position.highest_price_since_entry,
            position.last_price,
        )
        peak_gain_pct = (
            (peak - position.average_price)
            / position.average_price
            * Decimal("100")
        )
        activation = Decimal(
            str(self.config.risk_trailing_activation_pct)
        )
        if peak_gain_pct < activation or peak <= 0:
            return None

        drawdown_from_peak = (
            (position.last_price - peak)
            / peak
            * Decimal("100")
        )
        trailing_stop = Decimal(str(self.config.risk_trailing_stop_pct))
        if drawdown_from_peak <= -trailing_stop:
            return (
                "TRAILING_STOP: "
                f"peak gain {peak_gain_pct:.2f}%, "
                f"drawdown {drawdown_from_peak:.2f}% <= -{trailing_stop}%"
            )
        return None
