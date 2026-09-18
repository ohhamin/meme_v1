from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from backend.app.core.config import get_settings
from backend.app.models.schemas import OrderResult
from backend.app.services.runtime_settings import RuntimeSettingsService


class TradingService:
    def __init__(self):
        self.config = get_settings()
        self.runtime = RuntimeSettingsService()

    def stock_positions(self) -> list[dict]:
        # TODO: 국내주식 Broker Adapter 연결
        return []

    def crypto_positions(self) -> list[dict]:
        # TODO: Upbit Adapter 연결
        return []

    def manual_stock_order(self, symbol: str, side: str, quantity: int) -> OrderResult:
        return self._manual_order(
            symbol=symbol,
            side=side,
            description=f"{quantity}주",
        )

    def manual_crypto_order(self, symbol: str, side: str, amount_krw) -> OrderResult:
        return self._manual_order(
            symbol=symbol,
            side=side,
            description=f"{amount_krw} KRW",
        )

    def _manual_order(self, symbol: str, side: str, description: str) -> OrderResult:
        runtime = self.runtime.get()

        if runtime.kill_switch:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Kill switch is enabled. New orders are blocked.",
            )

        now = datetime.now(timezone.utc)

        if runtime.mode == "paper":
            return OrderResult(
                order_id=f"paper-{uuid4().hex[:12]}",
                symbol=symbol,
                side=side,
                status="paper_filled",
                message=f"Paper order simulated: {description}",
                created_at=now,
            )

        if not self.config.trading_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Live mode is selected, but TRADING_ENABLED=false.",
            )

        # 실제 Adapter 연결 전에는 절대로 주문하지 않는다.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Live broker adapter is not implemented yet.",
        )
