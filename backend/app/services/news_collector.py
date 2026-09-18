from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger


class NewsCollector:
    """경제/시장 뉴스 수집 서비스의 실행 골격.

    실제 뉴스 소스/API 연동은 다음 단계에서 구현한다.
    스케줄러는 이 서비스를 6시간마다 호출한다.
    """

    def __init__(self):
        self.config = get_settings()
        self.audit = AuditLogger()
        self.tz = ZoneInfo(self.config.app_timezone)

    async def run(self) -> bool:
        # TODO:
        # 1) 경제/시장 뉴스 소스 조회
        # 2) 중복 기사 제거
        # 3) 핵심 내용 요약
        # 4) data/news/YYYY-MM-DD.md 에 수집 시각 섹션으로 append
        #
        # 실제 소스 연결 전에는 빈/가짜 뉴스를 저장하지 않는다.
        self.audit.write(
            "system",
            {
                "event": "news_collection_skipped",
                "reason": "news source not configured",
                "scheduled_interval_hours": self.config.news_collection_interval_hours,
                "local_time": datetime.now(self.tz).isoformat(),
            },
        )
        return False
