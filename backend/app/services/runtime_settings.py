import json
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models.schemas import RuntimeSettings


class RuntimeSettingsService:
    def __init__(self):
        self.config = get_settings()
        self.path: Path = self.config.data_path / "state" / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _default(self) -> RuntimeSettings:
        return RuntimeSettings(
            mode="paper" if self.config.paper_trading else "live",
            kill_switch=self.config.kill_switch,
            live_order_allowed=False,
            scheduler_enabled=self.config.scheduler_enabled,
        )

    def get(self) -> RuntimeSettings:
        if not self.path.exists():
            state = self._default()
            self._write(state)
            return self._decorate(state)

        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
            migrated = False
            if "scheduler_enabled" not in raw:
                raw["scheduler_enabled"] = self.config.scheduler_enabled
                migrated = True
            state = RuntimeSettings(**raw)
            if migrated:
                self._write(state)
        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            # Corrupted runtime state must fail closed: Paper + Kill switch ON.
            state = RuntimeSettings(
                mode="paper",
                kill_switch=True,
                live_order_allowed=False,
                scheduler_enabled=False,
            )
            self._write(state)

        return self._decorate(state)

    def set_mode(self, mode: str) -> RuntimeSettings:
        state = self.get()
        entering_live = (
            mode == "live"
            and state.mode != "live"
        )
        state.mode = mode

        # Mode selection alone must never arm real ordering. Entering Live
        # always re-engages the Kill switch; the user must disable it in a
        # separate, explicit action after reviewing readiness.
        if entering_live:
            state.kill_switch = True

        self._write(state)
        return self._decorate(state)

    def set_kill_switch(self, enabled: bool) -> RuntimeSettings:
        state = self.get()
        state.kill_switch = enabled
        self._write(state)
        return self._decorate(state)

    def set_scheduler_enabled(self, enabled: bool) -> RuntimeSettings:
        state = self.get()
        state.scheduler_enabled = enabled
        self._write(state)
        return self._decorate(state)

    def _decorate(self, state: RuntimeSettings) -> RuntimeSettings:
        state.live_order_allowed = (
            state.mode == "live"
            and self.config.trading_enabled
            and not state.kill_switch
            and (
                self.config.live_manual_order_enabled
                or self.config.live_auto_order_enabled
            )
            and (
                self.config.upbit_live_order_enabled
                or self.config.toss_live_order_enabled
            )
        )
        return state

    def _write(self, state: RuntimeSettings) -> None:
        payload = state.model_dump()
        payload["live_order_allowed"] = False
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
