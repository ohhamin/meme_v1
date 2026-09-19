from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from uuid import uuid4

from fastapi import HTTPException, status

from backend.app.core.config import get_settings
from backend.app.services.audit import AuditLogger
from backend.app.models.schemas import AlgorithmProposal, AlgorithmProposalCreate


_RULE_RE = re.compile(
    r"<!-- RULE_START -->\s*(.*?)\s*<!-- RULE_END -->",
    flags=re.DOTALL,
)


_BASELINE = """# Current Trading Algorithm

Version: 0.2.0-baseline

이 문서는 Decision Engine이 참조하는 승인된 판단 규칙이다.
주문 실행 안전장치(Risk Guard)는 이 문서와 별도의 deterministic 코드로 동작한다.

## Portfolio Philosophy

- 주식(Toss)과 코인(Upbit)은 서로 다른 계좌로 판단한다.
- 실제 보유 종목 수는 전체 0~10개다.
- 10개를 채우는 것이 목표가 아니다.
- 시장에 매력적인 기회가 없으면 0개 보유 / 현금 100%도 정상이다.
- 현금 비중이 높다는 이유만으로 BUY하지 않는다.
- 이미 보유한 종목도 매 사이클 다시 평가한다.

## Inputs

- 현재 계좌별 현금/평가금액/보유 포지션/손익
- 판단 대상 종목의 최신 가격 및 시장 상태
- 가능할 경우 OHLCV 기반 단기/중기 수익률, 평균가격 괴리, 변동성, 거래량 변화
- 압축된 최근 뉴스/거시경제 Context
- 최근 판단 Context
- 사용자가 승인한 Applied Proposal 규칙

## Decision Semantics

각 종목마다 하나만 출력한다.

- BUY: 신규 또는 추가 매수를 원하는 방향
- SELL: 기존 포지션의 일부/전부 축소를 원하는 방향
- HOLD: 지금은 주문을 만들 근거가 충분하지 않음

판단점수는 방향성을 0~100으로 표현한다.

- 0~40: SELL 영역
- 41~59: HOLD 영역
- 60~100: BUY 영역

Action과 Score는 반드시 같은 방향이어야 한다.
데이터가 부족하거나 서로 충돌하면 HOLD를 우선한다.

## Decision Discipline

- 단순히 지난 사이클의 판단을 반복하지 말고 새 정보가 있는지 확인한다.
- 반대로 작은 가격 움직임만으로 BUY↔SELL을 자주 뒤집지 않는다.
- 최근 판단 이후 의미 있는 변화가 없으면 HOLD를 선호한다.
- 뉴스 한 건만으로 강한 결론을 만들지 않고 가격/계좌/시장 Context와 함께 본다.
- 기술지표 하나만으로 BUY/SELL을 강제하지 않고 여러 근거 중 하나로 사용한다.
- 기술 feature가 없거나 표본이 부족하면 없는 값을 추정하지 않는다.
- 확인되지 않은 사실이나 제공되지 않은 가격/잔고를 만들어내지 않는다.
- 이미 발생한 손실을 만회하기 위한 보복성 매수/물타기를 가정하지 않는다.
- '항상 투자되어 있어야 한다'는 전제를 두지 않는다.

## Position Sizing Boundary

Decision Engine은 주문 금액을 직접 정하지 않는다.
BUY/SELL/HOLD + Score만 결정하고 실제 주문 후보 크기는 Position Sizer가 계산한다.

초기 실행 기준:

- BUY score 60~69: 계좌 평가금액의 1% 후보
- BUY score 70~79: 2%
- BUY score 80~89: 3%
- BUY score 90~100: 4%
- SELL score 31~40: 보유수량 25% 후보
- SELL score 21~30: 40%
- SELL score 0~20: 60%

이 값은 후보 크기이며 Risk Guard가 최종 PASS/BLOCK한다.

## Risk Boundary

Decision Engine은 Risk Guard를 우회할 수 없다.

현재 hard-risk의 핵심:

- Kill switch
- stale data 차단
- 주식 장 운영 여부
- 일일 손실/주문 횟수 제한
- 한 종목 최대 40%
- 전체 보유종목 최대 10개
- 계좌별 최소 현금 reserve
- 미확인 Live 주문이 있는 종목의 신규 Live 주문 차단

Risk Guard가 BLOCK한 것을 BUY/SELL 판단의 성공으로 간주하지 않는다.

## Scheduler

전체 Decision Cycle에 대해 하나의 next_check_minutes를 제안한다.

- 허용 범위: 30~120분
- 높은 변동성/중요 이벤트: 30~45분 고려
- 일반적인 시장: 약 60분 고려
- 변화가 작고 긴급성이 낮음: 90~120분 고려
- 단순히 주문을 만들기 위해 짧은 간격을 선택하지 않는다.

## Algorithm Changes

실행 중 Python/Dart 코드를 스스로 수정하지 않는다.
운영 데이터를 보고 개선이 필요하면 별도 Proposal을 만들 수 있지만,
사용자가 Apply한 Markdown 규칙만 다음 Decision Cycle부터 적용된다.

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
        self.audit = AuditLogger()

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
        self.audit.write(
            "system",
            {
                "event": "algorithm_proposal_created",
                "proposal_id": proposal_id,
                "title": payload.title,
            },
        )
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
        self.audit.write(
            "system",
            {
                "event": "algorithm_proposal_applied",
                "proposal_id": proposal_id,
                "title": self._extract_title(markdown),
            },
        )
        return self.current()

    def cancel(self, proposal_id: str) -> None:
        source = self._proposal_path(proposal_id)
        markdown = source.read_text(encoding="utf-8")
        shutil.move(str(source), str(self.cancelled_dir / source.name))
        self.audit.write(
            "system",
            {
                "event": "algorithm_proposal_cancelled",
                "proposal_id": proposal_id,
                "title": self._extract_title(markdown),
            },
        )

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
