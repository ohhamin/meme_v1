from decimal import Decimal

from backend.app.core.config import get_settings
from backend.app.models.schemas import RiskGuardResult, RiskOrderIntent
from backend.app.services.audit import AuditLogger
from backend.app.services.runtime_settings import RuntimeSettingsService


class RiskGuard:
    """Deterministic hard-risk gate.

    Risk Guard는 방향이나 종목을 고르지 않는다.
    이미 만들어진 주문 의도를 수정/생성하지 않고 PASS/BLOCK/NO_ORDER만 반환한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()
        self.audit = AuditLogger()

    def policy(self) -> dict:
        return {
            "max_position_pct": self.config.risk_max_position_pct,
            "max_daily_loss_pct": self.config.risk_max_daily_loss_pct,
            "max_daily_orders": self.config.risk_max_daily_orders,
            "max_data_age_seconds": self.config.risk_max_data_age_seconds,
            "min_cash_reserve_pct": self.config.risk_min_cash_reserve_pct,
            "max_open_positions": self.config.risk_max_open_positions,
            "minimum_open_positions": 0,
            "sell_is_risk_reducing": True,
            "resizes_orders": False,
        }

    def evaluate(self, intent: RiskOrderIntent) -> RiskGuardResult:
        if intent.action == "HOLD":
            return self._result(
                intent,
                status="NO_ORDER",
                reasons=["HOLD decision does not create an order."],
            )

        reasons: list[str] = []
        runtime = self.runtime.get()

        # 1) Global hard stop.
        if runtime.kill_switch:
            reasons.append("Kill switch is enabled.")

        # 2) A duplicate order in the same decision cycle is always blocked.
        if intent.same_cycle_duplicate:
            reasons.append("Duplicate order for the same symbol in this cycle.")

        # 3) Stale market/account data must never be traded automatically.
        if intent.data_age_seconds > self.config.risk_max_data_age_seconds:
            reasons.append(
                "Market/account snapshot is stale "
                f"({intent.data_age_seconds}s > "
                f"{self.config.risk_max_data_age_seconds}s)."
            )

        # 4) Stock orders require an open market. Crypto adapters normally pass true.
        if intent.market == "stock" and not intent.market_open:
            reasons.append("Stock market is closed.")

        # 5) Basic malformed-order checks.
        if intent.price <= 0:
            reasons.append("Price must be positive.")

        if intent.order_notional <= 0:
            reasons.append("Order notional must be positive.")

        if intent.action == "SELL" and intent.order_quantity <= 0:
            reasons.append("Sell quantity must be positive.")

        # SELL은 기존 위험을 줄이는 방향이므로 아래의 신규위험 제한
        # (일일 손실, 신규 노출, 현금 reserve, 주문 횟수)은 적용하지 않는다.
        # 대신 보유 수량 초과는 반드시 차단한다.
        if intent.action == "SELL":
            if intent.order_quantity > intent.position_quantity:
                reasons.append(
                    "Sell quantity exceeds current position quantity."
                )
            return self._finalize(intent, reasons)

        # From here, BUY-only exposure controls.
        # portfolio_equity / available_cash are always the selected broker account
        # (Toss stock account OR Upbit crypto account), never a combined account.
        equity = intent.portfolio_equity
        position_after = intent.position_value + intent.order_notional
        position_after_pct = self._pct(position_after, equity)

        if intent.daily_pnl_pct <= Decimal(
            str(-self.config.risk_max_daily_loss_pct)
        ):
            reasons.append(
                "Daily loss limit reached "
                f"({intent.daily_pnl_pct}% <= "
                f"-{self.config.risk_max_daily_loss_pct}%)."
            )

        if intent.daily_order_count >= self.config.risk_max_daily_orders:
            reasons.append(
                "Daily order count limit reached "
                f"({intent.daily_order_count} >= "
                f"{self.config.risk_max_daily_orders})."
            )

        if position_after_pct > Decimal(
            str(self.config.risk_max_position_pct)
        ):
            reasons.append(
                "Position exposure after order exceeds limit "
                f"({position_after_pct:.2f}% > "
                f"{self.config.risk_max_position_pct}%)."
            )

        if (
            intent.position_quantity <= 0
            and intent.open_position_count >= self.config.risk_max_open_positions
        ):
            reasons.append(
                "Maximum open position count reached "
                f"({intent.open_position_count} >= "
                f"{self.config.risk_max_open_positions})."
            )

        reserve_required = equity * (
            Decimal(str(self.config.risk_min_cash_reserve_pct))
            / Decimal("100")
        )
        cash_after = intent.available_cash - intent.order_notional

        if cash_after < 0:
            reasons.append("Insufficient available cash.")
        elif cash_after < reserve_required:
            reasons.append(
                "Cash reserve would fall below configured minimum "
                f"({self.config.risk_min_cash_reserve_pct}%)."
            )

        return self._finalize(intent, reasons)

    @staticmethod
    def _pct(value: Decimal, total: Decimal) -> Decimal:
        if total <= 0:
            return Decimal("999999")
        return (value / total) * Decimal("100")

    def _finalize(
        self,
        intent: RiskOrderIntent,
        reasons: list[str],
    ) -> RiskGuardResult:
        status = "BLOCK" if reasons else "PASS"
        return self._result(intent, status=status, reasons=reasons)

    def _result(
        self,
        intent: RiskOrderIntent,
        *,
        status: str,
        reasons: list[str],
    ) -> RiskGuardResult:
        result = RiskGuardResult(
            status=status,
            reasons=reasons,
            symbol=intent.symbol,
            action=intent.action,
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
                "reasons": result.reasons,
                "order_notional": str(intent.order_notional),
                "order_quantity": str(intent.order_quantity),
            },
        )
        return result
