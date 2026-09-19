import re

from backend.app.models.schemas import (
    LatestDecisionItem,
    LatestDecisionResponse,
)
from backend.app.services.file_store import DailyMarkdownStore


class LatestDecisionService:
    """Parse only the most recent persisted decision cycle into structured data."""

    def __init__(self):
        self.store = DailyMarkdownStore("decisions")

    def get(self, mode: str | None = None) -> LatestDecisionResponse | None:
        target = mode.upper() if mode else None
        for day in self.store.available_dates(limit=7):
            markdown = self.store.read(day)
            cycles = self._cycles(markdown)
            if target is not None:
                cycles = [
                    cycle
                    for cycle in cycles
                    if cycle["execution_mode"] == target
                ]
            if not cycles:
                continue
            cycle = cycles[-1]
            break
        else:
            return None
        items = cycle["items"]
        return LatestDecisionResponse(
            date=day,
            time=cycle["time"],
            execution_mode=cycle["execution_mode"],
            cycle_summary=cycle["cycle_summary"],
            buy_count=sum(1 for item in items if item.action == "BUY"),
            sell_count=sum(1 for item in items if item.action == "SELL"),
            hold_count=sum(1 for item in items if item.action == "HOLD"),
            items=items,
        )

    def filter_markdown(self, markdown: str, mode: str) -> str:
        target = mode.upper()
        chunks: list[list[str]] = []
        current: list[str] | None = None

        for raw in markdown.splitlines():
            line = raw.strip()
            if line.startswith("## ") and "Decision Cycle" in line:
                if current:
                    chunks.append(current)
                current = [raw]
            elif current is not None:
                current.append(raw)

        if current:
            chunks.append(current)

        selected: list[str] = []
        for chunk in chunks:
            execution_mode = "PAPER"
            for raw in chunk:
                line = raw.strip()
                if line.startswith("- Execution Mode:"):
                    execution_mode = (
                        line.split(":", 1)[1].strip().upper() or "PAPER"
                    )
                    break
            if execution_mode == target:
                selected.extend(chunk)
                selected.append("")

        return "\n".join(selected).strip()

    def _cycles(self, markdown: str) -> list[dict]:
        cycles: list[dict] = []
        current: dict | None = None
        item: dict | None = None

        def flush_item() -> None:
            nonlocal item
            if current is None or item is None:
                return
            if item.get("symbol") and item.get("action") and item.get("score") is not None:
                current["items"].append(
                    LatestDecisionItem(
                        time=current["time"],
                        market=item.get("market"),
                        symbol=item["symbol"],
                        action=item["action"],
                        score=item["score"],
                        reason=item.get("reason", ""),
                        risk=item.get("risk"),
                        block_reason=item.get("block_reason"),
                        next_check=item.get("next_check"),
                        order_side=item.get("order_side"),
                        order_quantity=item.get("order_quantity"),
                        order_notional=item.get("order_notional"),
                        execution_mode=current["execution_mode"],
                    )
                )
            item = None

        def flush_cycle() -> None:
            nonlocal current
            if current is None:
                return
            flush_item()
            cycles.append(current)
            current = None

        for raw in markdown.splitlines():
            line = raw.strip()

            if line.startswith("## ") and "Decision Cycle" in line:
                flush_cycle()
                time = line[3:].replace("Decision Cycle", "").strip()
                current = {
                    "time": time,
                    "execution_mode": "PAPER",
                    "cycle_summary": "",
                    "items": [],
                }
                continue

            if current is None:
                continue

            if line.startswith("- Execution Mode:"):
                current["execution_mode"] = (
                    line.split(":", 1)[1].strip().upper() or "PAPER"
                )
                continue

            if line.startswith("### "):
                flush_item()
                heading = line[4:].strip()
                match = re.search(r"\(([^()]+)\)\s*$", heading)
                symbol = match.group(1).strip() if match else heading
                item = {
                    "symbol": symbol,
                    "reason": "",
                }
                continue

            if line.startswith("> Cycle Summary:"):
                current["cycle_summary"] = line.split(":", 1)[1].strip()
                continue

            if item is None:
                continue

            if line.startswith("- Market:"):
                item["market"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Action:"):
                item["action"] = line.split(":", 1)[1].strip().upper()
            elif line.startswith("- Score:"):
                try:
                    item["score"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    item["score"] = None
            elif line.startswith("- Reason:"):
                item["reason"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Risk Guard:"):
                item["risk"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Block Reason:"):
                item["block_reason"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Next Check:"):
                item["next_check"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Order:"):
                item["order_side"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Order Quantity:"):
                item["order_quantity"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Order Notional:"):
                item["order_notional"] = line.split(":", 1)[1].strip()

        flush_cycle()
        return cycles
