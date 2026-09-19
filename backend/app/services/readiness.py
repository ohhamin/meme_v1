from backend.app.core.config import get_settings
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.paper_broker import PaperBroker
from backend.app.services.runtime_settings import RuntimeSettingsService
from backend.app.services.toss_universe import TossUniverseService
from backend.app.services.upbit_universe import UpbitUniverseService


class ReadinessService:
    """Explain what is still required before Paper/Live automation can run."""

    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()
        self.live_orders = LiveOrderJournal()

    def status(self) -> dict:
        runtime = self.runtime.get()
        stock_targets = self._stock_targets()
        crypto_targets = self._crypto_targets()

        paper_checks = {
            "openai_api_key": bool(self.config.openai_api_key),
            "decision_targets": bool(stock_targets or crypto_targets),
            "kill_switch_off": not runtime.kill_switch,
        }

        upbit_live_checks = {
            "credentials": bool(
                self.config.upbit_access_key
                and self.config.upbit_secret_key
            ),
            "broker_gate": self.config.upbit_live_order_enabled,
            "targets_or_holdings": bool(crypto_targets),
        }

        toss_live_checks = {
            "credentials": bool(
                self.config.toss_client_id
                and self.config.toss_client_secret
            ),
            "broker_gate": self.config.toss_live_order_enabled,
            "targets_or_holdings": bool(stock_targets),
        }

        common_live_checks = {
            "mode_live": runtime.mode == "live",
            "kill_switch_off": not runtime.kill_switch,
            "trading_enabled": self.config.trading_enabled,
            "no_unresolved_orders": not self.live_orders.unresolved(
                limit=500
            ),
        }

        manual_checks = {
            **common_live_checks,
            "manual_gate": self.config.live_manual_order_enabled,
            "at_least_one_broker": (
                self.config.upbit_live_order_enabled
                or self.config.toss_live_order_enabled
            ),
        }

        auto_checks = {
            **common_live_checks,
            "openai_api_key": bool(self.config.openai_api_key),
            "auto_gate": self.config.live_auto_order_enabled,
            "at_least_one_broker": (
                self.config.upbit_live_order_enabled
                or self.config.toss_live_order_enabled
            ),
            "decision_targets": bool(
                (
                    self.config.upbit_live_order_enabled
                    and crypto_targets
                )
                or (
                    self.config.toss_live_order_enabled
                    and stock_targets
                )
            ),
        }

        return {
            "paper_auto": self._section(paper_checks),
            "live_manual": self._section(manual_checks),
            "live_auto": self._section(auto_checks),
            "brokers": {
                "upbit": self._section(upbit_live_checks),
                "toss": self._section(toss_live_checks),
            },
            "targets": {
                "stock": stock_targets,
                "crypto": crypto_targets,
            },
        }

    def _stock_targets(self) -> list[str]:
        values = list(TossUniverseService().get())
        values.extend(
            position.symbol
            for position in PaperBroker("stock").portfolio().positions
        )
        return list(dict.fromkeys(values))

    def _crypto_targets(self) -> list[str]:
        values = list(UpbitUniverseService().get())
        values.extend(
            position.symbol
            for position in PaperBroker("crypto").portfolio().positions
        )
        return list(dict.fromkeys(values))

    @staticmethod
    def _section(checks: dict[str, bool]) -> dict:
        missing = [
            name
            for name, value in checks.items()
            if not value
        ]
        return {
            "ready": not missing,
            "checks": checks,
            "missing": missing,
        }
