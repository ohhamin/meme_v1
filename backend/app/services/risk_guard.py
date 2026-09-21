from decimal import Decimal, ROUND_DOWN

from backend.app.core.config import get_settings
from backend.app.models.schemas import RiskGuardResult, RiskOrderIntent
from backend.app.services.audit import AuditLogger
from backend.app.services.runtime_settings import RuntimeSettingsService


class RiskGuard:
    """Deterministic account-protection and exposure-control engine.

    BUY is treated as exposure-increasing and is checked strictly.
    SELL that does not exceed the current holding is exposure-reducing and
    bypasses BUY-only limits such as cooldown, daily order count, cash reserve,
    position concentration, and daily loss lockout.

    Risk Guard never chooses a symbol or market direction. It may, however,
    reduce a BUY size so the order stays inside deterministic hard limits.
    """

    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()
        self.audit = AuditLogger()

    def policy(self) -> dict:
        return {
            "version": "0.5",
            "max_position_pct": self.config.risk_max_position_pct,
            "max_daily_loss_pct": self.config.risk_max_daily_loss_pct,
            "max_daily_orders": self.config.risk_max_daily_orders,
            "max_data_age_seconds": self.config.risk_max_data_age_seconds,
            "min_cash_reserve_pct": self.config.risk_min_cash_reserve_pct,
            "max_open_positions": self.config.risk_max_open_positions,
            "buy_cooldown_minutes": self.config.risk_auto_symbol_cooldown_minutes,
            "sell_reentry_cooldown_minutes": (
                self.config.risk_sell_reentry_cooldown_minutes
            ),
            "stop_reentry_cooldown_minutes": (
                self.config.risk_stop_reentry_cooldown_minutes
            ),
            "hard_stop_loss_pct": self.config.risk_hard_stop_loss_pct,
            "trailing_activation_pct": (
                self.config.risk_trailing_activation_pct
            ),
            "trailing_stop_pct": self.config.risk_trailing_stop_pct,
            "risk_monitor_interval_minutes": (
                self.config.risk_monitor_interval_minutes
            ),
            "buy_kill_switch": self.config.risk_buy_kill_switch,
            "minimum_open_positions": 0,
            "sell_is_risk_reducing": True,
            "resizes_buy_orders": True,
            "result_states": [
                "ALLOW",
                "REDUCE",
                "BLOCK",
                "FORCE_EXIT",
                "NO_ORDER",
            ],
        }

    def evaluate(self, intent: RiskOrderIntent) -> RiskGuardResult:
        if intent.action == "HOLD":
            return self._result(
                intent,
                status="NO_ORDER",
                reasons=["HOLD decision does not create an order."],
                triggered_rule="HOLD",
            )

        runtime = self.runtime.get()
        reasons: list[str] = []

        # System-safety rules apply to both BUY and SELL.
        if runtime.kill_switch:
            reasons.append("Trading kill switch is enabled.")
        if intent.same_cycle_duplicate:
            reasons.append("Duplicate order for the same symbol in this cycle.")
        if intent.data_age_seconds > self.config.risk_max_data_age_seconds:
            reasons.append(
                "Market/account snapshot is stale "
                f"({intent.data_age_seconds}s > "
                f"{self.config.risk_max_data_age_seconds}s)."
            )
        if intent.market == "stock" and not intent.market_open:
            reasons.append("Stock market is closed.")
        if intent.price <= 0:
            reasons.append("Price must be positive.")
        if intent.order_notional <= 0:
            reasons.append("Order notional must be positive.")
        if intent.order_quantity <= 0:
            reasons.append("Order quantity must be positive.")

        if reasons:
            return self._result(
                intent,
                status="BLOCK",
                reasons=reasons,
                triggered_rule="SYSTEM_SAFETY",
            )

        # Exposure-reducing SELL must remain available during BUY lockouts.
        if intent.action == "SELL":
            if intent.order_quantity > intent.position_quantity:
                return self._result(
                    intent,
                    status="BLOCK",
                    reasons=[
                        "Sell quantity exceeds current position quantity."
                    ],
                    triggered_rule="SELL_EXCEEDS_POSITION",
                )
            return self._result(
                intent,
                status="ALLOW",
                reasons=[],
                triggered_rule="RISK_REDUCING_SELL",
            )

        # BUY-only emergency/portfolio lockouts.
        if self.config.risk_buy_kill_switch:
            reasons.append("BUY kill switch is enabled.")

        if intent.daily_pnl_pct <= Decimal(
            str(-self.config.risk_max_daily_loss_pct)
        ):
            reasons.append(
                "Daily equity loss limit reached "
                f"({intent.daily_pnl_pct}% <= "
                f"-{self.config.risk_max_daily_loss_pct}%)."
            )

        buy_order_count = (
            intent.daily_buy_order_count
            if intent.daily_buy_order_count is not None
            else intent.daily_order_count
        )
        if buy_order_count >= self.config.risk_max_daily_orders:
            reasons.append(
                "Daily exposure-increasing order count limit reached "
                f"({buy_order_count} >= "
                f"{self.config.risk_max_daily_orders})."
            )

        if (
            intent.position_quantity <= 0
            and intent.open_position_count
            >= self.config.risk_max_open_positions
        ):
            reasons.append(
                "Maximum open position count reached "
                f"({intent.open_position_count} >= "
                f"{self.config.risk_max_open_positions})."
            )

        cooldown_reason = self._buy_cooldown_reason(intent)
        if cooldown_reason:
            reasons.append(cooldown_reason)

        if reasons:
            return self._result(
                intent,
                status="BLOCK",
                reasons=reasons,
                triggered_rule="BUY_LOCKOUT",
            )

        # BUY sizing can be reduced to the maximum deterministic safe capacity.
        equity = intent.portfolio_equity
        max_position_value = equity * (
            Decimal(str(self.config.risk_max_position_pct))
            / Decimal("100")
        )
        max_by_position = max(
            Decimal("0"),
            max_position_value - intent.position_value,
        )

        reserve_required = equity * (
            Decimal(str(self.config.risk_min_cash_reserve_pct))
            / Decimal("100")
        )
        max_by_cash = max(
            Decimal("0"),
            intent.available_cash - reserve_required,
        )

        safe_notional = min(
            intent.order_notional,
            max_by_position,
            max_by_cash,
        )

        if safe_notional <= 0:
            detail = []
            if max_by_position <= 0:
                detail.append(
                    "Position is already at the configured concentration limit."
                )
            if max_by_cash <= 0:
                detail.append(
                    "No cash is available above the configured reserve."
                )
            return self._result(
                intent,
                status="BLOCK",
                reasons=detail or ["No safe BUY capacity remains."],
                triggered_rule="NO_BUY_CAPACITY",
            )

        adjusted_quantity = self._quantity_for_notional(
            market=intent.market,
            notional=safe_notional,
            price=intent.price,
        )
        adjusted_notional = adjusted_quantity * intent.price

        if adjusted_quantity <= 0 or adjusted_notional <= 0:
            return self._result(
                intent,
                status="BLOCK",
                reasons=[
                    "Safe BUY capacity is below the minimum tradable quantity."
                ],
                triggered_rule="MIN_TRADABLE_QUANTITY",
            )

        if adjusted_notional < intent.order_notional:
            return self._result(
                intent,
                status="REDUCE",
                reasons=[
                    "BUY size reduced to remain inside position and cash "
                    "reserve limits."
                ],
                adjusted_notional=adjusted_notional,
                adjusted_quantity=adjusted_quantity,
                triggered_rule="EXPOSURE_CAP",
            )

        return self._result(
            intent,
            status="ALLOW",
            reasons=[],
            adjusted_notional=intent.order_notional,
            adjusted_quantity=intent.order_quantity,
            triggered_rule="WITHIN_LIMITS",
        )

    def _buy_cooldown_reason(self, intent: RiskOrderIntent) -> str | None:
        if intent.source != "auto":
            return None

        checks = [
            (
                intent.seconds_since_last_stop_exit,
                self.config.risk_stop_reentry_cooldown_minutes,
                "Stop-loss re-entry cooldown",
            ),
            (
                intent.seconds_since_last_sell,
                self.config.risk_sell_reentry_cooldown_minutes,
                "Post-SELL re-entry cooldown",
            ),
            (
                (
                    intent.seconds_since_last_buy
                    if intent.seconds_since_last_buy is not None
                    else intent.seconds_since_last_auto_order
                ),
                self.config.risk_auto_symbol_cooldown_minutes,
                "BUY cooldown",
            ),
        ]
        for elapsed, minutes, label in checks:
            if elapsed is None:
                continue
            limit = minutes * 60
            if elapsed < limit:
                return f"{label} is active ({limit - elapsed}s remaining)."
        return None

    @staticmethod
    def _quantity_for_notional(
        *,
        market: str,
        notional: Decimal,
        price: Decimal,
    ) -> Decimal:
        if price <= 0:
            return Decimal("0")
        raw = notional / price
        if market == "stock":
            return raw.quantize(Decimal("1"), rounding=ROUND_DOWN)
        return raw.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

    def _result(
        self,
        intent: RiskOrderIntent,
        *,
        status: str,
        reasons: list[str],
        adjusted_notional: Decimal | None = None,
        adjusted_quantity: Decimal | None = None,
        triggered_rule: str | None = None,
    ) -> RiskGuardResult:
        result = RiskGuardResult(
            status=status,
            reasons=reasons,
            symbol=intent.symbol,
            action=intent.action,
            original_notional=intent.order_notional,
            original_quantity=intent.order_quantity,
            adjusted_notional=(
                intent.order_notional
                if adjusted_notional is None
                else adjusted_notional
            ),
            adjusted_quantity=(
                intent.order_quantity
                if adjusted_quantity is None
                else adjusted_quantity
            ),
            triggered_rule=triggered_rule,
        )

        self.audit.write(
            "system",
            {
                "event": "risk_guard_evaluated",
                "source": intent.source,
                "market": intent.market,
                "symbol": intent.symbol,
                "action": intent.action,
                "status": result.status,
                "triggered_rule": result.triggered_rule,
                "reasons": result.reasons,
                "original_notional": str(result.original_notional),
                "original_quantity": str(result.original_quantity),
                "adjusted_notional": str(result.adjusted_notional),
                "adjusted_quantity": str(result.adjusted_quantity),
            },
        )
        return result
