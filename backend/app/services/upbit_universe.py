import json
from pathlib import Path

from backend.app.core.config import get_settings


class UpbitUniverseService:
    """Persist the user's crypto decision universe locally.

    This is a candidate universe, not a target holding count.
    Holding count is still controlled separately by Risk Guard (0~10).
    """

    def __init__(self):
        self.config = get_settings()
        self.path: Path = (
            self.config.data_path
            / "state"
            / "upbit_universe.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> list[str]:
        if not self.path.exists():
            initial = self._normalize(
                self.config.upbit_decision_market_list
            )
            self._write(initial)
            return initial

        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            values = raw.get("markets", [])
            if not isinstance(values, list):
                raise ValueError("invalid markets")
            return self._normalize(values)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            initial = self._normalize(
                self.config.upbit_decision_market_list
            )
            self._write(initial)
            return initial

    def selection_mode(self) -> str:
        if not self.path.exists():
            self.get()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            mode = str(raw.get("selection_mode") or "manual").lower()
            return mode if mode in {"manual", "auto"} else "manual"
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return "manual"

    def auto_limit(self) -> int:
        if not self.path.exists():
            self.get()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return max(1, min(int(raw.get("auto_limit") or 10), 50))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 10

    def set(self, markets: list[str]) -> list[str]:
        return self.set_manual(markets)

    def set_manual(self, markets: list[str]) -> list[str]:
        normalized = self._normalize(markets)
        self._write(
            normalized,
            selection_mode="manual",
            auto_limit=self.auto_limit(),
        )
        return normalized

    def set_auto(self, markets: list[str], *, limit: int) -> list[str]:
        normalized = self._normalize(markets)
        self._write(
            normalized,
            selection_mode="auto",
            auto_limit=max(1, min(limit, 50)),
        )
        return normalized

    def _write(
        self,
        markets: list[str],
        *,
        selection_mode: str = "manual",
        auto_limit: int = 10,
    ) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "markets": markets,
                    "selection_mode": selection_mode,
                    "auto_limit": auto_limit,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)

    @staticmethod
    def _normalize(markets: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for raw in markets:
            market = str(raw).strip().upper()
            if not market:
                continue
            if not market.startswith("KRW-"):
                raise ValueError(
                    f"Only KRW markets are supported: {market}"
                )
            if market not in seen:
                seen.add(market)
                result.append(market)

        return result
