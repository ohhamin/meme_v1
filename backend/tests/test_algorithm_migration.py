from backend.app.services.algorithm import AlgorithmService


def test_legacy_applied_history_extracts_old_proposals():
    current = """# old

Version: 0.3.0-quant

## Applied Proposals

### Applied: 위험 뉴스 보류

- proposal_id: abc

뉴스 충돌 시 HOLD

### Applied: 데이터 품질

- proposal_id: def

시세가 불확실하면 HOLD
"""

    history = AlgorithmService._legacy_applied_history(current)

    assert "### Applied: 위험 뉴스 보류" in history
    assert "### Applied: 데이터 품질" in history
    assert "Version: 0.3.0-quant" not in history


def test_legacy_applied_history_is_empty_without_applied_rules():
    assert AlgorithmService._legacy_applied_history(
        "# algorithm\n\nVersion: 0.3.0-quant"
    ) == ""
