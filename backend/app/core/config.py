from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_env: str = "local"
    app_timezone: str = "Asia/Seoul"
    api_token: str = "change-me"
    data_dir: str = "data"

    paper_trading: bool = True
    trading_enabled: bool = False
    kill_switch: bool = True

    # Deterministic Risk Guard hard limits.
    # Risk Guard does not decide BUY/SELL; it only permits or blocks an order intent.
    risk_max_position_pct: float = 10.0
    risk_max_market_exposure_pct: float = 60.0
    risk_max_single_order_pct: float = 5.0
    risk_max_daily_loss_pct: float = 3.0
    risk_max_daily_orders: int = 20
    risk_max_data_age_seconds: int = 300
    risk_min_cash_reserve_pct: float = 10.0

    decision_default_interval_minutes: int = 60
    decision_min_interval_minutes: int = 30
    decision_max_interval_minutes: int = 120
    news_collection_interval_hours: int = 6
    news_web_search_enabled: bool = True
    news_max_output_tokens: int = 2500
    scheduler_enabled: bool = False

    openai_api_key: str = ""
    openai_decision_model: str = "gpt-5.6-terra"
    openai_summary_model: str = "gpt-5.6-luna"
    openai_reasoning_effort: str = "low"
    openai_max_output_tokens: int = 4000
    llm_enabled: bool = True
    llm_daily_token_budget: int = 200000
    llm_cycle_input_token_limit: int = 8000
    llm_context_news_chars: int = 12000
    llm_context_decision_chars: int = 6000
    llm_conserve_threshold_pct: int = 20
    algorithm_review_interval_hours: int = 24

    upbit_access_key: str = ""
    upbit_secret_key: str = ""

    korea_broker_app_key: str = ""
    korea_broker_app_secret: str = ""
    korea_broker_account_no: str = ""

    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    fcm_device_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    def clamp_decision_interval(self, minutes: int) -> int:
        return max(
            self.decision_min_interval_minutes,
            min(minutes, self.decision_max_interval_minutes),
        )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
