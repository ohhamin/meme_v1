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


_BASELINE = """# 현재 매매 알고리즘

Version: 0.4.0-quant

## 한눈에 보기

이 알고리즘은 **수학적 정량 신호가 방향을 먼저 정하고, AI는 그 판단을 확인하거나 HOLD로 보류만 하는 구조**다.

1. 거래가 충분한 종목만 후보로 고른다.
2. 일봉 가격으로 모멘텀·추세·변동성·거래량을 계산해 0~100점을 만든다.
3. 정량점수 65 이상은 BUY 후보, 35 이하는 SELL 후보, 사이는 HOLD다.
4. AI는 뉴스·거시환경·계좌상태를 보고 BUY/SELL을 HOLD로 보류할 수 있지만 반대 방향으로 뒤집을 수 없다.
5. 변동성이 높을수록 주문 크기를 줄이고, 마지막에는 Risk Guard가 주문 가능 여부를 다시 검사한다.

즉 **후보 선정 → 정량 점수 → AI 보수적 검토 → 주문크기 계산 → Risk Guard** 순서다.

## 수학적 핵심

기간수익률: R_n = P_t / P_(t-n) - 1

위험조정 모멘텀: Z_n = R_n / (sigma × sqrt(n))

MomentumScore_n = 50 + 25 × clip(Z_n, -2, 2)

여기서 sigma는 최근 일별 수익률의 표준편차다.

### 주식

한국 개별주식은 전통적인 '과거 수익률이 높을수록 계속 산다' 방식의 모멘텀이 장기 반전에 취약하다는 연구가 있어,
극단적인 하루 급등락의 영향을 줄이는 **Sign Momentum(상승한 날의 비율)** 을 핵심으로 사용한다.

Sign_n = 최근 n일 중 수익률이 양수인 거래일 수 / 수익률이 0이 아닌 거래일 수 × 100

StockScore = 0.30×Sign60 + 0.20×Sign20 + 0.20×Trend + 0.15×M20 + 0.10×Stability + 0.05×VolumeConfirm - SaliencePenalty

- Sign60: 최근 60거래일 중 상승일 비율
- Sign20: 최근 20거래일 중 상승일 비율
- M20: 최근 20거래일 위험조정 수익률. 보조 신호로만 사용
- Trend: 현재가가 단기/장기 평균가격 위인지 아래인지
- Stability: 일 변동성이 낮을수록 높은 점수
- VolumeConfirm: 가격 방향과 거래량 변화가 같은 방향인지 확인
- 5일·20일의 극단적 급등과 큰 누적수익은 추격매수/반전 위험으로 감점

### 코인

CryptoScore = 0.40×M21 + 0.30×M7 + 0.15×Trend + 0.10×Stability + 0.05×VolumeConfirm - ReversalPenalty

- M21: 최근 21일 위험조정 모멘텀
- M7: 최근 7일 위험조정 모멘텀
- 42일 강한 상승이 21일 신호보다 과도하게 앞서 있으면 장기 반전 가능성을 고려해 감점
- 장기 낙폭이 크다는 이유만으로 자동 매수하지는 않음

## BUY / HOLD / SELL

- Quant Score >= 65: BUY 후보
- 36~64: HOLD
- Quant Score <= 35: SELL 후보

AI는 이 방향을 반대로 바꿀 수 없다.

- Quant BUY → AI 결과는 BUY 또는 HOLD
- Quant SELL → AI 결과는 SELL 또는 HOLD
- Quant HOLD → AI 결과는 HOLD

## 변동성에 따른 주문 크기

기본 BUY 크기는 판단점수에 따라 계좌 평가금액의 1~4%다.

- 60~69: 1%
- 70~79: 2%
- 80~89: 3%
- 90~100: 4%

RiskScale = min(1, TargetVol / RealizedVol)

- 주식 TargetVol: 일 2%
- 코인 TargetVol: 일 4%
- RiskScale 하한: 0.35
- 저변동성이라고 주문을 1배보다 키우지는 않는다.

SELL은 기존 보유수량 기준으로 단계적으로 축소한다.

- 점수 31~40: 25%
- 점수 21~30: 40%
- 점수 0~20: 60%

## Risk Guard

- Kill switch
- 오래된 시세 차단
- 주식 장 운영 여부
- 일일 손실 한도
- 일일 주문 횟수
- 한 종목 최대 비중
- 전체 최대 보유 종목 수
- 최소 현금 보유
- 같은 종목 자동 주문 cooldown
- 미확인 Live 주문 중복 방지

## 연구 근거와 한계

핵심 방향은 한국 주식시장의 sign/rank momentum 연구, 코인의 단기 모멘텀과 장기 반전 연구,
그리고 고변동성 시 노출 축소와 유동성 필터에 관한 학술 연구를 참고했다.

다만 **위 가중치와 65/35 임계값은 논문에서 그대로 가져온 숫자가 아니라 이 앱을 위한 초기 설계값**이다.
Paper 데이터와 walk-forward 검증이 충분히 쌓이기 전에는 수익성을 입증한 값으로 취급하지 않는다.

## Algorithm Changes

성과 데이터가 충분히 쌓이면 변경 제안을 만들 수 있지만 사용자가 승인한 변경만 적용한다.

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
        else:
            current = self.current_path.read_text(encoding="utf-8")
            if (
                (
                    "Version: 0.2.0-baseline" in current
                    or "Version: 0.3.0-quant" in current
                )
                and "### Applied:" not in current
            ):
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
