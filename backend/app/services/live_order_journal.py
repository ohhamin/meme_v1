import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.models.schemas import LiveOrderRecord


class LiveOrderJournal:
    """Durable state machine for external broker order attempts.

    A record is written before any live mutation. SUBMITTING/UNKNOWN records
    are never auto-resubmitted; they must be reconciled by broker query.
    """

    terminal = {"CONFIRMED", "REJECTED"}

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.base_dir: Path = self.config.data_path / "state" / "live_orders"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        broker: str,
        source: str,
        market: str,
        symbol: str,
        side: str,
        quantity,
        notional,
        reference_price,
    ) -> LiveOrderRecord:
        now = datetime.now(self.tz)
        intent_id = uuid4().hex
        # Both brokers support caller-provided identifiers; keep under Toss 36-char limit.
        client_order_id = f"meme-{intent_id[:27]}"

        record = LiveOrderRecord(
            intent_id=intent_id,
            broker=broker,
            source=source,
            market=market,
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional=notional,
            reference_price=reference_price,
            client_order_id=client_order_id,
            status="CREATED",
            created_at=now,
            updated_at=now,
        )
        self._write(record)
        return record

    def update(
        self,
        intent_id: str,
        *,
        status: str | None = None,
        broker_order_id: str | None = None,
        broker_status: str | None = None,
        reason: str | None = None,
    ) -> LiveOrderRecord:
        record = self.get(intent_id)
        if status is not None:
            record.status = status
        if broker_order_id is not None:
            record.broker_order_id = broker_order_id
        if broker_status is not None:
            record.broker_status = broker_status
        if reason is not None:
            record.reason = reason
        record.updated_at = datetime.now(self.tz)
        self._write(record)
        return record

    def get(self, intent_id: str) -> LiveOrderRecord:
        path = self.base_dir / f"{intent_id}.json"
        if not path.exists():
            raise KeyError(intent_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return LiveOrderRecord.model_validate(raw)

    def list(
        self,
        *,
        statuses: set[str] | None = None,
        limit: int = 100,
    ) -> list[LiveOrderRecord]:
        records: list[LiveOrderRecord] = []
        for path in self.base_dir.glob("*.json"):
            try:
                record = LiveOrderRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except Exception:
                continue
            if statuses and record.status not in statuses:
                continue
            records.append(record)

        records.sort(key=lambda x: x.updated_at, reverse=True)
        return records[: max(1, min(limit, 500))]

    def unresolved(self, limit: int = 100) -> list[LiveOrderRecord]:
        return self.list(
            statuses={"SUBMITTING", "SUBMITTED", "UNKNOWN"},
            limit=limit,
        )

    def count_today(
        self,
        *,
        broker: str | None = None,
    ) -> int:
        today = datetime.now(self.tz).date()
        count = 0
        for record in self.list(limit=500):
            if record.created_at.astimezone(self.tz).date() != today:
                continue
            if broker and record.broker != broker:
                continue
            if record.status in {
                "PREFLIGHTED",
                "SUBMITTING",
                "SUBMITTED",
                "CONFIRMED",
                "UNKNOWN",
            }:
                count += 1
        return count

    def _write(self, record: LiveOrderRecord) -> None:
        path = self.base_dir / f"{record.intent_id}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temp.replace(path)
