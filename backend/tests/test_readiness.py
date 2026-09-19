from backend.app.services.readiness import ReadinessService


def test_readiness_defaults_keep_live_disabled(monkeypatch, tmp_path):
    service = ReadinessService()

    service.runtime.path = tmp_path / "settings.json"
    service.live_orders.base_dir = tmp_path / "live_orders"
    service.live_orders.base_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        service,
        "_stock_targets",
        lambda: ["005930"],
    )
    monkeypatch.setattr(
        service,
        "_crypto_targets",
        lambda: ["KRW-BTC"],
    )

    result = service.status()

    assert result["live_manual"]["ready"] is False
    assert result["live_auto"]["ready"] is False
    assert result["brokers"]["upbit"]["ready"] is False
    assert result["brokers"]["toss"]["ready"] is False


def test_readiness_section_lists_missing_checks():
    value = ReadinessService._section(
        {
            "a": True,
            "b": False,
            "c": False,
        }
    )

    assert value["ready"] is False
    assert value["missing"] == ["b", "c"]
