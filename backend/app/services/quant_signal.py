import math
from typing import Any


class QuantSignalService:
    """Deterministic, research-inspired directional prior.

    The score is deliberately simple and inspectable. It does not predict an
    exact return. It converts medium-horizon momentum, trend, volatility and
    volume confirmation into a 0-100 prior that the LLM may only confirm or
    downgrade to HOLD.
    """

    MODEL_VERSION = "v0.4"
    BUY_THRESHOLD = 65.0
    SELL_THRESHOLD = 35.0

    @classmethod
    def enrich(
        cls,
        *,
        market: str,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(features)
        if result.get("features_available") != 1:
            result.update(
                {
                    "quant_model_version": cls.MODEL_VERSION,
                    "quant_score": 50.0,
                    "quant_action": "HOLD",
                    "quant_risk_scale": 0.5,
                    "quant_components": "데이터 부족",
                }
            )
            return result

        vol = cls._number(result.get("realized_volatility_pct"))
        if vol is None or vol <= 0:
            result.update(
                {
                    "quant_model_version": cls.MODEL_VERSION,
                    "quant_score": 50.0,
                    "quant_action": "HOLD",
                    "quant_risk_scale": 0.5,
                    "quant_components": "변동성 계산 불가",
                }
            )
            return result

        short_ret = cls._number(result.get("return_short_pct"))
        medium_ret = cls._number(result.get("return_medium_pct"))
        long_ret = cls._number(result.get("return_long_pct"))
        sign_medium = cls._number(
            result.get("positive_day_ratio_medium")
        )
        sign_long = cls._number(
            result.get("positive_day_ratio_long")
        )
        short_gap = cls._number(result.get("sma_short_gap_pct"))
        long_gap = cls._number(result.get("sma_long_gap_pct"))
        volume_ratio = cls._number(result.get("volume_recent_ratio"))

        if market == "stock":
            short_h, medium_h = 5, 20
            short_m = cls._momentum_score(short_ret, vol, short_h)
            medium_m = cls._momentum_score(medium_ret, vol, medium_h)
            sign60 = cls._sign_score(sign_long)
            sign20 = cls._sign_score(sign_medium)
            trend = cls._trend_score(short_gap, long_gap, vol)
            stability = cls._stability_score(vol, low=1.0, high=4.0)
            anchor = sign60 * 0.60 + sign20 * 0.40
            confirmation = cls._volume_confirmation(
                anchor=anchor,
                volume_ratio=volume_ratio,
            )

            # Korean-equity evidence is less supportive of traditional raw
            # winner-minus-loser momentum. Daily sign momentum gets the
            # largest weight because it is less dominated by a few salient
            # price jumps, while 20-day magnitude momentum is only supportive.
            raw = (
                sign60 * 0.30
                + sign20 * 0.20
                + trend * 0.20
                + medium_m * 0.15
                + stability * 0.10
                + confirmation * 0.05
            )

            penalty = 0.0
            # Large short/medium moves are treated as reversal/entry risk.
            if short_m >= 80:
                penalty += (short_m - 80) * 0.40
            if medium_m >= 85:
                penalty += (medium_m - 85) * 0.45

            target_vol = 2.0
            components = (
                f"60일 상승빈도 {sign60:.0f} · "
                f"20일 상승빈도 {sign20:.0f} · "
                f"추세 {trend:.0f} · "
                f"20일 위험조정수익 {medium_m:.0f}"
            )
        else:
            short_h, medium_h, long_h = 7, 21, 42
            short_m = cls._momentum_score(short_ret, vol, short_h)
            medium_m = cls._momentum_score(medium_ret, vol, medium_h)
            long_m = cls._momentum_score(long_ret, vol, long_h)
            trend = cls._trend_score(short_gap, long_gap, vol)
            stability = cls._stability_score(vol, low=2.0, high=8.0)
            anchor = short_m * 0.38 + medium_m * 0.62
            confirmation = cls._volume_confirmation(
                anchor=anchor,
                volume_ratio=volume_ratio,
            )

            raw = (
                medium_m * 0.40
                + short_m * 0.30
                + trend * 0.15
                + stability * 0.10
                + confirmation * 0.05
            )

            # Crypto research finds short-horizon momentum but faster reversal
            # beyond roughly one month. Strong 42-day winners therefore get a
            # conservative overextension penalty; past losers are NOT granted
            # an automatic buy bonus.
            penalty = 0.0
            if long_m > 70 and long_m > medium_m:
                penalty += (long_m - 70) * 0.45

            target_vol = 4.0
            components = (
                f"21일 모멘텀 {medium_m:.0f} · "
                f"7일 모멘텀 {short_m:.0f} · "
                f"추세 {trend:.0f} · 안정성 {stability:.0f}"
            )

        score = cls._clamp(raw - penalty, 0.0, 100.0)
        action = (
            "BUY"
            if score >= cls.BUY_THRESHOLD
            else "SELL"
            if score <= cls.SELL_THRESHOLD
            else "HOLD"
        )

        # Never lever low-volatility instruments up. Volatility management only
        # reduces exposure when realized volatility is above the target.
        risk_scale = cls._clamp(target_vol / vol, 0.35, 1.0)

        result.update(
            {
                "quant_model_version": cls.MODEL_VERSION,
                "quant_score": round(score, 2),
                "quant_action": action,
                "quant_risk_scale": round(risk_scale, 4),
                "quant_penalty": round(penalty, 2),
                "quant_components": components,
            }
        )
        return result

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _sign_score(value: float | None) -> float:
        if value is None:
            return 50.0
        return max(0.0, min(value, 100.0))

    @classmethod
    def _momentum_score(
        cls,
        return_pct: float | None,
        daily_vol_pct: float,
        horizon: int,
    ) -> float:
        if return_pct is None:
            return 50.0
        denom = max(daily_vol_pct * math.sqrt(horizon), 0.25)
        z = cls._clamp(return_pct / denom, -2.0, 2.0)
        return 50.0 + 25.0 * z

    @classmethod
    def _trend_score(
        cls,
        short_gap: float | None,
        long_gap: float | None,
        daily_vol_pct: float,
    ) -> float:
        def gap_score(value: float | None) -> float:
            if value is None:
                return 50.0
            scaled = cls._clamp(
                value / max(daily_vol_pct * 2.0, 0.5),
                -2.0,
                2.0,
            )
            return 50.0 + 25.0 * scaled

        return gap_score(short_gap) * 0.4 + gap_score(long_gap) * 0.6

    @classmethod
    def _stability_score(
        cls,
        volatility: float,
        *,
        low: float,
        high: float,
    ) -> float:
        if volatility <= low:
            return 100.0
        if volatility >= high:
            return 0.0
        return 100.0 * (high - volatility) / (high - low)

    @classmethod
    def _volume_confirmation(
        cls,
        *,
        anchor: float,
        volume_ratio: float | None,
    ) -> float:
        if volume_ratio is None or volume_ratio <= 0:
            return 50.0
        volume_signal = 25.0 * cls._clamp(
            math.log(volume_ratio, 2),
            -2.0,
            2.0,
        )
        direction = cls._clamp((anchor - 50.0) / 50.0, -1.0, 1.0)
        return cls._clamp(50.0 + direction * volume_signal, 0.0, 100.0)

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))
