"""Tests for answer_draft_fallback: a->b->c chain, label, flag, metrics."""

import pytest

from aios_habit import answer_draft_fallback as fallback


@pytest.fixture(autouse=True)
def _clean_flag():
    fallback.clear_draft_fallback_override()
    yield
    fallback.clear_draft_fallback_override()


def _entries():
    return [
        fallback.DraftEntry(
            question="Trong file cấu hình Matecon, ctrlMode 0 và 1 khác nhau thế nào?",
            answer="ctrlMode 0 là sản xuất tự động, ctrlMode 1 là thủ công.",
            source_file="mom/batch-01.md",
            position=1,
        ),
        fallback.DraftEntry(
            question="AGV báo lỗi nguồn thấp thì kiểm tra gì?",
            answer="Kiểm tra nguồn và dây kết nối.",
            source_file="lsu/batch-16.md",
            position=2,
        ),
    ]


def test_rag_usable_returns_rag_lane():
    decision = fallback.resolve_answer(
        "ctrlMode là gì?",
        rag_ok=True,
        rag_answer="ctrlMode điều khiển truyền thông.",
        outcome_status="success",
        confidence_label="high",
        draft_entries=_entries(),
        enabled=True,
    )
    assert decision.lane == "rag"
    assert decision.has_draft_label is False


def test_rag_failure_falls_back_with_label():
    decision = fallback.resolve_answer(
        "ctrlMode 0 và 1 khác nhau thế nào trong file cấu hình Matecon?",
        rag_ok=False,
        rag_answer="",
        outcome_status="insufficient_evidence",
        draft_entries=_entries(),
        enabled=True,
    )
    assert decision.lane == "draft_fallback"
    assert fallback.DRAFT_LABEL in decision.answer_text
    assert decision.has_draft_label is True


def test_rag_admits_unknown_triggers_fallback():
    decision = fallback.resolve_answer(
        "ctrlMode 0 và 1 khác nhau thế nào?",
        rag_ok=True,
        rag_answer="Tôi không tìm thấy trong nguồn đang bật.",
        outcome_status="success",
        confidence_label="high",
        draft_entries=_entries(),
        enabled=True,
    )
    assert decision.lane == "draft_fallback"


def test_out_of_scope_returns_honest_not_found():
    decision = fallback.resolve_answer(
        "Thủ đô của sao Hỏa là gì?",
        rag_ok=False,
        rag_answer="",
        draft_entries=_entries(),
        enabled=True,
    )
    assert decision.lane == "not_found"
    assert "không tìm thấy" in decision.answer_text


def test_flag_off_restores_legacy_rag_only():
    decision = fallback.resolve_answer(
        "ctrlMode 0 và 1 khác nhau thế nào?",
        rag_ok=False,
        rag_answer="",
        draft_entries=_entries(),
        enabled=False,
    )
    assert decision.lane == "rag"
    assert decision.answer_text == ""
    assert fallback.DRAFT_LABEL not in decision.answer_text


def test_flag_defaults_on_and_env_can_turn_off(monkeypatch):
    monkeypatch.delenv(fallback.FLAG_ENV_KEY, raising=False)
    assert fallback.draft_fallback_enabled() is True
    monkeypatch.setenv(fallback.FLAG_ENV_KEY, "0")
    assert fallback.draft_fallback_enabled() is False


def test_metrics_and_label_rate_must_be_100_percent():
    records = [
        {"lane": "rag", "correct": True, "has_draft_label": False},
        {"lane": "draft_fallback", "correct": True, "has_draft_label": True},
        {"lane": "draft_fallback", "correct": False, "has_draft_label": True},
        {"lane": "not_found", "correct": True, "has_draft_label": False},
    ]
    metrics = fallback.compute_fallback_metrics(records)
    assert metrics.total == 4
    assert metrics.coverage == 0.75
    assert metrics.fallback_rate == 0.5
    assert metrics.draft_label_rate == 1.0


def test_metrics_flag_missing_label():
    records = [
        {"lane": "draft_fallback", "correct": True, "has_draft_label": False},
    ]
    metrics = fallback.compute_fallback_metrics(records)
    assert metrics.draft_label_rate == 0.0
    hints = fallback.review_recommendations(metrics)
    assert any("nhãn" in hint for hint in hints)


def test_parser_reads_question_answer_pairs():
    text = (
        "## CÂU HỎI 1\n"
        "- Hỏi: Câu hỏi mẫu là gì?\n"
        "- Đáp: Đây là đáp án mẫu.\n"
    )
    parsed = fallback.parse_draft_text(text, source_file="mom/batch-01.md")
    assert len(parsed) == 1
    assert "mẫu" in parsed[0].question
    assert parsed[0].source_file == "mom/batch-01.md"
