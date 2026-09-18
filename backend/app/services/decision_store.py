from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.models.schemas import DecisionCycleResult
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
