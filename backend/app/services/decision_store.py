from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.models.schemas import (
    CycleExecutionItem,
    DecisionCycleResult,
    LiveCycleExecutionItem,
)
from backend.app.services.rolling_context import RollingContextService


class DecisionMarkdownStore:
    def __init__(self):
        self.config = get_settings()
        self.tz = ZoneInfo(self.config.app_timezone)
        self.base_dir: Path = self.config.data_path / "decisions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append_cycle(
        self,
        result: DecisionCycleResult,
        *,
        risk_status: str = "PENDING",
        risk_reason: str | None = None,
    ) -> Path:
        now = datetime.now(self.tz)
        path = self.base_dir / f"{now.date().isoformat()}.md"

        is_new = not path.exists()
        lines: list[str] = []

        if is_new:
            lines.extend(
                [
                    f"# {now.date().isoformat()} Decisions",
                    "",
                ]
            )

        lines.extend(
            [
                f"## {now.strftime('%H:%M')} Decision Cycle",
                "",
            ]
        )

        for decision in result.decisions:
            display_name = decision.name.strip() if decision.name else decision.symbol
            if display_name == decision.symbol:
                heading = display_name
            else:
                heading = f"{display_name} ({decision.symbol})"

            lines.extend(
                [
                    f"### {heading}",
                    f"- Market: {decision.market}",
                    f"- Action: {decision.action}",
                    f"- Score: {decision.score}",
                    f"- Reason: {decision.reason}",
                    f"- Risk Guard: {risk_status}",
                ]
            )
            if risk_reason:
                lines.append(f"- Block Reason: {risk_reason}")
            lines.extend(
                [
                    f"- Next Check: {result.next_check_minutes}m",
                    "",
                ]
            )

        lines.extend(
            [
                f"> Cycle Summary: {result.cycle_summary}",
                "",
            ]
        )

        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        RollingContextService().refresh_decisions()
        return path


    def append_execution_cycle(
        self,
        result: DecisionCycleResult,
        items: list[CycleExecutionItem],
    ) -> Path:
        now = datetime.now(self.tz)
        path = self.base_dir / f"{now.date().isoformat()}.md"
        is_new = not path.exists()

        lines: list[str] = []
        if is_new:
            lines.extend(
                [
                    f"# {now.date().isoformat()} Decisions",
                    "",
                ]
            )

        lines.extend(
            [
                f"## {now.strftime('%H:%M')} Decision Cycle",
                "",
                "- Execution Mode: PAPER",
                "",
            ]
        )

        for item in items:
            decision = item.decision
            display_name = (
                decision.name.strip()
                if decision.name
                else decision.symbol
            )
            heading = (
                display_name
                if display_name == decision.symbol
                else f"{display_name} ({decision.symbol})"
            )

            risk_status = (
                item.risk.status
                if item.risk is not None
                else "NO_ORDER"
            )

            lines.extend(
                [
                    f"### {heading}",
                    f"- Market: {decision.market}",
                    f"- Action: {decision.action}",
                    f"- Score: {decision.score}",
                    f"- Reason: {decision.reason}",
                    f"- Sizing: {item.sizing.status}",
                    f"- Size Reason: {item.sizing.reason}",
                    f"- Risk Guard: {risk_status}",
                ]
            )

            if item.risk is not None and item.risk.reasons:
                lines.append(
                    "- Block Reason: "
                    + " | ".join(item.risk.reasons)
                )

            if item.order is not None:
                lines.extend(
                    [
                        f"- Order: {item.order.side.upper()}",
                        f"- Order Quantity: {item.order.quantity}",
                        f"- Order Price: {item.order.price}",
                        f"- Order Notional: {item.order.notional}",
                        f"- Order ID: {item.order.order_id}",
                    ]
                )

            lines.extend(
                [
                    f"- Next Check: {result.next_check_minutes}m",
                    "",
                ]
            )

        lines.extend(
            [
                f"> Cycle Summary: {result.cycle_summary}",
                "",
            ]
        )

        with path.open("a", encoding="utf-8") as fp:
            fp.write("\n".join(lines))

        RollingContextService().refresh_decisions()
        return path


    def append_live_execution_cycle(
        self,
        result: DecisionCycleResult,
        items: list[LiveCycleExecutionItem],
    ) -> Path:
        now = datetime.now(self.tz)
        path = self.base_dir / f"{now.date().isoformat()}.md"
        is_new = not path.exists()

        lines: list[str] = []
        if is_new:
            lines.extend(
                [
                    f"# {now.date().isoformat()} Decisions",
                    "",
                ]
            )

        lines.extend(
            [
                f"## {now.strftime('%H:%M')} Decision Cycle",
                "",
                "- Execution Mode: LIVE",
                "",
            ]
        )

        for item in items:
            decision = item.decision
            display_name = (
                decision.name.strip()
                if decision.name
                else decision.symbol
            )
            heading = (
                display_name
                if display_name == decision.symbol
                else f"{display_name} ({decision.symbol})"
            )
            risk_status = (
                item.risk.status
                if item.risk is not None
                else "NO_ORDER"
            )

            lines.extend(
                [
                    f"### {heading}",
                    f"- Market: {decision.market}",
                    f"- Action: {decision.action}",
                    f"- Score: {decision.score}",
                    f"- Reason: {decision.reason}",
                    f"- Sizing: {item.sizing.status}",
                    f"- Size Reason: {item.sizing.reason}",
                    f"- Risk Guard: {risk_status}",
                ]
            )

            if item.risk is not None and item.risk.reasons:
                lines.append(
                    "- Block Reason: "
                    + " | ".join(item.risk.reasons)
                )

            if (
                item.sizing.status == "ORDER"
                and item.message
                and item.message.startswith("Live order submitted")
            ):
                lines.extend(
                    [
                        f"- Order: {decision.action}",
                        f"- Order Quantity: {item.sizing.order_quantity}",
                        f"- Order Notional: {item.sizing.order_notional}",
                        f"- Order Status: SUBMITTED",
                    ]
                )

            if item.message:
                lines.append(f"- Execution Message: {item.message}")

            lines.extend(
                [
                    f"- Next Check: {result.next_check_minutes}m",
                    "",
                ]
            )

        lines.extend(
            [
                f"> Cycle Summary: {result.cycle_summary}",
                "",
            ]
        )

        with path.open("a", encoding="utf-8") as fp:
            fp.write("\n".join(lines))

        RollingContextService().refresh_decisions()
        return path
