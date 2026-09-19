from backend.app.services.decision_universe import merge_decision_universe


def test_merge_decision_universe_keeps_configured_order_and_adds_holdings():
    result = merge_decision_universe(
        ["KRW-ETH", "krw-btc"],
        ["KRW-BTC", "KRW-XRP"],
    )

    assert result == [
        "KRW-ETH",
        "KRW-BTC",
        "KRW-XRP",
    ]


def test_merge_decision_universe_allows_holdings_only():
    assert merge_decision_universe(
        [],
        ["005930"],
    ) == ["005930"]
