import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger


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
        self.path: Path = self.config.data_path / "context" / "market_context.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def refresh(self) -> dict:
        if not self.config.fred_api_key:
            return self.read()

        indicators: dict[str, dict] = {}
        failures: list[str] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, spec in self.SERIES.items():
                try:
                    indicators[name] = await self._fetch_series(
                        client, spec["series_id"], spec["unit"]
                    )
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    failures.append(f"{name}:{type(exc).__name__}")

        if not indicators:
            self.audit.write("system", {"event": "macro_context_refresh_failed", "failures": failures})
            return self.read()

        payload = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "source": "FRED",
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
        return {
            "series_id": series_id,
            "value": latest_value,
            "previous_value": previous_value,
            "change_pct": round(change_pct, 4) if change_pct is not None else None,
            "observation_date": latest_date,
            "unit": unit,
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
            payload["status"] = (
                "stale"
                if age_hours > self.config.macro_context_max_age_hours
                else "ok"
            )
            payload["age_hours"] = round(max(0.0, age_hours), 2)
            return payload
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return {"status": "unavailable", "reason": "invalid_cache"}
