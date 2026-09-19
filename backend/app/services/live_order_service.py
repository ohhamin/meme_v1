import asyncio
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from fastapi import HTTPException, status

from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_order import TossOrderAdapter
from backend.app.brokers.upbit_order import UpbitOrderAdapter
from backend.app.brokers.upbit_private import UpbitPrivateRequestError
from backend.app.models.schemas import (
    LiveOrderExecutionResult,
    LiveOrderRecord,
    OrderResult,
    RiskOrderIntent,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.idempotency import IdempotencyStore
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.live_risk_snapshot import (
    LiveRiskSnapshotError,
    LiveRiskSnapshotService,
)
from backend.app.services.push import PushService
from backend.app.services.risk_guard import RiskGuard
from backend.app.services.runtime_settings import RuntimeSettingsService


class LiveOrderService:
    """Manual live-order orchestration with durable intent-before-mutation safety."""

    def __init__(self):
        self.runtime = RuntimeSettingsService()
        self.config = self.runtime.config
        self.risk = RiskGuard()
        self.snapshots = LiveRiskSnapshotService()
        self.journal = LiveOrderJournal()
        self.idempotency = IdempotencyStore()
        self.upbit = UpbitOrderAdapter()
        self.toss = TossOrderAdapter()
        self.audit = AuditLogger()
        self.push = PushService()

    def enablement(self) -> dict:
        return {
            "trading_enabled": self.config.trading_enabled,
            "live_manual_order_enabled": self.config.live_manual_order_enabled,
            "live_auto_order_enabled": self.config.live_auto_order_enabled,
            "upbit_live_order_enabled": self.config.upbit_live_order_enabled,
            "toss_live_order_enabled": self.config.toss_live_order_enabled,
        }

    async def manual_stock_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        idempotency_key: str,
    ) -> OrderResult:
        self._require_live_manual("toss")
        self.idempotency.ensure_new(idempotency_key)

        try:
            snap = await self.snapshots.toss(symbol)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Live Toss snapshot unavailable: {exc}",
            ) from exc

        qty = Decimal(quantity)
        notional = qty * snap["price"]
        return await self._execute(
            broker="toss",
            source="manual",
            symbol=snap["symbol"],
            side=side,
            quantity=qty,
            notional=notional,
            snapshot=snap,
            idempotency_key=idempotency_key,
        )

    async def manual_crypto_order(
        self,
        *,
        symbol: str,
        side: str,
        amount_krw,
        idempotency_key: str,
    ) -> OrderResult:
        self._require_live_manual("upbit")
        self.idempotency.ensure_new(idempotency_key)

        try:
            snap = await self.snapshots.upbit(symbol)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Live Upbit snapshot unavailable: {exc}",
            ) from exc

        amount = Decimal(str(amount_krw))
        if side == "buy":
            notional = amount
            quantity = (
                amount / snap["price"]
            ).quantize(
                Decimal("0.00000001"),
                rounding=ROUND_DOWN,
            )
        elif side == "sell":
            quantity = (
                amount / snap["price"]
            ).quantize(
                Decimal("0.00000001"),
                rounding=ROUND_DOWN,
            )
            notional = quantity * snap["price"]
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="side must be buy or sell",
            )

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Calculated crypto quantity is zero.",
            )

        return await self._execute(
            broker="upbit",
            source="manual",
            symbol=snap["symbol"],
            side=side,
            quantity=quantity,
            notional=notional,
            snapshot=snap,
            idempotency_key=idempotency_key,
        )

    async def auto_order(
        self,
        *,
        market: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
    ) -> OrderResult:
        broker = "upbit" if market == "crypto" else "toss"
        self._require_live_auto(broker)

        try:
            snapshot = (
                await self.snapshots.upbit(symbol)
                if broker == "upbit"
                else await self.snapshots.toss(symbol)
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Live broker snapshot unavailable: {exc}",
            ) from exc

        return await self._execute(
            broker=broker,
            source="auto",
            symbol=snapshot["symbol"],
            side=side,
            quantity=quantity,
            notional=notional,
            snapshot=snapshot,
            idempotency_key=(
                f"auto-{broker}-{uuid4().hex}"
            ),
        )

    def _require_live_manual(self, broker: str) -> None:
        runtime = self.runtime.get()
        reasons: list[str] = []

        if runtime.mode != "live":
            reasons.append("Runtime mode is not live.")
        if runtime.kill_switch:
            reasons.append("Kill switch is enabled.")
        if not self.config.trading_enabled:
            reasons.append("TRADING_ENABLED=false.")
        if not self.config.live_manual_order_enabled:
            reasons.append("LIVE_MANUAL_ORDER_ENABLED=false.")
        if broker == "upbit" and not self.config.upbit_live_order_enabled:
            reasons.append("UPBIT_LIVE_ORDER_ENABLED=false.")
        if broker == "toss" and not self.config.toss_live_order_enabled:
            reasons.append("TOSS_LIVE_ORDER_ENABLED=false.")

        if reasons:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": "Live order is disabled by safety gates.",
                    "reasons": reasons,
                },
            )

    def _require_live_auto(self, broker: str) -> None:
        runtime = self.runtime.get()
        reasons: list[str] = []

        if runtime.mode != "live":
            reasons.append("Runtime mode is not live.")
        if runtime.kill_switch:
            reasons.append("Kill switch is enabled.")
        if not self.config.trading_enabled:
            reasons.append("TRADING_ENABLED=false.")
        if not self.config.live_auto_order_enabled:
            reasons.append("LIVE_AUTO_ORDER_ENABLED=false.")
        if broker == "upbit" and not self.config.upbit_live_order_enabled:
            reasons.append("UPBIT_LIVE_ORDER_ENABLED=false.")
        if broker == "toss" and not self.config.toss_live_order_enabled:
            reasons.append("TOSS_LIVE_ORDER_ENABLED=false.")

        if reasons:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": "Live auto order is disabled by safety gates.",
                    "reasons": reasons,
                },
            )

    async def _execute(
        self,
        *,
        broker: str,
        source: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        notional: Decimal,
        snapshot: dict,
        idempotency_key: str,
    ) -> OrderResult:
        if self.journal.has_unresolved(
            broker=broker,
            symbol=symbol,
        ):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": (
                        "Another unresolved live order exists for this symbol."
                    ),
                    "broker": broker,
                    "symbol": symbol,
                },
            )

        action = "BUY" if side == "buy" else "SELL"

        intent = RiskOrderIntent(
            source=source,
            market=snapshot["market"],
            symbol=symbol,
            action=action,
            order_notional=notional,
            order_quantity=quantity,
            price=snapshot["price"],
            portfolio_equity=snapshot["portfolio_equity"],
            available_cash=snapshot["available_cash"],
            position_value=snapshot["position_value"],
            position_quantity=snapshot["position_quantity"],
            open_position_count=snapshot["open_position_count"],
            daily_pnl_pct=snapshot["daily_pnl_pct"],
            daily_order_count=snapshot["daily_order_count"],
            data_age_seconds=snapshot["data_age_seconds"],
            market_open=snapshot["market_open"],
            same_cycle_duplicate=False,
        )
        risk = self.risk.evaluate(intent)

        record = self.journal.create(
            broker=broker,
            source=source,
            market=snapshot["market"],
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            reference_price=snapshot["price"],
        )
        # Reserve the user request key before any external mutation. A retry
        # after an ambiguous outcome must never submit another order.
        self.idempotency.remember(
            idempotency_key,
            record.intent_id,
        )

        if risk.status != "PASS":
            record = self.journal.update(
                record.intent_id,
                status="REJECTED",
                reason=" | ".join(risk.reasons),
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": "Risk Guard blocked the live order.",
                    "intent_id": record.intent_id,
                    "reasons": risk.reasons,
                },
            )

        adapter = self.upbit if broker == "upbit" else self.toss
        preflight = await adapter.preflight(
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            **(
                {"identifier": record.client_order_id}
                if broker == "upbit"
                else {"client_order_id": record.client_order_id}
            ),
        )

        if not preflight.allowed:
            record = self.journal.update(
                record.intent_id,
                status="REJECTED",
                reason=" | ".join(preflight.reasons),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Broker preflight rejected the live order.",
                    "intent_id": record.intent_id,
                    "reasons": preflight.reasons,
                },
            )

        self.journal.update(
            record.intent_id,
            status="PREFLIGHTED",
        )
        self.journal.update(
            record.intent_id,
            status="SUBMITTING",
        )

        try:
            if broker == "upbit":
                response = await self.upbit.submit_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    notional=notional,
                    identifier=record.client_order_id,
                )
                order_id = str(response.get("uuid") or "")
                broker_status = str(response.get("state") or "submitted")
            else:
                response = await self.toss.submit_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    client_order_id=record.client_order_id,
                )
                result = response.get("result") or {}
                order_id = str(result.get("orderId") or "")
                broker_status = "submitted"

            if not order_id:
                record = self.journal.update(
                    record.intent_id,
                    status="UNKNOWN",
                    reason="Broker accepted response without order id.",
                )
                self._notify_unknown(record)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "message": (
                            "Live order outcome is unknown. "
                            "Do not retry manually with the same intent."
                        ),
                        "intent_id": record.intent_id,
                    },
                )

            record = self.journal.update(
                record.intent_id,
                status="SUBMITTED",
                broker_order_id=order_id,
                broker_status=broker_status,
            )
            self.audit.write(
                "orders",
                {
                    "event": "live_order_submitted",
                    "intent_id": record.intent_id,
                    "broker": broker,
                    "broker_order_id": order_id,
                    "client_order_id": record.client_order_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": str(quantity),
                    "notional": str(notional),
                },
            )
            self.push.send(
                title="Live 주문 접수",
                body=f"{symbol} {side.upper()}",
                data={
                    "type": "live_order_submitted",
                    "intent_id": record.intent_id,
                    "broker": broker,
                },
            )

            return OrderResult(
                order_id=order_id,
                symbol=symbol,
                side=side,
                status="submitted",
                message=(
                    f"Live order submitted. intent_id={record.intent_id}"
                ),
                created_at=record.updated_at,
            )

        except HTTPException:
            raise
        except (UpbitPrivateRequestError, TossApiError) as exc:
            ambiguous = bool(getattr(exc, "ambiguous", False))
            record = self.journal.update(
                record.intent_id,
                status="UNKNOWN" if ambiguous else "REJECTED",
                reason=str(exc),
            )

            if ambiguous and broker == "upbit":
                record = await self._try_reconcile_upbit(record)

            if record.status == "SUBMITTED":
                return OrderResult(
                    order_id=record.broker_order_id or record.intent_id,
                    symbol=symbol,
                    side=side,
                    status="submitted",
                    message=(
                        "Live order was recovered by broker lookup after "
                        "an ambiguous submit response."
                    ),
                    created_at=record.updated_at,
                )

            if ambiguous:
                self._notify_unknown(record)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "message": (
                            "Live order outcome is unknown. "
                            "The system will not resubmit it."
                        ),
                        "intent_id": record.intent_id,
                    },
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Broker rejected the live order.",
                    "intent_id": record.intent_id,
                    "reason": str(exc),
                },
            ) from exc

    async def _try_reconcile_upbit(
        self,
        record: LiveOrderRecord,
    ) -> LiveOrderRecord:
        attempts = max(
            1,
            self.config.live_order_reconcile_attempts,
        )
        for attempt in range(attempts):
            if attempt > 0:
                await asyncio.sleep(
                    max(
                        0.1,
                        self.config.live_order_reconcile_interval_seconds,
                    )
                )
            try:
                order = await self.upbit.get_order(
                    identifier=record.client_order_id
                )
            except UpbitPrivateRequestError:
                continue

            order_id = str(order.get("uuid") or "")
            broker_status = str(order.get("state") or "")
            if order_id:
                return self.journal.update(
                    record.intent_id,
                    status=(
                        "CONFIRMED"
                        if broker_status in {"done", "cancel"}
                        else "SUBMITTED"
                    ),
                    broker_order_id=order_id,
                    broker_status=broker_status,
                    reason="Recovered by identifier lookup.",
                )
        return record

    def _notify_unknown(
        self,
        record: LiveOrderRecord,
    ) -> None:
        self.audit.write(
            "orders",
            {
                "event": "live_order_unknown",
                "intent_id": record.intent_id,
                "broker": record.broker,
                "symbol": record.symbol,
                "side": record.side,
                "client_order_id": record.client_order_id,
                "reason": record.reason,
            },
        )
        self.push.send(
            title="Live 주문 상태 확인 필요",
            body=f"{record.symbol} {record.side.upper()} · 자동 재주문 안 함",
            data={
                "type": "live_order_unknown",
                "intent_id": record.intent_id,
                "broker": record.broker,
            },
        )
