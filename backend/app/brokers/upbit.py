from backend.app.brokers.base import BrokerAdapter


class UpbitAdapter(BrokerAdapter):
    async def get_balance(self):
        raise NotImplementedError

    async def get_positions(self):
        raise NotImplementedError

    async def get_price(self, symbol: str):
        raise NotImplementedError

    async def validate_order(self, **kwargs):
        raise NotImplementedError

    async def place_order(self, **kwargs):
        raise NotImplementedError

    async def get_order(self, order_id: str):
        raise NotImplementedError

    async def is_market_open(self) -> bool:
        return True
