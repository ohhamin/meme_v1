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
                    "Decision market does not match the selected broker account."
                ),
            )

        if decision.action == "HOLD":
            return self._no_order(
                decision,
                reason="HOLD decision creates no order.",
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
                        "BUY score is below sizing threshold "
                        f"({decision.score} < {self.config.position_buy_min_score})."
                    ),
                )

            target_pct = Decimal(str(self._buy_pct(decision.score)))
            notional = (
                portfolio.equity * target_pct / Decimal("100")
            ).quantize(Decimal("1"), rounding=ROUND_DOWN)

            if notional <= 0:
                return self._no_order(
                    decision,
                    reason="Calculated BUY notional is zero.",
                )

            if decision.market == "stock":
                quantity = (
                    notional / instrument.price
                ).quantize(Decimal("1"), rounding=ROUND_DOWN)
                if quantity <= 0:
                    return self._no_order(
                        decision,
                        reason="Calculated stock quantity is below 1 share.",
                    )
                notional = quantity * instrument.price
            else:
                quantity = (
                    notional / instrument.price
                ).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                if quantity <= 0:
                    return self._no_order(
                        decision,
                        reason="Calculated crypto quantity is zero.",
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
                reason=f"BUY sized at {target_pct}% of current equity.",
            )

        # SELL
        if decision.score > self.config.position_sell_max_score:
            return self._no_order(
                decision,
                reason=(
                    "SELL score is above sizing threshold "
                    f"({decision.score} > {self.config.position_sell_max_score})."
                ),
            )

        if position is None or position.quantity <= 0:
            return self._no_order(
                decision,
                reason="No current position to sell.",
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
                reason="Calculated SELL quantity is zero.",
            )

        return PositionSizeResult(
            status="ORDER",
            market=decision.market,
            symbol=decision.symbol,
            action=decision.action,
            score=decision.score,
            order_notional=quantity * instrument.price,
            order_quantity=quantity,
            reason=f"SELL sized at {sell_pct}% of current position.",
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
