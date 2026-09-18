from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from uuid import uuid4

from fastapi import HTTPException, status

from backend.app.core.config import get_settings
from backend.app.models.schemas import AlgorithmProposal, AlgorithmProposalCreate


_RULE_RE = re.compile(
    r"<!-- RULE_START -->\s*(.*?)\s*<!-- RULE_END -->",
    flags=re.DOTALL,
)


_BASELINE = """# Current Trading Algorithm

Version: 0.1.0-baseline

이 문서는 Decision Engine이 참조하는 현재 알고리즘 규칙 문서다.
초기 버전은 실제 매수/매도 공식을 확정하지 않고, 판단 흐름과 안전 제약만 정의한다.

## Inputs

- 현재 보유 포지션과 손익
- 현재가/거래량/변동성 등 시장 데이터
- 최근 7일 뉴스 Markdown
- 직전 판단과 다음 체크 시각

## Decision Output

각 종목마다 다음을 생성한다.

- BUY / SELL / HOLD
- 판단점수 0~100
- 판단 근거
- 다음 판단 간격 30~120분

판단점수는 방향성을 표시하기 위한 값이며, 단독으로 주문을 실행하는 임계값은 아직 정의하지 않는다.

## Scheduler

- 기본 판단 간격: 60분
- 최소: 30분
- 최대: 120분
- 변동성, 뉴스 중요도, 포지션 상태에 따라 다음 간격을 조정한다.
- Backend가 최종적으로 30~120분 범위를 강제한다.

## Risk

- Decision Engine의 결과 뒤에 Risk Guard가 별도로 동작한다.
- Paper mode가 기본이다.
- Kill switch가 켜져 있으면 신규 주문을 모두 차단한다.
- 파싱/API 오류가 있으면 자동 주문은 fail-closed 한다.

## Algorithm Changes

알고리즘은 실행 중 Python 코드를 스스로 수정하지 않는다.
승인된 제안은 이 문서의 Applied Proposals 영역에 규칙으로 추가되며,
Decision Engine은 다음 판단부터 갱신된 문서를 참조한다.

## Applied Proposals

아직 적용된 제안이 없다.
"""


class AlgorithmService:
    def __init__(self):
        root = get_settings().data_path / "algorithm"
        self.current_path = root / "current.md"
        self.pending_dir = root / "proposals" / "pending"
        self.applied_dir = root / "proposals" / "applied"
        self.cancelled_dir = root / "proposals" / "cancelled"

        for directory in (
            root,
            self.pending_dir,
            self.applied_dir,
            self.cancelled_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        if not self.current_path.exists():
            self.current_path.write_text(_BASELINE, encoding="utf-8")

    def current(self) -> str:
        return self.current_path.read_text(encoding="utf-8")

    def list_pending(self) -> list[AlgorithmProposal]:
        proposals = []
        for path in sorted(self.pending_dir.glob("*.md"), reverse=True):
            markdown = path.read_text(encoding="utf-8")
            title = self._extract_title(markdown)
            proposals.append(
                AlgorithmProposal(
                    id=path.stem,
                    title=title,
                    markdown=markdown,
                    created_at=self._extract_created_at(markdown),
                )
            )
        return proposals

    def create(self, payload: AlgorithmProposalCreate) -> AlgorithmProposal:
        proposal_id = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:6]
        created_at = datetime.now(timezone.utc)
        markdown = (
            f"# {payload.title}\n\n"
            f"- id: {proposal_id}\n"
            f"- created_at: {created_at.isoformat()}\n"
            f"- status: pending\n\n"
            f"## 제안 이유\n\n{payload.reason.strip()}\n\n"
            f"## 제안 규칙\n\n"
            f"<!-- RULE_START -->\n"
            f"{payload.rule_text.strip()}\n"
            f"<!-- RULE_END -->\n"
        )
        path = self.pending_dir / f"{proposal_id}.md"
        path.write_text(markdown, encoding="utf-8")
        return AlgorithmProposal(
            id=proposal_id,
            title=payload.title,
            markdown=markdown,
            created_at=created_at,
        )

    def apply(self, proposal_id: str) -> str:
        source = self._proposal_path(proposal_id)
        markdown = source.read_text(encoding="utf-8")
        match = _RULE_RE.search(markdown)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Proposal has no valid rule block.",
            )

        rule = match.group(1).strip()
        applied_at = datetime.now(timezone.utc).isoformat()
        current = self.current().rstrip()

        if "아직 적용된 제안이 없다." in current:
            current = current.replace("아직 적용된 제안이 없다.", "")

        addition = (
            f"\n\n### Applied: {self._extract_title(markdown)}\n\n"
            f"- proposal_id: {proposal_id}\n"
            f"- applied_at: {applied_at}\n\n"
            f"{rule}\n"
        )

        temp = self.current_path.with_suffix(".tmp")
        temp.write_text(current + addition, encoding="utf-8")
        temp.replace(self.current_path)

        shutil.move(str(source), str(self.applied_dir / source.name))
        return self.current()

    def cancel(self, proposal_id: str) -> None:
        source = self._proposal_path(proposal_id)
        shutil.move(str(source), str(self.cancelled_dir / source.name))

    def _proposal_path(self, proposal_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", proposal_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid proposal id",
            )
        path = self.pending_dir / f"{proposal_id}.md"
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found",
            )
        return path

    @staticmethod
    def _extract_title(markdown: str) -> str:
        first = markdown.splitlines()[0] if markdown.splitlines() else "Untitled"
        return first.removeprefix("# ").strip() or "Untitled"

    @staticmethod
    def _extract_created_at(markdown: str):
        for line in markdown.splitlines():
            if line.startswith("- created_at:"):
                raw = line.split(":", 1)[1].strip()
                try:
                    return datetime.fromisoformat(raw)
                except ValueError:
                    return None
        return None
