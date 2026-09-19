import json
from pathlib import Path

from backend.app.core.config import get_settings


class TossUniverseService:
    """Persist Korean stock decision universe locally."""

    def __init__(self):
        self.config = get_settings()
        self.path: Path = (
            self.config.data_path
            / "state"
            / "toss_universe.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> list[str]:
        if not self.path.exists():
            initial = self._normalize(
                self.config.toss_decision_symbol_list
            )
            self._write(initial)
            return initial

        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            values = raw.get("symbols", [])
            if not isinstance(values, list):
                raise ValueError("invalid symbols")
            return self._normalize(values)
        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            initial = self._normalize(
                self.config.toss_decision_symbol_list
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
            return max(1, min(int(raw.get("auto_limit") or 15), 30))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 15

    def set(self, symbols: list[str]) -> list[str]:
        return self.set_manual(symbols)

    def set_manual(self, symbols: list[str]) -> list[str]:
        normalized = self._normalize(symbols)
        self._write(
            normalized,
            selection_mode="manual",
            auto_limit=self.auto_limit(),
        )
        return normalized

    def set_auto(self, symbols: list[str], *, limit: int) -> list[str]:
        normalized = self._normalize(symbols)
        self._write(
            normalized,
            selection_mode="auto",
            auto_limit=max(1, min(limit, 30)),
        )
        return normalized

    def _write(
        self,
        symbols: list[str],
        *,
        selection_mode: str = "manual",
        auto_limit: int = 15,
    ) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "symbols": symbols,
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
    def _normalize(symbols: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for raw in symbols:
            symbol = str(raw).strip().upper()
            if not symbol:
                continue
            if len(symbol) != 6 or not symbol.isdigit():
                raise ValueError(
                    f"Only 6-digit Korean stock symbols are supported: {symbol}"
                )
            if symbol not in seen:
                seen.add(symbol)
                result.append(symbol)

        if len(result) > 200:
            raise ValueError(
                "Decision universe supports up to 200 stock symbols."
            )

        return result
