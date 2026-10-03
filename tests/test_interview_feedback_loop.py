"""Tests cho UX-INTERVIEW-FEEDBACK items 1-3 (backend, du lieu mau).

1. Phien phong van chuyen gia: gap -> cau hoi vang (tai dung bo sinh
   deterministic cua pilot) -> dap an vao form nhan qua chuan -> luu
   staging (sqlite rieng, cam ghi production).
2. Feedback tung goi y: dung/sai/mot_phan; sai/mot_phan thieu 3 truong
   thi raise ValueError; luu local_cases, khong vao kho tri thuc.
3. Vong lap tu cai thien: bai hoc co truy vet, nhan dien tinh huong
   tuong tu bang tu khoa, metric ti le lap lai loi giam dan theo thoi gian.

Tat ca test dung AIOS_LOCAL_CASES_DIR -> tmp_path: khong cham vao
local_cases that, DB that, hay index production.
"""

import json
import sqlite3

import pytest

from aios_habit import self_improvement, suggestion_feedback
from aios_habit.expert_interview_session import (
    SESSION_ACTIVE,
    SESSION_COMPLETED,
    InterviewSessionError,
    abandon_session,
    answer_question,
    complete_session,
    session_summary,
    start_session,
    unanswered_questions,
)
from aios_habit.golden_answer_importer import ProductionWriteRefusedError
from aios_habit.golden_question_export import fixture_phenomena
from aios_habit.self_improvement import (
    LessonStore,
    consult_lessons,
    improvement_overview,
    keyword_jaccard,
    lesson_from_suggestion_feedback,
    metric_trend,
    record_repetition_event,
    repetition_rates,
    situation_fingerprint,
    situation_keywords,
)
from aios_habit.suggestion_feedback import (
    SuggestionFeedbackStrictError,
    record_feedback_strict,
)


@pytest.fixture(autouse=True)
def _isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    yield


# ---------------------------------------------------------------------------
# Item 1: phien phong van chuyen gia
# ---------------------------------------------------------------------------

def _answer_payload(question, confidence=0.8, state="answered"):
    """Dap an hop le theo form nhan qua chuan (GoldenAnswer)."""
    base = {
        "answer_text": "Cơ chế gây lỗi đã xác minh qua log jig và ảnh hiện trường, đủ 20 ký tự.",
        "answer_state": state,
        "confidence": confidence,
        "hypotheses": ["Board điều khiển bị nhiễu nguồn"],
        "causal_mechanism": "Nhiễu nguồn -> reset vi xử lý -> dừng máy đột ngột",
        "m4_branches": ["Machine"],
        "evidence_to_collect": ["Log jig 3 ngày gần nhất", "Ảnh board"],
        "confirm_criteria": "Tái hiện lỗi khi cấp nguồn nhiễu mô phỏng",
    }
    if question is not None and question.loai_cau_hoi == "discriminator":
        base["discriminate_notes"] = (
            "Phân biệt với giả thuyết board hỏng: đo nguồn cấp, nếu nhiễu "
            "thì lỗi theo nguồn, không theo board."
        )
    if state != "answered" or confidence < 0.7:
        base["needs_expert_review"] = ["causal_mechanism"]
    return base


def test_session_gap_to_questions_reuses_pilot_generator():
    ctx = fixture_phenomena("TEST-IS-01")[0]
    session = start_session(ctx, questions_per_session=3)
    assert session.status == SESSION_ACTIVE
    # select_top_k co the tra VE NHIEU HON k khi can bu dap rang buoc cung
    # (discriminator / bang chung do duoc / du 3 nhanh 4M) — hanh vi cua pilot.
    assert len(session.questions) >= 1
    assert all(q.diem > 0 for q in session.questions)
    # Moi cau hoi deu noi ve gap va case that cua context.
    for q in session.questions:
        assert q.target_gap_id
        assert q.target_case_ids
    assert unanswered_questions(session) == session.questions


