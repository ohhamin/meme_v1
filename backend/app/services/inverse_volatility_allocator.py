import math
from typing import Any


class InverseVolatilityAllocator:
    """Experimental allocation benchmark.

    Relative weights are proportional to inverse realized volatility. This is a
    diagonal-covariance approximation to equal-risk allocation and deliberately
    avoids estimating expected returns. It is NOT wired into live/paper orders.
    """

    @classmethod
    def allocate(
        cls,
        instruments: list[dict[str, Any]],
        *,
        max_weight: float = 0.25,
    ) -> list[dict[str, Any]]:
        max_weight = cls._clamp(max_weight, 0.01, 1.0)
        rows: list[dict[str, Any]] = []

        for item in instruments:
            vol = cls._number(item.get("realized_volatility_pct"))
            if vol is None or vol <= 0:
                continue
            rows.append(
                {
                    "symbol": str(item.get("symbol") or ""),
                    "volatility_pct": vol,
                    "raw_weight": 1.0 / vol,
                }
            )

        if not rows:
            return []

        weights = cls._capped_normalize(
            [row["raw_weight"] for row in rows],
            cap=max_weight,
        )

        result: list[dict[str, Any]] = []
        for row, weight in zip(rows, weights, strict=True):
            result.append(
                {
                    "symbol": row["symbol"],
                    "volatility_pct": round(row["volatility_pct"], 6),
                    "weight": round(weight, 8),
                    "risk_proxy": round(
                        weight * row["volatility_pct"],
                        8,
                    ),
                }
            )
        return result

    @classmethod
    def _capped_normalize(
        cls,
        raw: list[float],
        *,
        cap: float,
    ) -> list[float]:
        count = len(raw)
        if count == 0:
            return []

        # A cap below 1/N makes a fully invested portfolio impossible.
        effective_cap = max(cap, 1.0 / count)
        remaining = set(range(count))
        weights = [0.0] * count
        budget = 1.0

        while remaining and budget > 1e-12:
            denominator = sum(raw[index] for index in remaining)
            if denominator <= 0:
                equal = budget / len(remaining)
                for index in remaining:
                    weights[index] = equal
                break

            capped: list[int] = []
            for index in remaining:
                proposed = budget * raw[index] / denominator
                if proposed > effective_cap + 1e-12:
                    weights[index] = effective_cap
                    budget -= effective_cap
                    capped.append(index)

            if not capped:
                denominator = sum(raw[index] for index in remaining)
                for index in remaining:
                    weights[index] = (
                        budget * raw[index] / denominator
                    )
                break

            remaining.difference_update(capped)

        total = sum(weights)
        if total > 0:
            weights = [value / total for value in weights]
        return weights

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
