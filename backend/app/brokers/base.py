from abc import ABC, abstractmethod
from typing import Any


class BrokerAdapter(ABC):
    @abstractmethod
    async def get_balance(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_price(self, symbol: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def validate_order(self, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, **kwargs) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_order(self, order_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def is_market_open(self) -> bool:
        raise NotImplementedError
