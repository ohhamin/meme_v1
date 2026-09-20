import math
from typing import Any


class PureMathSignalService:
    """Experimental, fully deterministic statistical signal.

    This model is NOT used for live/paper trading. It exists so the current
    research-weighted quant model can be compared against a low-parameter,
    purely mathematical benchmark in no-lookahead backtests.

    Evidence is converted to z-scores and combined by the median, avoiding
    fitted weights. BUY/SELL requires a one-sided 90% normal-confidence level.
    """

    Z_90 = 1.2815515655446004

    @classmethod
    def enrich(
        cls,
        *,
        market: str,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(features)
        if result.get("features_available") != 1:
            return cls._neutral(result, "데이터 부족")

        vol = cls._number(result.get("realized_volatility_pct"))
        if vol is None or vol <= 0:
            return cls._neutral(result, "변동성 계산 불가")

        if market == "stock":
            evidence = [
                (
                    "60일 상승빈도",
                    cls._sign_z(
                        result.get("positive_day_ratio_long"),
                        60,
                    ),
                ),
                (
                    "20일 상승빈도",
                    cls._sign_z(
                        result.get("positive_day_ratio_medium"),
                        20,
                    ),
                ),
                (
                    "20일 위험조정수익",
                    cls._return_z(
                        result.get("return_medium_pct"),
                        vol,
                        20,
                    ),
                ),
            ]
        elif market == "crypto":
            evidence = [
                (
                    "21일 위험조정수익",
                    cls._return_z(
                        result.get("return_medium_pct"),
                        vol,
                        21,
                    ),
                ),
                (
                    "7일 위험조정수익",
                    cls._return_z(
                        result.get("return_short_pct"),
                        vol,
                        7,
                    ),
                ),
                (
                    "21일 상승빈도",
                    cls._sign_z(
                        result.get("positive_day_ratio_medium"),
                        21,
                    ),
                ),
            ]
        else:
            raise ValueError("market must be stock or crypto")

        valid = [
            (label, z)
            for label, z in evidence
            if z is not None and math.isfinite(z)
        ]
        if len(valid) < 2:
            return cls._neutral(result, "유효 신호 부족")

        z_values = sorted(z for _, z in valid)
        aggregate_z = cls._median(z_values)
        evidence_score = cls._normal_cdf(aggregate_z) * 100.0

        if aggregate_z >= cls.Z_90:
            action = "BUY"
        elif aggregate_z <= -cls.Z_90:
            action = "SELL"
        else:
            action = "HOLD"

        result.update(
            {
                "math_score": round(evidence_score, 2),
                "math_action": action,
                "math_z": round(aggregate_z, 4),
                "math_confidence_level": 0.90,
                "math_components": " · ".join(
                    f"{label} z={z:.2f}"
                    for label, z in valid
                ),
            }
        )
        return result

    @classmethod
    def _neutral(
        cls,
        result: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        result.update(
            {
                "math_score": 50.0,
                "math_action": "HOLD",
                "math_z": 0.0,
                "math_confidence_level": 0.90,
                "math_components": reason,
            }
        )
        return result

    @classmethod
    def _sign_z(
        cls,
        ratio_pct: Any,
        n: int,
    ) -> float | None:
        ratio = cls._number(ratio_pct)
        if ratio is None or n < 2:
            return None
        p = cls._clamp(ratio / 100.0, 0.0, 1.0)
        standard_error = math.sqrt(0.25 / n)
        if standard_error <= 0:
            return None
        return cls._clamp(
            (p - 0.5) / standard_error,
            -4.0,
            4.0,
        )

    @classmethod
    def _return_z(
        cls,
        return_pct: Any,
        daily_vol_pct: float,
        horizon: int,
    ) -> float | None:
        value = cls._number(return_pct)
        if value is None or horizon < 1:
            return None
        denom = daily_vol_pct * math.sqrt(horizon)
        if denom <= 0:
            return None
        return cls._clamp(value / denom, -4.0, 4.0)

    @staticmethod
    def _median(values: list[float]) -> float:
        middle = len(values) // 2
        if len(values) % 2:
            return values[middle]
        return (values[middle - 1] + values[middle]) / 2.0

    @staticmethod
    def _normal_cdf(z: float) -> float:
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

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
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))
