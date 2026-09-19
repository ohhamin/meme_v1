from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.app.services.auto_trade_activity import AutoTradeActivityService


def test_auto_trade_activity_round_trip(tmp_path):
    service = AutoTradeActivityService()
    service.path = tmp_path / "activity.json"
    tz = ZoneInfo(service.config.app_timezone)
    now = datetime.now(tz)
    before = now - timedelta(minutes=30)

    service.record(
        mode="paper",
        market="crypto",
        symbol="KRW-BTC",
        at=before,
    )

    age = service.seconds_since_last(
        mode="paper",
        market="crypto",
        symbol="krw-btc",
        now=now,
    )

    assert age is not None
    assert 1799 <= age <= 1801


def test_auto_trade_activity_separates_paper_and_live(tmp_path):
    service = AutoTradeActivityService()
    service.path = tmp_path / "activity.json"

    service.record(
        mode="paper",
        market="stock",
        symbol="005930",
    )

    assert service.seconds_since_last(
        mode="paper",
        market="stock",
        symbol="005930",
    ) is not None
    assert service.seconds_since_last(
        mode="live",
        market="stock",
        symbol="005930",
    ) is None
