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
                count=61,
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
        if len(closes) < 25 or len(volumes) != len(closes):
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
        medium_momentum = [item["return_20d_pct"] for item in rows]
        short_momentum = [item["return_5d_pct"] for item in rows]
        activity = [item["volume_ratio_5d"] for item in rows]
        stability = [-item["volatility_20d_pct"] for item in rows]

        for index, item in enumerate(rows):
            components = {
                "liquidity": round(
                    cls._percentile(liquidity, liquidity[index]),
                    2,
                ),
                "momentum_20d": round(
                    cls._percentile(
                        medium_momentum,
                        medium_momentum[index],
                    ),
                    2,
                ),
                "momentum_5d": round(
                    cls._percentile(
                        short_momentum,
                        short_momentum[index],
                    ),
                    2,
                ),
                "activity": round(
                    cls._percentile(activity, activity[index]),
                    2,
                ),
                "stability": round(
                    cls._percentile(stability, stability[index]),
                    2,
                ),
            }
            raw_score = (
                components["liquidity"] * 0.45
                + components["momentum_20d"] * 0.20
                + components["momentum_5d"] * 0.10
                + components["activity"] * 0.15
                + components["stability"] * 0.10
            )

            penalties: list[dict] = []
            if abs(item["return_5d_pct"]) > 12:
                penalties.append(
                    {
                        "code": "short_term_move",
                        "points": 8,
                        "detail": "5일 등락폭이 12%를 초과",
                    }
                )
            if item["return_20d_pct"] > 30:
                penalties.append(
                    {
                        "code": "extended_momentum",
                        "points": 7,
                        "detail": "20일 상승률이 30%를 초과",
                    }
                )
            if item["volatility_20d_pct"] > 5:
                penalties.append(
                    {
                        "code": "high_volatility",
                        "points": 8,
                        "detail": "20일 변동성이 5%를 초과",
                    }
                )

            penalty_total = sum(
                int(penalty["points"])
                for penalty in penalties
            )
            score = raw_score - penalty_total

            item["score_components"] = components
            item["raw_score"] = round(raw_score, 2)
            item["penalties"] = penalties
            item["penalty_total"] = penalty_total
            item["score"] = round(
                max(0.0, min(100.0, score)),
                2,
            )
            item["selection_reason"] = cls._selection_reason(item)

    @staticmethod
    def _selection_reason(item: dict) -> str:
        components = item.get("score_components") or {}
        labels = {
            "liquidity": "유동성",
            "momentum_20d": "20일 추세",
            "momentum_5d": "5일 추세",
            "activity": "거래활성도",
            "stability": "변동성 안정성",
        }
        strongest = sorted(
            components.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )[:2]
        strengths = " · ".join(
            f"{labels.get(key, key)} {value:.0f}"
            for key, value in strongest
        )
        penalty_total = int(item.get("penalty_total") or 0)
        if penalty_total > 0:
            return (
                f"{strengths} 강점 · 과열/변동성 감점 "
                f"-{penalty_total}"
            )
        return f"{strengths} 강점 · 별도 감점 없음"

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
        payload = {
            "refreshed_at": datetime.now(self.tz).isoformat(),
            "selected": selected,
            "ranking": [
                {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "score": item["score"],
                    "raw_score": item.get("raw_score"),
                    "score_components": item.get(
                        "score_components",
                        {},
                    ),
                    "penalty_total": item.get("penalty_total", 0),
                    "penalties": item.get("penalties", []),
                    "selection_reason": item.get(
                        "selection_reason",
                        "",
                    ),
                    "selected": item["symbol"] in selected,
                    "avg_turnover_20d": round(
                        item["avg_turnover_20d"],
                        2,
                    ),
                    "return_5d_pct": round(item["return_5d_pct"], 4),
                    "return_20d_pct": round(item["return_20d_pct"], 4),
                    "volatility_20d_pct": round(
                        item["volatility_20d_pct"],
                        4,
                    ),
                    "volume_ratio_5d": round(
                        item["volume_ratio_5d"],
                        4,
                    ),
                }
                for item in ranked
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
