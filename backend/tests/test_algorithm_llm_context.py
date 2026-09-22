from types import SimpleNamespace

from backend.app.services import algorithm as module
from backend.app.services.algorithm import AlgorithmService


def make_service(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(data_path=tmp_path),
    )
    return AlgorithmService()


def test_llm_context_is_much_smaller_than_human_algorithm(
    monkeypatch,
    tmp_path,
):
    service = make_service(monkeypatch, tmp_path)

    full = service.current()
    compact = service.llm_context()

    assert "Version: 0.8.0-evidence" in compact
    assert "Technical" in compact
    assert "Risk Guard v0.5" not in compact
    assert "참고 연구" not in compact
    assert len(compact) < len(full) * 0.35


def test_llm_context_keeps_applied_evidence_rules(
    monkeypatch,
    tmp_path,
):
    service = make_service(monkeypatch, tmp_path)
    service.current_path.write_text(
        service.current()
        + "\n\n### Applied: 테스트\n\n"
        + "뉴스가 모순되면 confidence를 낮춘다.\n",
        encoding="utf-8",
    )

    compact = service.llm_context()

    assert "뉴스가 모순되면 confidence를 낮춘다." in compact
