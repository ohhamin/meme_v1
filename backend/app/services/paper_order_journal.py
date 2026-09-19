import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


class PaperOrderJournal:
    """Append-only Paper execution journal with realized PnL on sells."""

    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.base_dir: Path = self.config.data_path / "paper_orders"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        order_id: str,
        market: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        notional: Decimal,
        fee: Decimal,
        source: str,
        created_at: datetime,
        session_id: str | None = None,
        realized_pnl: Decimal | None = None,
        entry_score: Decimal | None = None,
        realized_return_pct: Decimal | None = None,
    ) -> Path:
        day = created_at.astimezone(self.tz).date().isoformat()
        path = self.base_dir / f"{day}.jsonl"
        payload = {
            "order_id": order_id,
            "market": market,
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price),
            "notional": str(notional),
            "fee": str(fee),
            "source": source,
            "created_at": created_at.isoformat(),
            "session_id": session_id,
            "realized_pnl": (
                str(realized_pnl)
                if realized_pnl is not None
                else None
            ),
            "entry_score": (
                str(entry_score)
                if entry_score is not None
                else None
            ),
            "realized_return_pct": (
                str(realized_return_pct)
                if realized_return_pct is not None
                else None
            ),
        }
        with path.open("a", encoding="utf-8") as fp:
            fp.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
        return path

    def recent(
        self,
        *,
        limit: int = 50,
        days: int = 7,
        market: str | None = None,
        session_id: str | None = None,
    ) -> list[dict]:
        cutoff = datetime.now(self.tz).date() - timedelta(
            days=max(1, days) - 1
        )
        files = sorted(self.base_dir.glob("*.jsonl"), reverse=True)

        records: list[dict] = []
        for path in files:
            try:
                day = datetime.strptime(path.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if day < cutoff:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue

            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(raw, dict):
                    if market is not None and raw.get("market") != market:
                        continue
                    if session_id is not None and raw.get("session_id") != session_id:
                        continue
                    records.append(raw)
                    if len(records) >= limit:
                        return records
        return records
