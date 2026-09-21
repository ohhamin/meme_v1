import asyncio
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from statistics import fmean, pstdev
from zoneinfo import ZoneInfo

from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter
from backend.app.core.config import get_settings
from backend.app.services.upbit_universe import UpbitUniverseService


class UpbitUniverseSelector:
    """Select liquid crypto candidates using short-horizon momentum.

    Liquidity is a hard practical preference; price momentum decides which of
    the liquid coins deserve attention. This is candidate selection only.
    """

    def __init__(
        self,
        market_data: UpbitMarketDataAdapter | None = None,
        universe: UpbitUniverseService | None = None,
    ):
        self.market_data = market_data or UpbitMarketDataAdapter()
        self.universe = universe or UpbitUniverseService()
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.state_path: Path = (
            self.config.data_path / "state" / "upbit_universe_selector.json"
        )
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def select(
        self,
        *,
        limit: int = 20,
        force: bool = True,
        required_markets: list[str] | None = None,
    ) -> list[str]:
        limit = max(1, min(limit, 30))
        required = self._stable_unique(required_markets or [])[:limit]
        if (
            not force
            and self.universe.selection_mode() == "auto"
            and self._cache_is_fresh(hours=6)
        ):
            return self.universe.get()

        markets = await self.market_data.list_markets(
            quote_currency="KRW",
            details=True,
        )
        eligible = [
            item.market
            for item in markets
            if not item.warning
            and not item.caution
            and item.market != "KRW-USDT"
        ]
        quotes = await self.market_data.quotes(eligible)
        liquid = [
            item
            for item in sorted(
                quotes,
                key=lambda item: item.acc_trade_price_24h or 0,
                reverse=True,
            )
            if item.acc_trade_price_24h is not None
            and item.acc_trade_price_24h > 0
        ][: max(30, limit * 3)]

        rows: list[dict] = []
        for index, quote in enumerate(liquid):
            try:
                candles = await self.market_data.daily_candles(
                    quote.market,
                    count=64,
                )
                metrics = self._metrics(candles)
            except Exception:
                metrics = None

            if metrics is not None:
                rows.append(
                    {
                        "market": quote.market,
                        "liquidity_24h": float(
                            quote.acc_trade_price_24h or 0
                        ),
                        **metrics,
                    }
                )

            if index < len(liquid) - 1:
                await asyncio.sleep(0.11)

        if not rows:
            selected = self._fill_required(
                required,
                [item.market for item in liquid],
                limit,
            )
            return self.universe.set_auto(selected, limit=limit)

        self._score(rows)
        ranked = sorted(
            rows,
            key=lambda item: (
                item["score"],
                item["liquidity_24h"],
            ),
            reverse=True,
        )
        selected = self._fill_required(
            required,
            [item["market"] for item in ranked],
            limit,
        )
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
    def _stable_unique(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw).strip().upper()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @classmethod
    def _fill_required(
        cls,
        required: list[str],
        ranked: list[str],
        limit: int,
    ) -> list[str]:
        return cls._stable_unique([*required, *ranked])[:limit]

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
        if len(closes) < 43 or len(volumes) != len(closes):
            return None

        returns = [
            (closes[i] / closes[i - 1] - 1) * 100
            for i in range(1, len(closes))
            if closes[i - 1] > 0
        ]
        recent21 = volumes[-21:]
        previous14 = recent21[:14]
        recent7 = recent21[-7:]
        previous_mean = fmean(previous14) if previous14 else 0.0
        recent_mean = fmean(recent7) if recent7 else 0.0

        return {
            "return_7d_pct": UpbitUniverseSelector._return_pct(closes, 7),
            "return_21d_pct": UpbitUniverseSelector._return_pct(closes, 21),
            "return_42d_pct": UpbitUniverseSelector._return_pct(closes, 42),
            "volatility_21d_pct": (
                pstdev(returns[-21:])
                if len(returns) >= 2
                else 0.0
            ),
            "volume_ratio_7d": (
                recent_mean / previous_mean
                if previous_mean > 0
                else 1.0
            ),
        }

    @staticmethod
    def _return_pct(closes: list[float], periods: int) -> float:
        if len(closes) <= periods or closes[-periods - 1] <= 0:
            return 0.0
        return (closes[-1] / closes[-periods - 1] - 1) * 100

    @classmethod
    def _score(cls, rows: list[dict]) -> None:
        liquidity = [
            math.log1p(item["liquidity_24h"])
            for item in rows
        ]
        medium = [item["return_21d_pct"] for item in rows]
        short = [item["return_7d_pct"] for item in rows]
        activity = [item["volume_ratio_7d"] for item in rows]
        stability = [-item["volatility_21d_pct"] for item in rows]

        for index, item in enumerate(rows):
            liquidity_score = cls._percentile(liquidity, liquidity[index])
            medium_score = cls._percentile(medium, medium[index])
            short_score = cls._percentile(short, short[index])
            activity_score = cls._percentile(activity, activity[index])
            stability_score = cls._percentile(stability, stability[index])

            raw = (
                liquidity_score * 0.35
                + medium_score * 0.30
                + short_score * 0.20
                + stability_score * 0.10
                + activity_score * 0.05
            )

            penalty = 0.0
            reasons: list[str] = []
            if abs(item["return_7d_pct"]) > 25:
                penalty += 8
                reasons.append("7일 급등락")
            if item["return_42d_pct"] > 60:
                penalty += 8
                reasons.append("42일 과열")
            if item["volatility_21d_pct"] > 8:
                penalty += 8
                reasons.append("높은 변동성")

            item["liquidity_score"] = round(liquidity_score, 2)
            item["momentum_21d_score"] = round(medium_score, 2)
            item["momentum_7d_score"] = round(short_score, 2)
            item["activity_score"] = round(activity_score, 2)
            item["stability_score"] = round(stability_score, 2)
            item["penalty"] = round(penalty, 2)
            item["penalty_reasons"] = reasons
            item["score"] = round(
                max(0.0, min(100.0, raw - penalty)),
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
                    **item,
                    "rank": index + 1,
                    "selected": item["market"] in selected_set,
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