def test_session_answer_validation_rejects_vague_form():
    ctx = fixture_phenomena("TEST-IS-02")[0]
    session = start_session(ctx, questions_per_session=2)
    q = session.questions[0]
    vague = {"answer_text": "Chắc do board hỏng gì đó, cần kiểm tra thêm.", "answer_state": "answered", "confidence": 0.9}
    with pytest.raises(InterviewSessionError):
        answer_question(session, q.question_id, vague)
    # Cau hoi van chua co dap an hop le.
    assert q in unanswered_questions(session)


def test_session_complete_writes_staging_only(tmp_path):
    ctx = fixture_phenomena("TEST-IS-03")[0]
    session = start_session(ctx, questions_per_session=2)
    for q in session.questions:
        answer_question(session, q.question_id, _answer_payload(q))
    staging = tmp_path / "staging_enrichment.sqlite"
    report = complete_session(session, staging_path=staging)
    assert report["status"] == SESSION_COMPLETED
    assert report["dedup_skipped"] == 0
    assert len(report["stored_answer_ids"]) == len(session.questions)
    # Doc lai tu staging: dap an nam dung bang, trang thai cho duyet.
    conn = sqlite3.connect(str(staging))
    try:
        rows = conn.execute(
            "SELECT answer_id, question_id, reviewer_status FROM staging_answers"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == len(session.questions)
    assert {r[2] for r in rows} == {"cho_chuyen_gia_phan_hoi"}
    assert session.status == SESSION_COMPLETED


def test_session_complete_requires_all_questions_answered():
    ctx = fixture_phenomena("TEST-IS-04")[0]
    session = start_session(ctx, questions_per_session=2)
    # Tra loi tat ca tru cau cuoi -> con thieu -> khong cho hoan thanh.
    for q in session.questions[:-1]:
        answer_question(session, q.question_id, _answer_payload(q))
    with pytest.raises(InterviewSessionError):
        complete_session(session, staging_path=None)


def test_session_complete_refuses_production_path(tmp_path):
    ctx = fixture_phenomena("TEST-IS-05")[0]
    session = start_session(ctx, questions_per_session=1)
    for q in session.questions:
        answer_question(session, q.question_id, _answer_payload(q))
    prod = tmp_path / "workspace_chat.sqlite"
    with pytest.raises(ProductionWriteRefusedError):
        complete_session(session, staging_path=prod)


def test_session_abandon_blocks_further_answers():
    ctx = fixture_phenomena("TEST-IS-06")[0]
    session = start_session(ctx, questions_per_session=1)
    abandon_session(session)
    with pytest.raises(InterviewSessionError):
        answer_question(session, session.questions[0].question_id, _answer_payload(session.questions[0]))


def test_session_summary_for_future_ui():
    ctx = fixture_phenomena("TEST-IS-07")[0]
    session = start_session(ctx, questions_per_session=2)
    summary = session_summary(session)
    assert summary["total_questions"] == len(session.questions) >= 1
    assert summary["answered"] == 0
    assert len(summary["remaining_question_ids"]) == len(session.questions)


def test_session_dedup_on_double_complete_same_content(tmp_path):
    ctx = fixture_phenomena("TEST-IS-08")[0]
    staging = tmp_path / "staging_enrichment.sqlite"
    s1 = start_session(ctx, questions_per_session=1)
    payloads = {}
    for q in s1.questions:
        payload = _answer_payload(q)
        payloads[q.question_id] = payload
        answer_question(s1, q.question_id, payload)
    complete_session(s1, staging_path=staging)
    # Phien moi, cung cau hoi, cung noi dung dap an -> dedup bo qua.
    s2 = start_session(ctx, questions_per_session=1)
    assert [q.question_id for q in s2.questions] == [q.question_id for q in s1.questions]
    for q in s2.questions:
        answer_question(s2, q.question_id, payloads[q.question_id])
    report = complete_session(s2, staging_path=staging)
    assert report["dedup_skipped"] == len(s2.questions)


# ---------------------------------------------------------------------------
# Item 2: feedback tung goi y
# ---------------------------------------------------------------------------

def test_strict_dung_needs_no_fields(tmp_path):
    result = record_feedback_strict("G1", "chuyen-gia-a", "dung")
    assert result["ok"] is True
    path = suggestion_feedback.feedback_file()
    assert path.name == "suggestion_feedback.jsonl"
    assert str(tmp_path) in str(path)  # luu local_cases, khong phai kho tri thuc


def test_strict_sai_missing_fields_raises_value_error():
    with pytest.raises(ValueError) as exc_info:
        record_feedback_strict("G2", "chuyen-gia-a", "sai", reason="Sai hẳn")
    assert "nguyên nhân thật" in str(exc_info.value)
    assert "nội dung nắn lại" in str(exc_info.value)
    # Tu choi luu: khong co ban ghi nao.
    assert suggestion_feedback.get_feedback("G2") == []


def test_strict_mot_phan_missing_one_field_raises():
    with pytest.raises(SuggestionFeedbackStrictError):
        record_feedback_strict(
            "G3", "chuyen-gia-a", "mot_phan",
            reason="Đúng một nửa", nguyen_nhan_that="Do nhiễu nguồn",
        )


def test_strict_sai_full_three_fields_saved():
    result = record_feedback_strict(
        "G4", "chuyen-gia-a", "sai",
        reason="Gợi ý thay board là sai",
        true_cause="Nhiễu nguồn cấp cho board điều khiển",
        correction="Kiểm tra nguồn cấp và chống nhiễu trước khi thay board",
    )
    assert result["ok"] is True
    stored = suggestion_feedback.get_feedback("G4")
    assert len(stored) == 1
    assert stored[0]["true_cause"] == "Nhiễu nguồn cấp cho board điều khiển"


def test_strict_invalid_verdict_raises():
    with pytest.raises(SuggestionFeedbackStrictError):
        record_feedback_strict("G5", "chuyen-gia-a", "tam_duoc", reason="x")


def test_lesson_requires_full_three_fields():
    incomplete = {"verdict": "sai", "reason": "Sai", "true_cause": "", "correction": "x"}
    with pytest.raises(ValueError):
        lesson_from_suggestion_feedback(incomplete, situation_text="Máy dừng F100")


# ---------------------------------------------------------------------------
# Item 3: vong lap tu cai thien
# ---------------------------------------------------------------------------

def _full_feedback(suggestion_id="G10"):
    return {
        "type": "feedback",
        "suggestion_id": suggestion_id,
        "verdict": "sai",
        "reason": "Gợi ý thay board là sai, tốn chi phí",
        "true_cause": "Nhiễu nguồn cấp cho board điều khiển",
        "correction": "Kiểm tra nguồn cấp và chống nhiễu trước khi thay board",
        "content": "Máy dừng đột ngột báo F100 khi đang chạy, nghi board hỏng",
        "context": "line A, model X",
    }


def test_lesson_from_feedback_has_traceability():
    lesson = lesson_from_suggestion_feedback(_full_feedback())
    assert lesson.lesson_id.startswith("LES-")
    assert lesson.situation_fingerprint
    assert "board" in lesson.keywords
    # Truy vet: tinh huong -> loi -> cach sua.
    assert "F100" in lesson.situation_text or "dừng" in lesson.situation_text
    assert lesson.loi
    assert lesson.nguyen_nhan
    assert lesson.cach_sua
    assert lesson.source_suggestion_id == "G10"


def test_fingerprint_stable_and_keyword_similarity():
    a = "Máy dừng đột ngột báo F100, nghi board điều khiển hỏng"
    # Cung tap tu khoa, chi dao thu tu -> cung fingerprint (on dinh).
    b = "báo F100 máy dừng đột ngột hỏng board điều khiển nghi"
    c = "Băng tải kẹt sản phẩm tại vị trí chuyển tiếp"
    assert situation_fingerprint(a) == situation_fingerprint(b)
    assert situation_fingerprint(a) != situation_fingerprint(c)
    assert keyword_jaccard(situation_keywords(a), situation_keywords(b)) == 1.0
    assert keyword_jaccard(situation_keywords(a), situation_keywords(c)) < 0.3


def test_find_similar_lesson_before_answering():
    store = LessonStore()
    store.add(lesson_from_suggestion_feedback(_full_feedback("G11")))
    hits = store.find_similar("Máy F100 dừng đột ngột giữa ca, nghi board")
    assert hits, "phai nhan dien duoc tinh huong tuong tu"
    lesson, score = hits[0]
    assert score >= 0.3
    assert lesson.source_suggestion_id == "G11"
    # Tinh huong khac han thi khong nhan.
    assert store.find_similar("Nhiệt độ buồng sấy vượt ngưỡng cài đặt") == []


def test_consult_lessons_ui_payload():
    store = LessonStore()
    store.add(lesson_from_suggestion_feedback(_full_feedback("G12")))
    payload = consult_lessons("Máy dừng F100 đột ngột", store=store)
    assert len(payload) == 1
    item = payload[0]
    assert "cach_sua" in item and "loi_truoc_day" in item


def test_repetition_metric_decreases_over_time():
    # Du lieu mau: tuan dau lap lai nhieu, cac tuan sau giam dan.
    events = []
    plan = [("2026-09-07", 8, 10), ("2026-09-14", 5, 10), ("2026-09-21", 2, 10), ("2026-09-28", 1, 10)]
    for period, repeated, total in plan:
        for i in range(total):
            events.append(
                {"period": period, "verdict": "sai", "repeated": i < repeated}
            )
    rates = repetition_rates(events)
    assert [r["ti_le"] for r in rates] == [0.8, 0.5, 0.2, 0.1]
    assert metric_trend(rates) == "giam_dan"


def test_repetition_metric_flat_is_not_improving():
    events = [
        {"period": "2026-09-07", "verdict": "sai", "repeated": True},
        {"period": "2026-09-07", "verdict": "sai", "repeated": False},
        {"period": "2026-09-14", "verdict": "mot_phan", "repeated": True},
        {"period": "2026-09-14", "verdict": "mot_phan", "repeated": True},
    ]
    rates = repetition_rates(events)
    assert metric_trend(rates) == "khong_giam"


def test_repetition_metric_needs_two_periods():
    assert metric_trend([]) == "khong_du_du_lieu"
    assert metric_trend([{"ky": "2026-09-07", "ti_le": 0.5}]) == "khong_du_du_lieu"


def test_metric_end_to_end_with_recorded_events(tmp_path):
    metrics_path = tmp_path / "improvement_metrics.jsonl"
    record_repetition_event("G20", "sai", True, period="2026-09-07", path=metrics_path)
    record_repetition_event("G21", "sai", False, period="2026-09-07", path=metrics_path)
    record_repetition_event("G22", "sai", False, period="2026-09-14", path=metrics_path)
    record_repetition_event("G23", "sai", False, period="2026-09-14", path=metrics_path)
    overview = improvement_overview(path=metrics_path)
    assert overview["xu_huong"] == "giam_dan"
    assert overview["ti_le_lap_lai_theo_ky"][0]["ti_le"] == 0.5
    assert overview["ti_le_lap_lai_theo_ky"][1]["ti_le"] == 0.0
    # File metric nam trong local_cases (tmp), khong phai kho tri thuc.
    assert metrics_path.exists()


def test_feedback_and_lesson_files_stay_in_local_cases(tmp_path):
    record_feedback_strict(
        "G30", "cg", "mot_phan", reason="r", true_cause="c", correction="s"
    )
    store = LessonStore()
    store.add(lesson_from_suggestion_feedback(_full_feedback("G30")))
    for name in ("suggestion_feedback.jsonl", "improvement_lessons.jsonl"):
        path = tmp_path / name
        assert path.exists(), name
        # Noi dung la du lieu van hanh, khong phai tri thuc da duyet.
        first = path.read_text(encoding="utf-8").splitlines()[0]
        record = json.loads(first)
        assert "enrichment_label" not in record
        assert record.get("reviewer_status", "cho_chuyen_gia_phan_hoi") != "chuyen_gia_da_phan_hoi"
