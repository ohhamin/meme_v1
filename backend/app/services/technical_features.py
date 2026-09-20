from statistics import fmean, pstdev


class TechnicalFeatureService:
    """Compute small deterministic OHLCV summaries for the LLM context."""

    @staticmethod
    def compute(
        *,
        candles: list[dict],
        current_price: float,
        short_period: int,
        medium_period: int,
        long_period: int,
        interval_label: str,
    ) -> dict[str, float | int | str | None]:
        if current_price <= 0 or len(candles) < 2:
            return {
                "feature_interval": interval_label,
                "feature_samples": len(candles),
                "features_available": 0,
            }

        ordered = sorted(
            candles,
            key=lambda item: str(item.get("timestamp") or ""),
        )
        closes = [
            float(item["close"])
            for item in ordered
            if float(item.get("close") or 0) > 0
        ]
        highs = [
            float(item["high"])
            for item in ordered
            if float(item.get("high") or 0) > 0
        ]
        lows = [
            float(item["low"])
            for item in ordered
            if float(item.get("low") or 0) > 0
        ]
        volumes = [
            max(0.0, float(item.get("volume") or 0))
            for item in ordered
        ]

        if len(closes) < 2:
            return {
                "feature_interval": interval_label,
                "feature_samples": len(closes),
                "features_available": 0,
            }

        returns = [
            (
                (closes[index] / closes[index - 1]) - 1
            )
            * 100
            for index in range(1, len(closes))
            if closes[index - 1] > 0
        ]

        result: dict[str, float | int | str | None] = {
            "features_available": 1,
            "feature_interval": interval_label,
            "feature_samples": len(closes),
            "return_short_pct": TechnicalFeatureService._return_pct(
                closes,
                short_period,
            ),
            "return_medium_pct": TechnicalFeatureService._return_pct(
                closes,
                medium_period,
            ),
            "return_long_pct": TechnicalFeatureService._return_pct(
                closes,
                long_period,
            ),
            "sma_short_gap_pct": TechnicalFeatureService._sma_gap(
                current_price,
                closes,
                short_period,
            ),
            "sma_medium_gap_pct": TechnicalFeatureService._sma_gap(
                current_price,
                closes,
                medium_period,
            ),
            "sma_long_gap_pct": TechnicalFeatureService._sma_gap(
                current_price,
                closes,
                long_period,
            ),
            "realized_volatility_pct": (
                round(
                    pstdev(
                        returns[
                            -min(max(long_period, 2), len(returns)):
                        ]
                    ),
                    4,
                )
                if len(returns) >= 2
                else 0.0
            ),
        }

        window = min(long_period + 1, len(ordered))
        if highs and lows and window >= 2:
            recent_high = max(highs[-window:])
            recent_low = min(lows[-window:])
            result["range_long_pct"] = (
                round(
                    (recent_high / recent_low - 1) * 100,
                    4,
                )
                if recent_low > 0
                else None
            )
        else:
            result["range_long_pct"] = None

        recent_count = min(
            max(short_period, 1),
            len(volumes),
        )
        previous = volumes[
            max(0, len(volumes) - (recent_count * 2)):
            max(0, len(volumes) - recent_count)
        ]
        recent = volumes[-recent_count:]

        previous_mean = fmean(previous) if previous else 0.0
        recent_mean = fmean(recent) if recent else 0.0
        result["volume_recent_ratio"] = (
            round(recent_mean / previous_mean, 4)
            if previous_mean > 0
            else None
        )

        return result

    @staticmethod
    def _return_pct(
        closes: list[float],
        periods: int,
    ) -> float | None:
        if periods < 1 or len(closes) <= periods:
            return None
        base = closes[-(periods + 1)]
        if base <= 0:
            return None
        return round(
            (closes[-1] / base - 1) * 100,
            4,
        )

    @staticmethod
    def _sma_gap(
        current_price: float,
        closes: list[float],
        periods: int,
    ) -> float | None:
        if periods < 1 or len(closes) < periods:
            return None
        average = fmean(closes[-periods:])
        if average <= 0:
            return None
        return round(
            (current_price / average - 1) * 100,
            4,
        )
