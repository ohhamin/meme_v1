from decimal import Decimal

from backend.app.models.schemas import MarketInstrumentSnapshot
from backend.app.services.paper_broker import PaperBroker


def make_broker(tmp_path) -> PaperBroker:
    broker = PaperBroker("crypto")
    broker.path = tmp_path / "paper_portfolio.json"
    broker.audit.write = lambda *args, **kwargs: None
    broker.push.send = lambda *args, **kwargs: None
    broker.config.paper_crypto_initial_cash_krw = 1000000
    broker.config.paper_fee_bps = 0
    broker.config.paper_slippage_bps = 0
    broker.reset(Decimal("1000000"))
    return broker


def test_buy_updates_cash_and_position(tmp_path):
    broker = make_broker(tmp_path)

    order = broker.execute(
        symbol="BTC",
        name="Bitcoin",
        side="buy",
        quantity=Decimal("0.001"),
        market_price=Decimal("100000000"),
        decision_score=85,
    )

    portfolio = broker.portfolio()
    assert order.notional == Decimal("100000.000")
    assert portfolio.cash == Decimal("900000.000")
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].quantity == Decimal("0.001")
    assert portfolio.daily_order_count == 1


def test_sell_reduces_position_and_increases_cash(tmp_path):
    broker = make_broker(tmp_path)
    broker.execute(
        symbol="BTC",
        name="Bitcoin",
        side="buy",
        quantity=Decimal("0.001"),
        market_price=Decimal("100000000"),
    )

    broker.execute(
        symbol="BTC",
        name="Bitcoin",
        side="sell",
        quantity=Decimal("0.0004"),
        market_price=Decimal("110000000"),
    )

    portfolio = broker.portfolio()
    assert portfolio.positions[0].quantity == Decimal("0.0006")
    assert portfolio.cash == Decimal("944000.0000")
    assert portfolio.daily_order_count == 2


def test_update_prices_marks_portfolio_to_market(tmp_path):
    broker = make_broker(tmp_path)
    broker.execute(
        symbol="BTC",
        name="Bitcoin",
        side="buy",
        quantity=Decimal("0.001"),
        market_price=Decimal("100000000"),
    )

    broker.update_prices(
        [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol="BTC",
                name="Bitcoin",
                price=Decimal("120000000"),
            )
        ]
    )

    portfolio = broker.portfolio()
    position = portfolio.positions[0]
    assert position.market_value == Decimal("120000.000")
    assert position.return_rate == Decimal("20.0")
    assert portfolio.equity == Decimal("1020000.000")



def test_update_prices_preserves_snapshot_age(tmp_path):
    broker = make_broker(tmp_path)
    broker.execute(
        symbol="BTC",
        name="Bitcoin",
        side="buy",
        quantity=Decimal("0.001"),
        market_price=Decimal("100000000"),
    )

    broker.update_prices(
        [
            MarketInstrumentSnapshot(
                market="crypto",
                symbol="BTC",
                name="Bitcoin",
                price=Decimal("100000000"),
                data_age_seconds=600,
            )
        ]
    )

    position = broker.portfolio().positions[0]
    age = broker.config.risk_max_data_age_seconds
    assert position.last_price_at is not None

    from datetime import datetime

    now = datetime.now(position.last_price_at.tzinfo)
    observed_age = int(
        (now - position.last_price_at).total_seconds()
    )
    assert 598 <= observed_age <= 602
