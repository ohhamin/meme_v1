from datetime import date, timedelta
from pathlib import Path
import re

from fastapi import HTTPException, status

from backend.app.core.config import get_settings


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyMarkdownStore:
    def __init__(self, folder: str):
        self.base_dir = get_settings().data_path / folder
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def available_dates(self, limit: int = 7) -> list[str]:
        dates = [
            p.stem
            for p in self.base_dir.glob("*.md")
            if _DATE_PATTERN.fullmatch(p.stem)
        ]
        return sorted(dates, reverse=True)[:limit]

    def read(self, day: str) -> str:
        if not _DATE_PATTERN.fullmatch(day):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date must be YYYY-MM-DD",
            )

        path = self.base_dir / f"{day}.md"
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data for the selected date",
            )
        return path.read_text(encoding="utf-8")

    def append_today(self, markdown: str) -> Path:
        today = date.today().isoformat()
        path = self.base_dir / f"{today}.md"
        with path.open("a", encoding="utf-8") as f:
            if path.stat().st_size > 0:
                f.write("\n\n")
            f.write(markdown.rstrip() + "\n")
        return path

    def cleanup_older_than(self, days: int = 7) -> None:
        cutoff = date.today() - timedelta(days=days)
        for path in self.base_dir.glob("*.md"):
            if not _DATE_PATTERN.fullmatch(path.stem):
                continue
            try:
                file_date = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if file_date < cutoff:
                path.unlink(missing_ok=True)
