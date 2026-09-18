from backend.app.models.schemas import AlgorithmProposalCreate
from backend.app.services.algorithm import AlgorithmService


class AlgorithmReviewService:
    """운영 데이터를 바탕으로 전략 변경 '제안'만 만드는 계층.

    실제 자동 분석 기준은 Decision/Order 로그가 쌓인 뒤 구현한다.
    이 서비스는 절대로 제안을 자동 적용하지 않는다.
    """

    def __init__(self):
        self.algorithms = AlgorithmService()

    def propose(
        self,
        *,
        title: str,
        reason: str,
        rule_text: str,
    ):
        return self.algorithms.create(
            AlgorithmProposalCreate(
                title=title,
                reason=reason,
                rule_text=rule_text,
            )
        )

    def review_needed(self) -> bool:
        # TODO:
        # - 판단 방향이 반복적으로 뒤집히는지
        # - 동일 Risk Guard 사유가 반복되는지
        # - 판단 간격이 실제 변동성에 부적절했는지
        # - Paper 결과가 의도한 규칙과 지속적으로 어긋나는지
        # 등을 분석해 제안 생성 여부를 판단한다.
        return False
