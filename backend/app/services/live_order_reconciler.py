from backend.app.brokers.toss_client import TossApiError
from backend.app.brokers.toss_order import TossOrderAdapter
from backend.app.brokers.upbit_order import UpbitOrderAdapter
from backend.app.brokers.upbit_private import UpbitPrivateRequestError
from backend.app.models.schemas import (
    LiveOrderRecord,
    LiveOrderReconcileResponse,
)
from backend.app.services.audit import AuditLogger
from backend.app.services.live_order_journal import LiveOrderJournal
from backend.app.services.push import PushService
from backend.app.services.auto_trade_activity import AutoTradeActivityService


class LiveOrderReconciler:
    """Queries broker order status without ever resubmitting an order."""

    def __init__(self):
        self.journal = LiveOrderJournal()
        self.upbit = UpbitOrderAdapter()
        self.toss = TossOrderAdapter()
        self.audit = AuditLogger()
        self.push = PushService()
        self.auto_activity = AutoTradeActivityService()

    async def reconcile(
        self,
        *,
        intent_id: str | None = None,
        limit: int = 100,
    ) -> LiveOrderReconcileResponse:
        records = (
            [self.journal.get(intent_id)]
            if intent_id
            else self.journal.unresolved(limit=limit)
        )

        updated = 0
        result: list[LiveOrderRecord] = []

        for record in records:
            before = record.status
            record = await self._one(record)
            if record.status != before:
                updated += 1
            result.append(record)

        unresolved = sum(
            1
            for record in result
            if record.status in {
                "SUBMITTING",
                "SUBMITTED",
                "UNKNOWN",
            }
        )

        return LiveOrderReconcileResponse(
            updated=updated,
            unresolved=unresolved,
            records=result,
        )

    async def _one(
        self,
        record: LiveOrderRecord,
    ) -> LiveOrderRecord:
        try:
            if record.broker == "upbit":
                order = await self.upbit.get_order(
                    order_id=record.broker_order_id,
                    identifier=(
                        None
                        if record.broker_order_id
                        else record.client_order_id
                    ),
                )
                order_id = str(order.get("uuid") or "")
                broker_status = str(order.get("state") or "")
                if not order_id:
                    return record

                status = (
                    "CONFIRMED"
                    if broker_status in {"done", "cancel"}
                    else "SUBMITTED"
                )
                return self._save(
                    record,
                    status=status,
                    broker_order_id=order_id,
                    broker_status=broker_status,
                )

            # Toss can recover an ambiguous submit by the caller-generated
            # clientOrderId using read-only OPEN/CLOSED order lists.
            if not record.broker_order_id:
                recovered = await self.toss.find_order_by_client_order_id(
                    symbol=record.symbol,
                    client_order_id=record.client_order_id,
                )
                if recovered is None:
                    return record

                recovered_order_id = str(
                    recovered.get("orderId") or ""
                )
                if not recovered_order_id:
                    return record

                record = self.journal.update(
                    record.intent_id,
                    status="SUBMITTED",
                    broker_order_id=recovered_order_id,
                    broker_status=str(
                        recovered.get("status") or "PENDING"
                    ),
                    reason="Recovered by Toss clientOrderId lookup.",
                )

            payload = await self.toss.get_order(
                record.broker_order_id
            )
            order = payload.get("result") or {}
            broker_status = str(order.get("status") or "")
            status = self._toss_journal_status(
                broker_status
            )

            return self._save(
                record,
                status=status,
                broker_order_id=record.broker_order_id,
                broker_status=broker_status,
            )

        except (
            UpbitPrivateRequestError,
            TossApiError,
            ValueError,
        ):
            return record

    @staticmethod
    def _toss_journal_status(broker_status: str) -> str:
        normalized = broker_status.strip().upper()

        if normalized in {"FILLED", "CANCELED"}:
            return "CONFIRMED"
        if normalized == "REJECTED":
            return "REJECTED"

        # These states can imply that another/open order may still exist.
        # Keep the symbol blocked until a human or later broker state resolves it.
        if normalized in {
            "REPLACED",
            "CANCEL_REJECTED",
            "REPLACE_REJECTED",
        }:
            return "UNKNOWN"

        return "SUBMITTED"

    def _save(
        self,
        record: LiveOrderRecord,
        *,
        status: str,
        broker_order_id: str,
        broker_status: str,
    ) -> LiveOrderRecord:
        updated = self.journal.update(
            record.intent_id,
            status=status,
            broker_order_id=broker_order_id,
            broker_status=broker_status,
        )

        if (
            updated.source == "auto"
            and status in {"SUBMITTED", "CONFIRMED"}
        ):
            self.auto_activity.record(
                mode="live",
                market=updated.market,
                symbol=updated.symbol,
                at=updated.created_at,
            )

        if status == "CONFIRMED":
            self.audit.write(
                "orders",
                {
                    "event": "live_order_reconciled",
                    "intent_id": updated.intent_id,
                    "broker": updated.broker,
                    "broker_order_id": updated.broker_order_id,
                    "broker_status": updated.broker_status,
                },
            )
            self.push.send(
                title="Live 주문 상태 확인",
                body=(
                    f"{updated.symbol} {updated.side.upper()} · "
                    f"{updated.broker_status}"
                ),
                data={
                    "type": "live_order_reconciled",
                    "intent_id": updated.intent_id,
                    "broker": updated.broker,
                },
            )

        return updated
