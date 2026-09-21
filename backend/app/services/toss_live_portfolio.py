from backend.app.brokers.toss_account import TossAccountAdapter


class TossLivePortfolioService:
    """Read-only Korean stock portfolio view from Toss holdings."""

    def __init__(self):
        self.accounts = TossAccountAdapter()

    async def positions(self) -> list[dict]:
        status = await self.accounts.status()

        if not status.configured:
            return []

        return [
            {
                "symbol": item.symbol,
                "name": item.name,
                "invested_amount": item.purchase_amount,
                "average_price": item.average_purchase_price,
                "quantity": item.quantity,
                "return_rate": item.return_rate,
                "decision_score": None,
                "current_price": item.last_price,
                "market_value": item.market_value,
                "source": "toss_live",
            }
            for item in status.holdings
        ]
