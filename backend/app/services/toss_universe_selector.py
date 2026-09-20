import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from statistics import fmean, pstdev
from zoneinfo import ZoneInfo

from backend.app.brokers.toss_market_data import TossMarketDataAdapter
from backend.app.core.config import get_settings
from backend.app.services.toss_universe import TossUniverseService


class TossUniverseSelector:
    """Select a liquid, trend-aware Korean stock decision universe.

    This is only a candidate screener. BUY/SELL decisions still belong to the
    normal LLM -> sizing -> risk-guard pipeline.
    """

    DEFAULT_POOL = [
        "005930", "000660", "373220", "207940", "005380", "000270",
        "068270", "105560", "055550", "035420", "035720", "012330",
        "028260", "066570", "051910", "006400", "032830", "096770",
        "086790", "316140", "009150", "034020", "267260", "042660",
        "012450", "010130", "003550", "017670", "030200", "033780",
        "018260", "003670", "247540", "086280", "010950", "011200",
    ]

    def __init__(
        self,
        market_data: TossMarketDataAdapter | None = None,
        universe: TossUniverseService | None = None,
    ):
        self.market_data = market_data or TossMarketDataAdapter()
        self.universe = universe or TossUniverseService()
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.state_path: Path = (
            self.config.data_path / "state" / "toss_universe_selector.json"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def select(
        self,
        *,
        limit: int = 15,
        force: bool = True,
    ) -> list[str]:
        limit = max(1, min(limit, 30))

        if (
            not force
            and self.universe.selection_mode() == "auto"
            and self._cache_is_fresh(hours=6)
        ):
            return self.universe.get()

        infos = await self.market_data.stock_info(self.DEFAULT_POOL)
        eligible = [
            item
            for item in infos
            if item.status == "ACTIVE"
            and item.currency == "KRW"
            and item.security_type == "STOCK"
            and not item.trading_suspended
            and item.market in {"KOSPI", "KOSDAQ"}
        ]

        rows: list[dict] = []
        for item in eligible:
            candles = await self.market_data.candles(
                item.symbol,
                interval="1d",
                count=91,
            )
            metrics = self._metrics(candles)
            if metrics is None:
                continue
            if metrics["avg_turnover_20d"] < 1_000_000_000:
                continue
            rows.append(
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    **metrics,
                }
            )

        if not rows:
            return self.universe.get()

        self._score(rows)
        ranked = sorted(
            rows,
            key=lambda item: (
                item["score"],
                item["avg_turnover_20d"],
            ),
            reverse=True,
        )
        selected = [item["symbol"] for item in ranked[:limit]]
        saved = self.universe.set_auto(selected, limit=limit)
        self._save_state(ranked, saved)
        return saved

    async def refresh_if_auto(self) -> list[str]:
        if self.universe.selection_mode() != "auto":
            return self.universe.get()
        return await self.select(
            limit=self.universe.auto_limit(),
            force=False,
        )

    @staticmethod
    def _metrics(candles: list[dict]) -> dict | None:
        ordered = sorted(
            candles,
            key=lambda item: str(item.get("timestamp") or ""),
        )
        closes = [
            float(item.get("close") or 0)
            for item in ordered
            if float(item.get("close") or 0) > 0
        ]
        volumes = [
            max(0.0, float(item.get("volume") or 0))
            for item in ordered
            if float(item.get("close") or 0) > 0
        ]
        if len(closes) < 61 or len(volumes) != len(closes):
            return None

        daily_returns = [
            (closes[index] / closes[index - 1] - 1) * 100
            for index in range(1, len(closes))
            if closes[index - 1] > 0
        ]
        recent20_closes = closes[-20:]
        recent20_volumes = volumes[-20:]
        avg_turnover = fmean(
            close * volume
            for close, volume in zip(
                recent20_closes,
                recent20_volumes,
            )
        )
        prev_volume = fmean(recent20_volumes[:15])
        recent_volume = fmean(recent20_volumes[-5:])
        volume_ratio = (
            recent_volume / prev_volume
            if prev_volume > 0
            else 1.0
        )

        return {
            "avg_turnover_20d": avg_turnover,
            "return_5d_pct": TossUniverseSelector._return_pct(closes, 5),
            "return_20d_pct": TossUniverseSelector._return_pct(closes, 20),
            "return_60d_pct": TossUniverseSelector._return_pct(closes, 60),
            "volatility_20d_pct": (
                pstdev(daily_returns[-20:])
                if len(daily_returns) >= 2
                else 0.0
            ),
            "volume_ratio_5d": volume_ratio,
        }

    @staticmethod
    def _return_pct(closes: list[float], periods: int) -> float:
        if len(closes) <= periods or closes[-periods - 1] <= 0:
            return 0.0
        return (
            closes[-1] / closes[-periods - 1] - 1
        ) * 100

    @classmethod
    def _score(cls, rows: list[dict]) -> None:
        liquidity = [
            math.log1p(item["avg_turnover_20d"])
            for item in rows
        ]
        long_momentum = [item["return_60d_pct"] for item in rows]
        medium_momentum = [item["return_20d_pct"] for item in rows]
        short_momentum = [item["return_5d_pct"] for item in rows]
        activity = [item["volume_ratio_5d"] for item in rows]
        stability = [-item["volatility_20d_pct"] for item in rows]

        for index, item in enumerate(rows):
            liquidity_score = cls._percentile(
                liquidity,
                liquidity[index],
            )
            long_score = cls._percentile(
                long_momentum,
                long_momentum[index],
            )
            medium_score = cls._percentile(
                medium_momentum,
                medium_momentum[index],
            )
            short_score = cls._percentile(
                short_momentum,
                short_momentum[index],
            )
            activity_score = cls._percentile(
                activity,
                activity[index],
            )
            stability_score = cls._percentile(
                stability,
                stability[index],
            )

            raw_score = (
                liquidity_score * 0.35
                + long_score * 0.30
                + medium_score * 0.20
                + activity_score * 0.05
                + stability_score * 0.10
            )

            penalty = 0.0
            penalty_reasons: list[str] = []
            # Avoid filling the candidate list with short-term blow-off moves.
            if abs(item["return_5d_pct"]) > 12:
                penalty += 8
                penalty_reasons.append("5일 급등락")
            if item["return_20d_pct"] > 30:
                penalty += 7
                penalty_reasons.append("20일 과열")
            if item["return_60d_pct"] > 50:
                penalty += 7
                penalty_reasons.append("60일 과열")
            if item["volatility_20d_pct"] > 5:
                penalty += 8
                penalty_reasons.append("높은 변동성")

            item["liquidity_score"] = round(liquidity_score, 2)
            item["momentum_60d_score"] = round(long_score, 2)
            item["momentum_20d_score"] = round(medium_score, 2)
            item["momentum_5d_score"] = round(short_score, 2)
            item["activity_score"] = round(activity_score, 2)
            item["stability_score"] = round(stability_score, 2)
            item["penalty"] = round(penalty, 2)
            item["penalty_reasons"] = penalty_reasons
            item["score"] = round(
                max(0.0, min(100.0, raw_score - penalty)),
                2,
            )

    @staticmethod
    def _percentile(values: list[float], value: float) -> float:
        if len(values) <= 1:
            return 100.0
        below = sum(1 for item in values if item < value)
        equal = sum(1 for item in values if item == value)
        rank = below + max(0, equal - 1) / 2
        return rank / (len(values) - 1) * 100

    def _cache_is_fresh(self, *, hours: int) -> bool:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            refreshed_at = datetime.fromisoformat(
                str(raw.get("refreshed_at") or "")
            )
            if refreshed_at.tzinfo is None:
                refreshed_at = refreshed_at.replace(tzinfo=self.tz)
            return datetime.now(self.tz) - refreshed_at < timedelta(hours=hours)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def _save_state(self, ranked: list[dict], selected: list[str]) -> None:
        selected_set = set(selected)
        payload = {
            "refreshed_at": datetime.now(self.tz).isoformat(),
            "selected": selected,
            "ranking": [
                {
                    "rank": index + 1,
                    "selected": item["symbol"] in selected_set,
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "score": item["score"],
                    "liquidity_score": item["liquidity_score"],
                    "momentum_60d_score": item["momentum_60d_score"],
                    "momentum_20d_score": item["momentum_20d_score"],
                    "momentum_5d_score": item["momentum_5d_score"],
                    "activity_score": item["activity_score"],
                    "stability_score": item["stability_score"],
                    "penalty": item["penalty"],
                    "penalty_reasons": item["penalty_reasons"],
                    "avg_turnover_20d": round(
                        item["avg_turnover_20d"],
                        2,
                    ),
                    "return_5d_pct": round(item["return_5d_pct"], 4),
                    "return_20d_pct": round(item["return_20d_pct"], 4),
                    "return_60d_pct": round(item["return_60d_pct"], 4),
                    "volatility_20d_pct": round(
                        item["volatility_20d_pct"],
                        4,
                    ),
                    "volume_ratio_5d": round(
                        item["volume_ratio_5d"],
                        4,
                    ),
                }
                for index, item in enumerate(ranked)
            ],
        }
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.state_path)

    def status(self) -> dict:
        ranking = []
        refreshed_at = None
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            ranking = raw.get("ranking") or []
            refreshed_at = raw.get("refreshed_at")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

        return {
            "selection_mode": self.universe.selection_mode(),
            "auto_limit": self.universe.auto_limit(),
            "symbols": self.universe.get(),
            "refreshed_at": refreshed_at,
            "ranking": ranking,
        }
