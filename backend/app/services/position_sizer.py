from decimal import Decimal, ROUND_DOWN

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    MarketInstrumentSnapshot,
    PaperPortfolio,
    PositionSizeResult,
    SymbolDecision,
)


class PositionSizer:
    """Deterministic translation from decision -> order size.

    BUY/SELL direction comes from the decision engine.
    This class only decides the proposed size and never bypasses Risk Guard.
    """

    def __init__(self):
        self.config = get_settings()

    def size(
        self,
        *,
        decision: SymbolDecision,
        instrument: MarketInstrumentSnapshot,
        portfolio: PaperPortfolio,
    ) -> PositionSizeResult:
        if portfolio.market != decision.market:
            return self._no_order(
                decision,
                reason=(
                    "판단 시장과 선택된 계좌의 시장이 일치하지 않아 주문하지 않았어요."
                ),
            )

        if decision.action == "HOLD":
            return self._no_order(
                decision,
                reason="HOLD 판단이라 주문하지 않았어요.",
            )

        position = next(
            (
                p
                for p in portfolio.positions
                if p.market == decision.market and p.symbol == decision.symbol
            ),
            None,
        )

        if decision.action == "BUY":
            if decision.score < self.config.position_buy_min_score:
                return self._no_order(
                    decision,
                    reason=(
                        "BUY 점수가 주문 생성 기준보다 낮아 주문하지 않았어요. "
                        f"({decision.score} < {self.config.position_buy_min_score})"
                    ),
                )

            base_target_pct = Decimal(str(self._buy_pct(decision.score)))
            risk_scale = self._risk_scale(instrument)
            target_pct = base_target_pct * risk_scale
            notional = (
                portfolio.equity * target_pct / Decimal("100")
            ).quantize(Decimal("1"), rounding=ROUND_DOWN)

            if notional <= 0:
                return self._no_order(
                    decision,
                    reason="계산된 매수 금액이 0원이라 주문하지 않았어요.",
                )

            if decision.market == "stock":
                quantity = (
                    notional / instrument.price
                ).quantize(Decimal("1"), rounding=ROUND_DOWN)
                if quantity <= 0:
                    return self._no_order(
                        decision,
                        reason="계산된 매수 수량이 1주 미만이라 주문하지 않았어요.",
                    )
                notional = quantity * instrument.price
            else:
                quantity = (
                    notional / instrument.price
                ).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                if quantity <= 0:
                    return self._no_order(
                        decision,
                        reason="계산된 코인 매수 수량이 0이라 주문하지 않았어요.",
                    )
                notional = quantity * instrument.price

            return PositionSizeResult(
                status="ORDER",
                market=decision.market,
                symbol=decision.symbol,
                action=decision.action,
                score=decision.score,
                order_notional=notional,
                order_quantity=quantity,
                reason=(
                    f"BUY 기본 비중 {base_target_pct}% × 변동성 조정 "
                    f"{risk_scale} = 현재 평가금액의 {target_pct}%로 계산했어요."
                ),
            )

        # SELL
        if decision.score > self.config.position_sell_max_score:
            return self._no_order(
                decision,
                reason=(
                    "SELL 점수가 주문 생성 기준보다 높아 주문하지 않았어요. "
                    f"({decision.score} > {self.config.position_sell_max_score})"
                ),
            )

        if position is None or position.quantity <= 0:
            return self._no_order(
                decision,
                reason="현재 보유 수량이 없어 매도 주문을 만들지 않았어요.",
            )

        sell_pct = Decimal(str(self._sell_pct(decision.score)))
        raw_quantity = position.quantity * sell_pct / Decimal("100")

        if decision.market == "stock":
            quantity = raw_quantity.quantize(
                Decimal("1"),
                rounding=ROUND_DOWN,
            )
            if quantity <= 0 and position.quantity >= 1:
                quantity = Decimal("1")
        else:
            quantity = raw_quantity.quantize(
                Decimal("0.00000001"),
                rounding=ROUND_DOWN,
            )

        quantity = min(quantity, position.quantity)
        if quantity <= 0:
            return self._no_order(
                decision,
                reason="계산된 매도 수량이 0이라 주문하지 않았어요.",
            )

        return PositionSizeResult(
            status="ORDER",
            market=decision.market,
            symbol=decision.symbol,
            action=decision.action,
            score=decision.score,
            order_notional=quantity * instrument.price,
            order_quantity=quantity,
            reason=f"현재 보유 수량의 {sell_pct}%를 매도하도록 계산했어요.",
        )

    def policy(self) -> dict:
        return {
            "buy_min_score": self.config.position_buy_min_score,
            "sell_max_score": self.config.position_sell_max_score,
            "buy_tiers": {
                "60-69": self.config.position_buy_pct_score_60,
                "70-79": self.config.position_buy_pct_score_70,
                "80-89": self.config.position_buy_pct_score_80,
                "90-100": self.config.position_buy_pct_score_90,
            },
            "sell_tiers": {
                "31-40": self.config.position_sell_pct_score_40,
                "21-30": self.config.position_sell_pct_score_30,
                "0-20": self.config.position_sell_pct_score_20,
            },
        }

    @staticmethod
    def _risk_scale(
        instrument: MarketInstrumentSnapshot,
    ) -> Decimal:
        raw = instrument.features.get("quant_risk_scale", 1.0)
        try:
            scale = Decimal(str(raw))
        except Exception:
            scale = Decimal("1")
        return max(Decimal("0.35"), min(scale, Decimal("1")))

    def _buy_pct(self, score: int) -> float:
        if score >= 90:
            return self.config.position_buy_pct_score_90
        if score >= 80:
            return self.config.position_buy_pct_score_80
        if score >= 70:
            return self.config.position_buy_pct_score_70
        return self.config.position_buy_pct_score_60

    def _sell_pct(self, score: int) -> float:
        if score <= 20:
            return self.config.position_sell_pct_score_20
        if score <= 30:
            return self.config.position_sell_pct_score_30
        return self.config.position_sell_pct_score_40

    @staticmethod
    def _no_order(
        decision: SymbolDecision,
        *,
        reason: str,
    ) -> PositionSizeResult:
        return PositionSizeResult(
            status="NO_ORDER",
            market=decision.market,
            symbol=decision.symbol,
            action=decision.action,
            score=decision.score,
            reason=reason,
        )
