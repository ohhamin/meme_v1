from backend.app.core.config import AppSettings
from backend.app.services.safety_config import SafetyConfigValidator


def settings(**overrides):
    base = {
        "app_env": "local",
        "api_token": "change-me",
        "trading_enabled": False,
        "live_manual_order_enabled": False,
        "live_auto_order_enabled": False,
        "upbit_live_order_enabled": False,
        "toss_live_order_enabled": False,
    }
    base.update(overrides)
    return AppSettings(_env_file=None, **base)


def test_local_paper_defaults_warn_but_do_not_fail():
    result = SafetyConfigValidator(settings()).validate()
    assert result.ok is True
    assert any("API_TOKEN" in warning for warning in result.warnings)


def test_production_rejects_default_api_token():
    result = SafetyConfigValidator(
        settings(app_env="production")
    ).validate()
    assert result.ok is False
    assert any("API_TOKEN" in error for error in result.errors)


def test_live_manual_gate_requires_global_trading_gate():
    result = SafetyConfigValidator(
        settings(live_manual_order_enabled=True)
    ).validate()
    assert result.ok is False
    assert any("TRADING_ENABLED" in error for error in result.errors)


def test_upbit_live_gate_requires_credentials():
    result = SafetyConfigValidator(
        settings(
            trading_enabled=True,
            live_manual_order_enabled=True,
            upbit_live_order_enabled=True,
            upbit_access_key="",
            upbit_secret_key="",
        )
    ).validate()
    assert result.ok is False
    assert any("Upbit API credentials" in error for error in result.errors)


def test_live_auto_requires_at_least_one_broker_gate():
    result = SafetyConfigValidator(
        settings(
            trading_enabled=True,
            live_auto_order_enabled=True,
        )
    ).validate()
    assert result.ok is False
    assert any("at least one broker" in error for error in result.errors)
