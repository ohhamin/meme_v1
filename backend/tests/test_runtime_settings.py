import json

from backend.app.services.runtime_settings import RuntimeSettingsService


def make_service(tmp_path):
    service = RuntimeSettingsService()
    service.path = tmp_path / "settings.json"
    return service


def test_corrupted_runtime_settings_fail_closed(tmp_path):
    service = make_service(tmp_path)
    service.path.write_text(
        "{not-json",
        encoding="utf-8",
    )

    state = service.get()

    assert state.mode == "paper"
    assert state.kill_switch is True
    assert state.live_order_allowed is False

    persisted = json.loads(
        service.path.read_text(encoding="utf-8")
    )
    assert persisted["mode"] == "paper"
    assert persisted["kill_switch"] is True


def test_invalid_runtime_settings_fail_closed(tmp_path):
    service = make_service(tmp_path)
    service.path.write_text(
        json.dumps(
            {
                "mode": "invalid",
                "kill_switch": False,
                "live_order_allowed": True,
            }
        ),
        encoding="utf-8",
    )

    state = service.get()

    assert state.mode == "paper"
    assert state.kill_switch is True
    assert state.live_order_allowed is False
