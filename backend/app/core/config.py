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

    decision_default_interval_minutes: int = 60
    decision_min_interval_minutes: int = 30
    decision_max_interval_minutes: int = 120
    news_collection_interval_hours: int = 6
    scheduler_enabled: bool = False

    openai_api_key: str = ""

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
