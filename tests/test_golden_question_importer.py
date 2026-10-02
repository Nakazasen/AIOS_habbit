"""Tests for golden_answer_importer: staging-only, dedup, schema, prod refusal."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aios_habit.golden_answer_importer import (
    ProductionWriteRefusedError,
    assert_not_production,
    dedup_key,
    import_batch_answers,
    record_expert_feedback,
)
from aios_habit.golden_question_export import export_batch, fixture_phenomena
from aios_habit.golden_question_schema import ENRICHMENT_LABEL


def _answer_dict(question_payload: dict, **overrides):
    q = question_payload["question"]
    ctx = question_payload["case_context"]
    data = {
        "answer_id": "GA-%s-1" % q["question_id"],
        "question_id": q["question_id"],
        "gap_id": q["target_gap_id"],
        "case_ids": ctx["case_ids"],
        "error_code": ctx["error_code"],
        "error_group": ctx["error_group"],
        "phenomenon": ctx["phenomenon"],
        "answer_text": "Đáp án đầy đủ cho câu hỏi này: cơ chế là A dẫn tới B rồi tới C, đã đo đạc kiểm chứng.",
        "answer_state": "answered",
        "hypotheses": ["H1: giả thuyết A", "H2: giả thuyết B"],
        "causal_mechanism": "A quá tải → B nóng lên → C dừng máy",
        "m4_branches": ["Machine"],
        "evidence_to_collect": ["Số đo dòng điện lúc lỗi (ampe kìm)"],
        "confirm_criteria": "Dòng vượt 10A trong 3 lần đo liên tiếp",
        "refute_criteria": "Dòng ổn định dưới 8A mà vẫn lỗi",
        "thresholds": [{"name": "dòng định mức", "value": "8", "unit": "A", "tolerance": "±10%"}],
        "confidence": 0.8,
        "reviewer_status": "cho_chuyen_gia_phan_hoi",
        "question_loai": q["loai_cau_hoi"],
    }
    if q["loai_cau_hoi"] == "discriminator":
        data["discriminate_notes"] = "Ngưỡng 10A phân biệt H1/H2."
    data.update(overrides)
    return data


@pytest.fixture
def batch_files(tmp_path: Path):
    phenomena = fixture_phenomena("KB-IMPORT")
    exported = export_batch("KB-IMPORT", phenomena, tmp_path / "batch")
    payloads = [
        json.loads(line)
        for line in exported.questions_path.read_text(encoding="utf-8").splitlines()
    ]
    return exported, payloads


def _write_answers(tmp_path: Path, payloads, indices, **overrides):
    path = tmp_path / "answers.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for i in indices:
            handle.write(json.dumps(_answer_dict(payloads[i], **overrides), ensure_ascii=False) + "\n")
    return path


def test_import_happy_path_staging_only(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = _write_answers(tmp_path, payloads, [0, 1, 2])
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 3
    assert report.errors == []
    assert report.claims_created == 3

    conn = sqlite3.connect(str(staging))
    try:
        labels = {row[0] for row in conn.execute("SELECT DISTINCT enrichment_label FROM staging_answers")}
        assert labels == {ENRICHMENT_LABEL}
        statuses = {row[0] for row in conn.execute("SELECT DISTINCT reviewer_status FROM staging_answers")}
        assert statuses == {"cho_chuyen_gia_phan_hoi"}
        claim_statuses = {row[0] for row in conn.execute("SELECT DISTINCT status FROM staging_claims")}
        assert claim_statuses == {"candidate"}
        # No LLM-source field anywhere in stored payloads.
        for (payload_json,) in conn.execute("SELECT payload_json FROM staging_answers"):
            assert "answered_by" not in payload_json
            assert "model_name" not in payload_json
    finally:
        conn.close()


def test_dedup_skips_identical_answers(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = _write_answers(tmp_path, payloads, [0, 0, 1])
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 2
    assert report.duplicates_skipped == 1


def test_rejects_bad_schema_and_unknown_question(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = tmp_path / "answers.jsonl"
    good = _answer_dict(payloads[0])
    vague = _answer_dict(payloads[1])
    vague["causal_mechanism"] = ""  # answered but no causality -> rejected
    unknown_q = _answer_dict(payloads[2])
    unknown_q["question_id"] = "GQ-NOPE-99"
    llm_leak = _answer_dict(payloads[3])
    llm_leak["answered_by"] = "copilot"
    with answers_path.open("w", encoding="utf-8") as handle:
        for item in (good, vague, unknown_q, llm_leak):
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 1
    assert len(report.errors) == 3
    errors_path = staging.parent / "import_errors.jsonl"
    assert errors_path.exists()
    assert len(errors_path.read_text(encoding="utf-8").splitlines()) == 3


def test_refuses_expert_reviewed_input(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = _write_answers(
        tmp_path, payloads, [0], reviewer_status="chuyen_gia_da_phan_hoi"
    )
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 0
    assert len(report.errors) == 1
    assert "chuyen_gia_da_phan_hoi" in report.errors[0]["reason"]


def test_refuses_production_paths(tmp_path: Path):
    with pytest.raises(ProductionWriteRefusedError):
        assert_not_production(tmp_path / "workspace_chat.sqlite")
    with pytest.raises(ProductionWriteRefusedError):
        assert_not_production(tmp_path / "error_cases_dict.db")
    with pytest.raises(ProductionWriteRefusedError):
        assert_not_production(tmp_path / "staging_enrichment.sqlite",
                              [tmp_path / "staging_enrichment.sqlite"])
    # Staging name itself is fine.
    assert_not_production(tmp_path / "staging_enrichment.sqlite")


def test_conflicting_claims_are_marked_not_resolved(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = tmp_path / "answers.jsonl"
    first = _answer_dict(payloads[0], answer_text="Đo được điện áp khởi động là 21.6V, dưới ngưỡng nên kết luận H2 đúng, cơ chế A tới B tới C rõ ràng.")
    second = _answer_dict(payloads[1], answer_text="Đo được điện áp khởi động là 24.0V, trên ngưỡng nên kết luận H1 đúng, cơ chế A tới B tới C rõ ràng.")
    with answers_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(first, ensure_ascii=False) + "\n")
        handle.write(json.dumps(second, ensure_ascii=False) + "\n")
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.claims_created == 2
    assert report.conflicted_claims >= 1
    conn = sqlite3.connect(str(staging))
    try:
        statuses = [row[0] for row in conn.execute("SELECT status FROM staging_claims")]
        assert "conflicted" in statuses
        escalations = [row[0] for row in conn.execute(
            "SELECT escalation_id FROM staging_claims WHERE status = 'conflicted'")]
        assert all(e for e in escalations)
    finally:
        conn.close()


def test_record_expert_feedback_flips_status_with_responsibility(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = _write_answers(tmp_path, payloads, [0])
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 1
    answer_id = "GA-%s-1" % payloads[0]["question"]["question_id"]

    with pytest.raises(Exception):
        # Responsibility confirmation is mandatory.
        record_expert_feedback(
            staging, answer_id, reviewer="Chuyên gia A", confidence=0.9,
            sources_checked="SOP-12", responsibility_confirmed=False,
            corrections={"perm_countermeasure": "Thay nguồn dự phòng"},
        )

    result = record_expert_feedback(
        staging, answer_id, reviewer="Chuyên gia A", confidence=0.9,
        sources_checked="SOP-12", responsibility_confirmed=True,
        corrections={"perm_countermeasure": "Thay nguồn dự phòng"},
    )
    assert result["reviewer_status"] == "chuyen_gia_da_phan_hoi"
    assert result["new_version"] == 2
    conn = sqlite3.connect(str(staging))
    try:
        row = conn.execute(
            "SELECT reviewer_status, version, payload_json FROM staging_answers WHERE answer_id = ?",
            (answer_id,),
        ).fetchone()
        assert row[0] == "chuyen_gia_da_phan_hoi"
        assert row[1] == 2
        assert "Thay nguồn dự phòng" in row[2]
        reviews = conn.execute("SELECT COUNT(*) FROM expert_reviews").fetchone()[0]
        assert reviews == 1
    finally:
        conn.close()


def test_duplicate_answer_id_with_different_text_is_error_not_crash(tmp_path: Path, batch_files):
    exported, payloads = batch_files
    answers_path = tmp_path / "answers.jsonl"
    first = _answer_dict(payloads[0])
    second = _answer_dict(payloads[0])
    second["answer_text"] = "Nội dung khác hẳn cho cùng answer_id, cơ chế A tới B tới C vẫn đầy đủ chi tiết."
    with answers_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(first, ensure_ascii=False) + "\n")
        handle.write(json.dumps(second, ensure_ascii=False) + "\n")
    staging = tmp_path / "staging_enrichment.sqlite"
    report = import_batch_answers(answers_path, exported.manifest_path, staging)
    assert report.imported == 1
    assert len(report.errors) == 1
    assert "đã tồn tại" in report.errors[0]["reason"]


def test_dedup_key_normalization():
    assert dedup_key("Q1", "  Đo  ĐIỆN áp  ") == dedup_key("Q1", "đo điện áp")
    assert dedup_key("Q1", "text a") != dedup_key("Q2", "text a")
