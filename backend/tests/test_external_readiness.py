import asyncio
from types import SimpleNamespace

from backend.app.services.external_readiness import ExternalReadinessService


def test_external_readiness_public_upbit_check(monkeypatch):
    service = ExternalReadinessService()

    async def fake_quotes(markets):
        assert markets == ["KRW-BTC"]
        return [SimpleNamespace(market="KRW-BTC")]

    monkeypatch.setattr(
        service.upbit_market,
        "quotes",
        fake_quotes,
    )

    result = asyncio.run(service._upbit_public())

    assert result["status"] == "ok"


def test_external_readiness_unconfigured_private_brokers():
    service = ExternalReadinessService()
    old_upbit_access = service.config.upbit_access_key
    old_upbit_secret = service.config.upbit_secret_key
    old_toss_id = service.config.toss_client_id
    old_toss_secret = service.config.toss_client_secret

    try:
        service.config.upbit_access_key = ""
        service.config.upbit_secret_key = ""
        service.config.toss_client_id = ""
        service.config.toss_client_secret = ""

        upbit = asyncio.run(service._upbit_account())
        toss = asyncio.run(service._toss_account())

        assert upbit["status"] == "not_configured"
        assert toss["status"] == "not_configured"
    finally:
        service.config.upbit_access_key = old_upbit_access
        service.config.upbit_secret_key = old_upbit_secret
        service.config.toss_client_id = old_toss_id
        service.config.toss_client_secret = old_toss_secret


def test_external_readiness_never_reports_mutation(monkeypatch):
    service = ExternalReadinessService()

    async def fake_upbit_public():
        return {"status": "ok", "configured": True}

    async def fake_upbit_account():
        return {"status": "not_configured", "configured": False}

    async def fake_toss_account():
        return {"status": "not_configured", "configured": False}

    monkeypatch.setattr(service, "_upbit_public", fake_upbit_public)
    monkeypatch.setattr(service, "_upbit_account", fake_upbit_account)
    monkeypatch.setattr(service, "_toss_account", fake_toss_account)

    result = asyncio.run(service.check())

    assert result["mutation_performed"] is False
