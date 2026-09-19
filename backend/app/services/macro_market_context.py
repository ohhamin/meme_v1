import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger
from backend.app.brokers.upbit_market_data import UpbitMarketDataAdapter, UpbitMarketDataError


class MacroMarketContextService:
    """Fetch and persist deterministic macro observations used as LLM context."""

    SERIES = {
        "us_10y_yield": {"series_id": "DGS10", "unit": "percent"},
        "wti_oil": {"series_id": "DCOILWTICO", "unit": "usd_per_barrel"},
        "usd_krw": {"series_id": "DEXKOUS", "unit": "krw_per_usd"},
        "sp500": {"series_id": "SP500", "unit": "index"},
        "nasdaq_composite": {"series_id": "NASDAQCOM", "unit": "index"},
    }

    def __init__(self):
        self.config = get_settings()
        self.audit = AuditLogger()
        self.upbit = UpbitMarketDataAdapter()
        self.path: Path = self.config.data_path / "context" / "market_context.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def refresh(self) -> dict:
        indicators: dict[str, dict] = {}
        failures: list[str] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            if self.config.fred_api_key:
                for name, spec in self.SERIES.items():
                    try:
                        indicators[name] = await self._fetch_series(client, spec["series_id"], spec["unit"])
                    except (httpx.HTTPError, ValueError, KeyError) as exc:
                        failures.append(f"{name}:{type(exc).__name__}")
            if self.config.krx_api_key:
                for name, endpoint, index_name in (("kospi", "kospi_dd_trd", "코스피"), ("kosdaq", "kosdaq_dd_trd", "코스닥")):
                    try:
                        indicators[name] = await self._fetch_krx_index(client, endpoint, index_name)
                    except (httpx.HTTPError, ValueError, KeyError) as exc:
                        failures.append(f"{name}:{type(exc).__name__}")
        try:
            quotes = await self.upbit.quotes(["KRW-BTC", "KRW-ETH"])
            for quote in quotes:
                key = "btc_krw" if quote.market == "KRW-BTC" else "eth_krw"
                indicators[key] = {"source": "Upbit", "symbol": quote.market, "value": float(quote.trade_price), "change_pct": round(float(quote.signed_change_rate) * 100, 4) if quote.signed_change_rate is not None else None, "observed_at": quote.timestamp.isoformat(), "age_seconds": quote.data_age_seconds, "unit": "krw", "status": "ok" if quote.data_age_seconds <= 300 else "stale"}
        except (UpbitMarketDataError, ValueError) as exc:
            failures.append(f"upbit_btc_eth:{type(exc).__name__}")

        if not indicators:
            self.audit.write("system", {"event": "macro_context_refresh_failed", "failures": failures})
            return self.read()

        payload = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "structured_market_data",
            "indicators": indicators,
            "partial_failures": failures,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.audit.write(
            "system",
            {
                "event": "macro_context_refreshed",
                "indicator_count": len(indicators),
                "partial_failures": failures,
            },
        )
        return payload

    async def _fetch_krx_index(self, client: httpx.AsyncClient, endpoint: str, index_name: str) -> dict:
        today = datetime.now(timezone.utc).date()
        for offset in range(0, 8):
            target = date.fromordinal(today.toordinal() - offset)
            response = await client.get(f"{self.config.krx_api_base_url}/idx/{endpoint}", params={"basDd": target.strftime("%Y%m%d")}, headers={"AUTH_KEY": self.config.krx_api_key}, timeout=self.config.krx_http_timeout_seconds)
            response.raise_for_status()
            rows = response.json().get("OutBlock_1", [])
            row = next((item for item in rows if str(item.get("IDX_NM") or "").replace(" ", "") == index_name), None)
            if row is None:
                continue
            raw_date = str(row["BAS_DD"])
            observed = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            return {"source": "KRX", "value": float(str(row["CLSPRC_IDX"]).replace(",", "")), "change": float(str(row["CMPPREVDD_IDX"]).replace(",", "")), "change_pct": float(str(row["FLUC_RT"]).replace(",", "")), "observation_date": observed, "unit": "index", **self._observation_freshness(observed)}
        raise ValueError(f"No recent KRX data for {index_name}")

    async def _fetch_series(
        self, client: httpx.AsyncClient, series_id: str, unit: str
    ) -> dict:
        response = await client.get(
            f"{self.config.fred_api_base_url}/series/observations",
            params={
                "series_id": series_id,
                "api_key": self.config.fred_api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 10,
            },
        )
        response.raise_for_status()
        observations = response.json()["observations"]
        valid = [
            (item["date"], float(item["value"]))
            for item in observations
            if item.get("value") not in {None, "", "."}
        ]
        if not valid:
            raise ValueError(f"No observations for {series_id}")

        latest_date, latest_value = valid[0]
        previous_value = valid[1][1] if len(valid) > 1 else None
        change_pct = (
            ((latest_value - previous_value) / previous_value) * 100
            if previous_value not in {None, 0}
            else None
        )
        freshness = self._observation_freshness(latest_date)
        return {
            "series_id": series_id,
            "value": latest_value,
            "previous_value": previous_value,
            "change_pct": round(change_pct, 4) if change_pct is not None else None,
            "observation_date": latest_date,
            "unit": unit,
            **freshness,
        }

    def _observation_freshness(self, observation_date: str) -> dict:
        observed = date.fromisoformat(observation_date)
        age_days = max(0, (datetime.now(timezone.utc).date() - observed).days)
        max_days = max(1, (self.config.macro_context_max_age_hours + 23) // 24)
        return {
            "age_days": age_days,
            "status": "stale" if age_days > max_days else "ok",
        }

    def read(self) -> dict:
        if not self.path.exists():
            return {"status": "unavailable", "reason": "not_collected"}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            collected = datetime.fromisoformat(payload["collected_at"])
            if collected.tzinfo is None:
                collected = collected.replace(tzinfo=timezone.utc)
            age_hours = (
                datetime.now(timezone.utc) - collected.astimezone(timezone.utc)
            ).total_seconds() / 3600
            payload["age_hours"] = round(max(0.0, age_hours), 2)
            indicators = payload.get("indicators", {})
            for indicator in indicators.values():
                observed = indicator.get("observation_date")
                if observed:
                    indicator.update(self._observation_freshness(observed))
            statuses = [item.get("status") for item in indicators.values()]
            payload["status"] = (
                "stale"
                if age_hours > self.config.macro_context_max_age_hours or "stale" in statuses
                else "ok"
            )
            return payload
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return {"status": "unavailable", "reason": "invalid_cache"}
