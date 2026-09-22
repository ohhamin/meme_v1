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
    live_manual_order_enabled: bool = False
    live_auto_order_enabled: bool = False
    upbit_live_order_enabled: bool = False
    toss_live_order_enabled: bool = False
    toss_confirm_high_value_orders: bool = False
    toss_high_value_order_threshold_krw: int = 100000000
    live_order_reconcile_attempts: int = 3
    live_order_reconcile_interval_seconds: float = 1.0

    risk_max_position_pct: float = 60.0
    risk_max_daily_loss_pct: float = 3.0
    risk_max_daily_orders: int = 20
    risk_max_data_age_seconds: int = 300
    risk_min_cash_reserve_pct: float = 10.0
    risk_max_portfolio_exposure_pct: float = 90.0
    risk_max_open_positions: int = 10
    risk_auto_symbol_cooldown_minutes: int = 60
    risk_sell_reentry_cooldown_minutes: int = 60
    risk_stop_reentry_cooldown_minutes: int = 180
    # Stock protective exits
    risk_hard_stop_loss_pct: float = 5.0
    risk_trailing_activation_pct: float = 10.0
    risk_trailing_stop_pct: float = 5.0

    # Crypto gets wider loss tolerance and earlier profit protection.
    risk_crypto_hard_stop_loss_pct: float = 7.0
    risk_crypto_trailing_activation_pct: float = 7.0
    risk_crypto_trailing_min_pct: float = 4.0
    risk_crypto_trailing_max_pct: float = 7.0
    risk_crypto_trailing_vol_multiplier: float = 1.25
    risk_monitor_interval_minutes: int = 5
    risk_buy_kill_switch: bool = False

    position_buy_min_score: int = 60
    position_sell_max_score: int = 40
    position_buy_pct_score_60: float = 5.0
    position_buy_pct_score_70: float = 10.0
    position_buy_pct_score_80: float = 15.0
    position_buy_pct_score_90: float = 20.0
    position_sell_pct_score_40: float = 25.0
    position_sell_pct_score_30: float = 40.0
    position_sell_pct_score_20: float = 60.0
    position_regime_bull_min_score: int = 60
    position_regime_bear_max_score: int = 40
    position_regime_threshold_shift: int = 5
    position_target_exposure_bull_pct: float = 80.0
    position_target_exposure_neutral_pct: float = 60.0
    position_target_exposure_bear_pct: float = 35.0

    paper_stock_initial_cash_krw: float = 1000000.0
    paper_crypto_initial_cash_krw: float = 1000000.0
    paper_fee_bps: float = 0.0
    paper_slippage_bps: float = 0.0

    decision_default_interval_minutes: int = 60
    decision_stock_universe_limit: int = 25
    decision_crypto_universe_limit: int = 20
    decision_min_interval_minutes: int = 30
    decision_max_interval_minutes: int = 120
    news_collection_interval_hours: int = 12
    news_web_search_enabled: bool = True
    news_max_output_tokens: int = 2500
    fred_api_key: str = ""
    fred_api_base_url: str = "https://api.stlouisfed.org/fred"
    macro_context_max_age_hours: int = 48
    krx_api_key: str = ""
    krx_api_base_url: str = "https://data-dbg.krx.co.kr/svc/apis"
    krx_http_timeout_seconds: float = 8.0
    scheduler_enabled: bool = False
    data_retention_days: int = 7
    idempotency_retention_days: int = 30
    startup_push_enabled: bool = False

    openai_api_key: str = ""
    openai_admin_key: str = ""
    openai_project_id: str = ""
    openai_decision_model: str = "gpt-5.6-terra"
    openai_summary_model: str = "gpt-5.6-luna"
    openai_reasoning_effort: str = "low"
    openai_max_output_tokens: int = 8000
    llm_enabled: bool = True
    llm_daily_token_budget: int = 2000000
    llm_cycle_input_token_limit: int = 12000
    llm_context_news_chars: int = 12000
    llm_context_decision_chars: int = 6000
    llm_conserve_threshold_pct: int = 20
    algorithm_review_interval_hours: int = 24
    algorithm_review_min_decisions: int = 20

    upbit_access_key: str = ""
    upbit_secret_key: str = ""
    upbit_api_base_url: str = "https://api.upbit.com/v1"
    upbit_decision_markets: str = ""
    upbit_http_timeout_seconds: float = 8.0

    toss_client_id: str = ""
    toss_client_secret: str = ""
    toss_api_base_url: str = "https://openapi.tossinvest.com"
    toss_account_seq: int | None = None
    toss_decision_symbols: str = ""
    toss_http_timeout_seconds: float = 8.0

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

    @property
    def toss_decision_symbol_list(self) -> list[str]:
        return [value.strip().upper() for value in self.toss_decision_symbols.split(",") if value.strip()]

    @property
    def upbit_decision_market_list(self) -> list[str]:
        return [value.strip().upper() for value in self.upbit_decision_markets.split(",") if value.strip()]

    def clamp_decision_interval(self, minutes: int) -> int:
        return max(self.decision_min_interval_minutes, min(minutes, self.decision_max_interval_minutes))


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
