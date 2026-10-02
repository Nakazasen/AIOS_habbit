"""Tests for golden_question_quality: M1-M5 on fixture data with fake adapters."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aios_habit.golden_question_export import export_batch, fixture_phenomena
from aios_habit.golden_question_generator import PhenomenonContext
from aios_habit.golden_question_quality import (
    build_standard_questions,
    high_gap_count,
    measure_m1,
    measure_m2,
    measure_m3,
    measure_m4,
    measure_m5,
    render_quality_report,
    run_before_after,
    write_quality_report,
)
from aios_habit.golden_question_schema import GoldenAnswer
from aios_habit.knowledge_coverage import (
    REASON_INSUFFICIENT_EVIDENCE,
    REASON_MISSING_SOURCE,
    CollectionInventory,
    CoverageQuestion,
    DocumentInventoryItem,
    FakeKnowledgeRetrievalAdapter,
    RetrievedSnippet,
    RetrievalReceipt,
)


@pytest.fixture
def phenomena():
    return fixture_phenomena("KB-QUALITY")


@pytest.fixture
def inventory():
    docs = (
        DocumentInventoryItem(
            doc_id="DOC-FCALL",
            title="Tài liệu F CALL",
            path="/docs/fcall.md",
            scope="F CALL",
            digest="abc",
        ),
    )
    return CollectionInventory(
        collection_id="error_cases",
        version="1.0.0",
        scopes=("F CALL",),
        documents=docs,
    )


def _receipt(question: CoverageQuestion, reason: str, score: float,
             snippets=()) -> RetrievalReceipt:
    return RetrievalReceipt(
        question_text=question.question_text,
        scope=question.scope,
        sources_checked=("DOC-FCALL",) if reason != REASON_MISSING_SOURCE else (),
        retrieved_snippets=tuple(snippets),
        coverage_score=score,
        reason_code=reason,
    )


def _adapters(phenomena, inventory, before_reason, after_with_new_chunks: bool):
    questions = build_standard_questions(phenomena)
    before_receipts = {q.question_id: _receipt(q, before_reason, 0.2) for q in questions}
    snippets = []
    if after_with_new_chunks:
        snippets = [
            RetrievedSnippet(
                snippet_id="STAGING-GQ-001#chunk_001",
                doc_id="DOC-FCALL",
                text="Tri thức mới từ câu hỏi vàng",
                score=0.95,
                metadata={"golden_new": True},
            )
        ]
    after_receipts = {q.question_id: _receipt(q, "sufficient_evidence", 0.9, snippets)
                      for q in questions}
    before = FakeKnowledgeRetrievalAdapter(inventory, before_receipts)
    after = FakeKnowledgeRetrievalAdapter(inventory, after_receipts)
    return questions, before, after


def _answers_for(phenomena, exported_questions):
    answers = []
    for payload_line in exported_questions:
        payload = json.loads(payload_line)
        q = payload["question"]
        ctx = payload["case_context"]
        data = {
            "answer_id": "GA-%s-1" % q["question_id"],
            "question_id": q["question_id"],
            "gap_id": q["target_gap_id"],
            "case_ids": ctx["case_ids"],
            "error_code": ctx["error_code"],
            "error_group": ctx["error_group"],
            "phenomenon": ctx["phenomenon"],
            "answer_text": "Đáp án đầy đủ cho câu hỏi này với cơ chế A dẫn tới B rồi tới C, đã đo đạc kiểm chứng.",
            "answer_state": "answered",
            "hypotheses": list(q["gia_thuyet_lien_quan"]) or ["H1", "H2"],
            "causal_mechanism": "A quá tải → B nóng → C dừng",
            "m4_branches": ["Machine"],
            "evidence_to_collect": ["Số đo dòng điện 10A lúc lỗi"],
            "confirm_criteria": "Dòng vượt 10A trong 3 lần đo",
            "thresholds": [{"name": "dòng", "value": "10", "unit": "A", "tolerance": "±10%"}],
            "confidence": 0.85,
            "question_loai": q["loai_cau_hoi"],
        }
        if q["loai_cau_hoi"] == "discriminator":
            data["discriminate_notes"] = "Ngưỡng 10A phân biệt các giả thuyết."
        answers.append(GoldenAnswer.from_dict(data))
    return answers


def test_m1_high_gap_reduction(phenomena, inventory):
    questions, before, after = _adapters(phenomena, inventory, REASON_MISSING_SOURCE, False)
    _, gaps_before = measure_m1(before, inventory, questions)
    _, gaps_after = measure_m1(after, inventory, questions)
    assert high_gap_count(gaps_before) == 5  # one high gap per phenomenon
    assert high_gap_count(gaps_after) == 0
    reduction = (5 - 0) / 5
    assert reduction >= 0.60


def test_m2_new_chunks_hit_top5(phenomena, inventory):
    questions, _, after = _adapters(phenomena, inventory, REASON_MISSING_SOURCE, True)
    result = measure_m2(after, questions)
    assert result["hits"] == 5
    assert result["total"] == 5


def test_m3_form_completeness(phenomena, tmp_path: Path):
    exported = export_batch("KB-Q3", phenomena, tmp_path / "b")
    lines = (tmp_path / "b" / "batch_KB-Q3_questions.jsonl").read_text(encoding="utf-8").splitlines()
    answers = _answers_for(phenomena, lines)
    result = measure_m3(answers)
    assert result["form_completeness"] >= 0.80
    assert result["measurable_evidence_rate"] >= 0.80
    assert result["causal_complete_rate"] >= 0.80
    assert result["total_answers"] == len(answers)


def test_m4_hypothesis_discrimination(phenomena, tmp_path: Path):
    exported = export_batch("KB-Q4", phenomena, tmp_path / "b")
    lines = (tmp_path / "b" / "batch_KB-Q4_questions.jsonl").read_text(encoding="utf-8").splitlines()
    questions_by_id = {}
    for line in lines:
        payload = json.loads(line)
        from aios_habit.golden_question_schema import GoldenQuestion

        questions_by_id[payload["question"]["question_id"]] = GoldenQuestion.from_dict(payload["question"])
    answers = _answers_for(phenomena, lines)
    result = measure_m4(phenomena, questions_by_id, answers)
    # Fixture: 5 phenomena x 1 hypothesis pair each, all discriminated.
    assert result["total_pairs"] == 5
    assert result["discriminated_pairs"] == 5
    assert result["rate"] == 1.0


def test_m5_expert_deviation():
    assert measure_m5("giữ nguyên", "giữ nguyên") == 0.0
    assert measure_m5("", "") == 0.0
    dev = measure_m5("đáp án gốc ban đầu", "đáp án đã được chuyên gia sửa toàn bộ nội dung khác hẳn")
    assert 0.0 < dev <= 1.0


def test_measure_answer_time():
    from aios_habit.golden_question_quality import measure_answer_time

    assert measure_answer_time([]) == {}
    exported_batch = export_batch("KB-AT", fixture_phenomena("KB-AT"), Path("/tmp/gq_at"))
    lines = (Path("/tmp/gq_at") / "batch_KB-AT_questions.jsonl").read_text(encoding="utf-8").splitlines()
    answers = _answers_for(fixture_phenomena("KB-AT"), lines)
    assert measure_answer_time(answers) == {}  # no timestamps
    stamped = []
    for i, a in enumerate(answers[:3]):
        data = a.to_dict()
        data["answered_at"] = "2026-10-02T%02d:00:00+07:00" % (8 + i)
        stamped.append(GoldenAnswer.from_dict(data))
    result = measure_answer_time(stamped)
    assert result["answers_with_timestamp"] == 3
    assert result["batch_span_minutes"] == 120.0


def test_run_before_after_and_report(phenomena, inventory, tmp_path: Path):
    questions, before, after = _adapters(phenomena, inventory, REASON_MISSING_SOURCE, True)
    exported = export_batch("KB-QR", phenomena, tmp_path / "b")
    lines = (tmp_path / "b" / "batch_KB-QR_questions.jsonl").read_text(encoding="utf-8").splitlines()
    from aios_habit.golden_question_schema import GoldenQuestion

    questions_by_id = {}
    for line in lines:
        payload = json.loads(line)
        questions_by_id[payload["question"]["question_id"]] = GoldenQuestion.from_dict(payload["question"])
    answers = _answers_for(phenomena, lines)

    report = run_before_after(
        "KB-QR", phenomena, before, after, inventory, questions_by_id, answers
    )
    assert report.m1_high_gap_reduction >= 0.60
    assert report.m2_hits >= 4
    assert report.m3_form_completeness >= 0.80
    assert report.m4_rate >= 0.70
    assert report.overall_pass()

    text = render_quality_report(report)
    assert "KB-QR" in text
    assert "M1" in text and "M4" in text
    path = write_quality_report(report, str(tmp_path / "reports"))
    assert Path(path).name == "bao_cao_chat_luong_KB-QR.md"
    assert Path(path).exists()
