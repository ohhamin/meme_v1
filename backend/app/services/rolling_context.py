from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.file_store import DailyMarkdownStore


class RollingContextService:
    """7일 원본 MD에서 LLM용 bounded rolling context를 만든다.

    추가 LLM 호출 없이 파일 크기만 제한하는 1차 압축 계층이다.
    추후 뉴스 수집 단계에서 저비용 모델 요약을 앞단에 추가할 수 있다.
    """

    def __init__(self):
        self.config = get_settings()
        self.base_dir: Path = self.config.data_path / "context"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def refresh_news(self) -> Path:
        return self._refresh(
            source_folder="news",
            target_name="news_rolling.md",
            max_chars=self.config.llm_context_news_chars,
        )

    def refresh_decisions(self) -> Path:
        return self._refresh(
            source_folder="decisions",
            target_name="decision_rolling.md",
            max_chars=self.config.llm_context_decision_chars,
        )

    def refresh_all(self) -> None:
        self.refresh_news()
        self.refresh_decisions()

    def _refresh(
        self,
        *,
        source_folder: str,
        target_name: str,
        max_chars: int,
    ) -> Path:
        store = DailyMarkdownStore(source_folder)
        chunks: list[str] = []

        # 오래된 날 -> 최신 날 순서로 만든 뒤 끝부분을 남기면 최신 context가 보존된다.
        for day in reversed(store.available_dates(limit=7)):
            try:
                chunks.append(store.read(day).strip())
            except Exception:
                continue

        text = "\n\n".join(chunk for chunk in chunks if chunk)
        if len(text) > max_chars:
            text = text[-max_chars:]
            newline = text.find("\n")
            if newline >= 0:
                text = text[newline + 1 :]

        target = self.base_dir / target_name
        temp = target.with_suffix(".tmp")
        temp.write_text(text.strip() + ("\n" if text.strip() else ""), encoding="utf-8")
        temp.replace(target)
        return target
