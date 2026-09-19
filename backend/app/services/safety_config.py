from dataclasses import dataclass, field

from backend.app.core.config import AppSettings, get_settings


@dataclass
class SafetyValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class SafetyConfigValidator:
    """Fail startup on production/live configurations that are unsafe by construction."""

    def __init__(self, config: AppSettings | None = None):
        self.config = config or get_settings()

    def validate(self) -> SafetyValidationResult:
        c = self.config
        result = SafetyValidationResult()

        env = c.app_env.strip().lower()
        non_local = env != "local"

        if non_local and (
            not c.api_token
            or c.api_token == "change-me"
            or len(c.api_token) < 24
        ):
            result.errors.append(
                "Production API_TOKEN must be changed and be at least 24 characters."
            )

        if c.live_manual_order_enabled or c.live_auto_order_enabled:
            if not c.trading_enabled:
                result.errors.append(
                    "Live order gates require TRADING_ENABLED=true."
                )

        if c.live_auto_order_enabled and not (
            c.upbit_live_order_enabled
            or c.toss_live_order_enabled
        ):
            result.errors.append(
                "LIVE_AUTO_ORDER_ENABLED requires at least one broker live-order gate."
            )

        if c.upbit_live_order_enabled and not (
            c.upbit_access_key and c.upbit_secret_key
        ):
            result.errors.append(
                "UPBIT_LIVE_ORDER_ENABLED requires Upbit API credentials."
            )

        if c.toss_live_order_enabled and not (
            c.toss_client_id and c.toss_client_secret
        ):
            result.errors.append(
                "TOSS_LIVE_ORDER_ENABLED requires Toss OAuth credentials."
            )

        if c.risk_max_open_positions < 1:
            result.errors.append(
                "RISK_MAX_OPEN_POSITIONS must be at least 1."
            )

        if not 0 < c.risk_max_position_pct <= 100:
            result.errors.append(
                "RISK_MAX_POSITION_PCT must be between 0 and 100."
            )

        if not 0 <= c.risk_min_cash_reserve_pct < 100:
            result.errors.append(
                "RISK_MIN_CASH_RESERVE_PCT must be between 0 and 100."
            )

        if c.decision_min_interval_minutes < 30:
            result.warnings.append(
                "Decision interval below 30 minutes conflicts with current operating policy."
            )

        if not non_local and c.api_token == "change-me":
            result.warnings.append(
                "API_TOKEN is still the local development default."
            )

        return result

    def require_safe_startup(self) -> SafetyValidationResult:
        result = self.validate()
        if result.errors:
            raise RuntimeError(
                "Unsafe configuration: " + " | ".join(result.errors)
            )
        return result
