"""Unit tests for feedback_sma_pipeline and anti-duplicate Windows voting logic.

Covers:
- Question normalization and hashing
- Windows identity deduplication (1 user 1 vote per message, updates on re-vote)
- Mandatory reason categories on dislike ('sai', 'kho_hieu', 'thieu_nguon', 'lac_de')
- SMA(20) window calculation and thresholds (Dislike >= 3 & 30%, Like >= 5 & 85%)
- Aggregation across 3 axes: query cluster, source document, domain
- Execution performance benchmark (< 50ms)
- Markdown report generation
"""

import time
from pathlib import Path

import pytest

from aios_habit.answer_feedback import (
    RATING_CHUA_HUU_ICH,
    RATING_HUU_ICH,
    REASON_CATEGORIES,
    REASON_CAT_KHO_HIEU,
    REASON_CAT_LAC_DE,
    REASON_CAT_SAI,
    REASON_CAT_THIEU_NGUON,
    AnswerFeedbackRecord,
    compute_question_hash,
    feedback_file,
    get_feedback,
    get_windows_identity,
    record_feedback,
)
from aios_habit.feedback_sma_pipeline import (
    DEFAULT_SMA_WINDOW,
    STATUS_ALERT_EXPERT,
    STATUS_KNOWLEDGE_CANDIDATE,
    STATUS_STABLE,
    compute_feedback_sma_pipeline,
    evaluate_sma_window,
    format_sma_pipeline_summary_markdown,
)


@pytest.fixture(autouse=True)
def _isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    yield


def test_question_hash_deterministic():
    q1 = "Lỗi C7620 xử lý thế nào?"
    q2 = "  lỗi c7620  xử lý thế nào? \n"
    h1 = compute_question_hash(q1)
    h2 = compute_question_hash(q2)
    assert len(h1) == 16
    assert h1 == h2
    assert compute_question_hash("") == ""


def test_anti_duplicate_vote_replaces_existing():
    # User votes like
    res1 = record_feedback(
        conversation_id="conv-1",
        message_id="msg-1",
        question="C7620 la loi gi?",
        answer="La loi camera",
        rating="huu_ich",
        user_id=r"DOMAIN\alice",
    )
    assert res1["ok"] is True
    assert "updated" not in res1 or res1.get("updated") is False

    stored1 = get_feedback("conv-1", "msg-1", user_id=r"DOMAIN\alice")
    assert stored1 is not None
    assert stored1["rating"] == "huu_ich"
    created_at = stored1["created_at"]

    # Same user changes mind: votes dislike with mandatory reason
    res2 = record_feedback(
        conversation_id="conv-1",
        message_id="msg-1",
        question="C7620 la loi gi?",
        answer="La loi camera",
        rating="chua_huu_ich",
        reason_category=REASON_CAT_SAI,
        reason="Sai ma loi roi, phai la loi motor",
        user_id=r"DOMAIN\alice",
    )
    assert res2["ok"] is True
    assert res2.get("updated") is True

    # File must contain exactly 1 record, not 2
    raw_lines = [
        line.strip()
        for line in feedback_file().read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(raw_lines) == 1

    stored2 = get_feedback("conv-1", "msg-1", user_id=r"DOMAIN\alice")
    assert stored2["rating"] == "chua_huu_ich"
    assert stored2["reason_category"] == REASON_CAT_SAI
    assert stored2["reason"] == "Sai ma loi roi, phai la loi motor"
    assert stored2["created_at"] == created_at  # Preserves initial creation timestamp
    assert stored2["updated_at"] != ""  # Has update timestamp


def test_different_users_vote_on_same_message():
    record_feedback(
        conversation_id="conv-1",
        message_id="msg-10",
        question="DMT PMT la gi?",
        answer="Giai thich...",
        rating="huu_ich",
        user_id=r"DOMAIN\user1",
    )
    record_feedback(
        conversation_id="conv-1",
        message_id="msg-10",
        question="DMT PMT la gi?",
        answer="Giai thich...",
        rating="chua_huu_ich",
        reason_category=REASON_CAT_KHO_HIEU,
        reason="Dung thuat ngu qua kho hieu",
        user_id=r"DOMAIN\user2",
    )

    raw_lines = [
        line.strip()
        for line in feedback_file().read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(raw_lines) == 2

    fb1 = get_feedback("conv-1", "msg-10", user_id=r"DOMAIN\user1")
    fb2 = get_feedback("conv-1", "msg-10", user_id=r"DOMAIN\user2")
    assert fb1["rating"] == "huu_ich"
    assert fb2["rating"] == "chua_huu_ich"
    assert fb2["reason_category"] == REASON_CAT_KHO_HIEU


def test_dislike_requires_valid_reason_category():
    # Empty reason and empty category must fail
    res_empty = record_feedback(
        "conv", "msg", "q", "a", "chua_huu_ich", reason_category="", reason="", user_id="u"
    )
    assert res_empty["ok"] is False

    # Invalid category must fail
    res_invalid = record_feedback(
        "conv",
        "msg",
        "q",
        "a",
        "chua_huu_ich",
        reason_category="tuy_tien",
        reason="che cho vui",
        user_id="u",
    )
    assert res_invalid["ok"] is False
    assert "Nhóm lý do không hợp lệ" in res_invalid["error_vi"]

    # All 4 valid categories must succeed
    for cat in (
        REASON_CAT_SAI,
        REASON_CAT_KHO_HIEU,
        REASON_CAT_THIEU_NGUON,
        REASON_CAT_LAC_DE,
    ):
        res_valid = record_feedback(
            "conv",
            f"msg_{cat}",
            "q",
            "a",
            "chua_huu_ich",
            reason_category=cat,
            reason=f"Ly do cho {cat}",
            user_id="u",
        )
        assert res_valid["ok"] is True


def test_sma20_single_dislike_does_not_trigger_alert():
    # 2 Dislikes and 4 Likes among 6 votes (neither alert nor candidate)
    records = []
    for i in range(4):
        records.append(
            AnswerFeedbackRecord(
                conversation_id="conv",
                message_id=f"msg_{i}",
                user_id=f"user_{i}",
                question="Q1",
                question_hash="h1",
                answer_excerpt="A1",
                rating=RATING_HUU_ICH,
            )
        )
    for i in range(2):
        records.append(
            AnswerFeedbackRecord(
                conversation_id="conv",
                message_id=f"msg_dislike_{i}",
                user_id=f"user_dis_{i}",
                question="Q1",
                question_hash="h1",
                answer_excerpt="A1",
                rating=RATING_CHUA_HUU_ICH,
                reason_category=REASON_CAT_SAI,
                reason="Sai mot chi tiet nho",
            )
        )

    res = evaluate_sma_window(records, dimension="query_cluster", key="h1")
    assert res.sample_count == 6
    assert res.like_count == 4
    assert res.dislike_count == 2
    assert round(res.dislike_ratio, 2) == 0.33
    # Dislike count is 2 (< 3), so even though ratio >= 30%, it does NOT alert
    assert res.is_alert is False
    assert res.is_candidate is False
    assert res.status == STATUS_STABLE


def test_sma20_negative_threshold_triggers_alert():
    # 3 Dislikes out of 8 votes = 37.5% (>= 30% and >= 3 dislikes) -> triggers ALERT_EXPERT_REVIEW
    records = []
    for i in range(5):
        records.append(
            AnswerFeedbackRecord(
                conversation_id="conv",
                message_id=f"msg_{i}",
                user_id=f"user_{i}",
                question="Loi lech truc Y",
                question_hash="hash_y",
                answer_excerpt="Huong dan...",
                rating=RATING_HUU_ICH,
            )
        )
    for i in range(3):
        records.append(
            AnswerFeedbackRecord(
                conversation_id="conv",
                message_id=f"msg_bad_{i}",
                user_id=f"user_bad_{i}",
                question="Loi lech truc Y",
                question_hash="hash_y",
                answer_excerpt="Huong dan...",
                rating=RATING_CHUA_HUU_ICH,
                reason_category=REASON_CAT_SAI if i < 2 else REASON_CAT_THIEU_NGUON,
                reason="Huong dan sai buoc thuc hien",
            )
        )

    res = evaluate_sma_window(records, dimension="query_cluster", key="hash_y")
    assert res.sample_count == 8
    assert res.like_count == 5
    assert res.dislike_count == 3
    assert res.dislike_ratio == 0.375
    assert res.is_alert is True
    assert res.status == STATUS_ALERT_EXPERT
    assert res.reason_counts[REASON_CAT_SAI] == 2
    assert res.reason_counts[REASON_CAT_THIEU_NGUON] == 1


def test_sma20_positive_threshold_triggers_candidate():
    # 6 Likes out of 6 votes (100% >= 85% and >= 5 likes) -> KNOWLEDGE_CANDIDATE
    records = []
    for i in range(6):
        records.append(
            AnswerFeedbackRecord(
                conversation_id="conv",
                message_id=f"msg_good_{i}",
                user_id=f"user_good_{i}",
                question="Quy trinh can chinh Sensor 3D",
                question_hash="hash_sensor",
                answer_excerpt="Chi tiet 4 buoc can...",
                rating=RATING_HUU_ICH,
            )
        )

    res = evaluate_sma_window(records, dimension="query_cluster", key="hash_sensor")
    assert res.sample_count == 6
    assert res.like_count == 6
    assert res.dislike_count == 0
    assert res.like_ratio == 1.0
    assert res.is_candidate is True
    assert res.status == STATUS_KNOWLEDGE_CANDIDATE


def test_sma20_three_axes_aggregation():
    # Records with different questions, cited sources, and domains
    records = [
        AnswerFeedbackRecord(
            conversation_id="c1",
            message_id="m1",
            user_id="u1",
            question="Cau hoi 1",
            question_hash="q1",
            answer_excerpt="A1",
            rating=RATING_HUU_ICH,
            cited_sources=["HDSD_May_A.pdf", "So_Do_Dien.pdf"],
            domain="BaoTri",
        ),
        AnswerFeedbackRecord(
            conversation_id="c1",
            message_id="m2",
            user_id="u2",
            question="Cau hoi 1",
            question_hash="q1",
            answer_excerpt="A1",
            rating=RATING_CHUA_HUU_ICH,
            reason_category=REASON_CAT_THIEU_NGUON,
            reason="Thieu bang tra ma",
            cited_sources=["HDSD_May_A.pdf"],
            domain="BaoTri",
        ),
        AnswerFeedbackRecord(
            conversation_id="c2",
            message_id="m3",
            user_id="u3",
            question="Cau hoi 2",
            question_hash="q2",
            answer_excerpt="A2",
            rating=RATING_HUU_ICH,
            cited_sources=["QuyTrinh_KiemTra.docx"],
            domain="KCS",
        ),
    ]

    report = compute_feedback_sma_pipeline(records=records, window_size=20)
    assert report.total_raw_records == 3
    assert report.deduplicated_records == 3

    # Check axis 1: query cluster
    assert "q1" in report.by_query_cluster
    assert "q2" in report.by_query_cluster
    assert report.by_query_cluster["q1"].sample_count == 2
    assert report.by_query_cluster["q2"].sample_count == 1

    # Check axis 2: source document
    assert "HDSD_May_A.pdf" in report.by_source_document
    assert report.by_source_document["HDSD_May_A.pdf"].sample_count == 2
    assert "So_Do_Dien.pdf" in report.by_source_document
    assert report.by_source_document["So_Do_Dien.pdf"].sample_count == 1

    # Check axis 3: domain
    assert "BaoTri" in report.by_domain
    assert "KCS" in report.by_domain
    assert report.by_domain["BaoTri"].sample_count == 2
    assert report.by_domain["KCS"].sample_count == 1


def test_sma20_performance_under_50ms():
    # Generate 1,000 synthetic feedback records
    records = []
    categories = list(REASON_CATEGORIES)
    for i in range(1000):
        is_like = (i % 3) != 0
        q_idx = i % 25
        doc_idx = i % 15
        dom_idx = i % 5
        records.append(
            AnswerFeedbackRecord(
                conversation_id=f"conv_{i % 50}",
                message_id=f"msg_{i}",
                user_id=f"DOMAIN\\user_{i % 100}",
                question=f"Cau hoi kiem thu so {q_idx}",
                question_hash=f"hash_{q_idx}",
                answer_excerpt=f"Cau tra loi chi tiet cho cau hoi {q_idx}...",
                rating=RATING_HUU_ICH if is_like else RATING_CHUA_HUU_ICH,
                reason_category="" if is_like else categories[i % len(categories)],
                reason="" if is_like else "Giai thich van de",
                cited_sources=[f"TaiLieu_{doc_idx}.pdf", f"PhuLuc_{doc_idx+1}.pdf"],
                domain=f"Mien_Nghiep_Vu_{dom_idx}",
            )
        )

    t0 = time.perf_counter()
    report = compute_feedback_sma_pipeline(records=records, window_size=20)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert report.deduplicated_records == 1000
    assert report.calculation_time_ms < 50.0, f"SMA pipeline took {report.calculation_time_ms}ms, expected < 50ms"
    assert duration_ms < 50.0, f"Total execution took {duration_ms}ms, expected < 50ms"


def test_format_sma_pipeline_summary_markdown():
    records = [
        AnswerFeedbackRecord(
            conversation_id="c1",
            message_id=f"m_{i}",
            user_id=f"u_{i}",
            question="Can chinh sensor?",
            question_hash="h_sens",
            answer_excerpt="Cac buoc...",
            rating=RATING_HUU_ICH,
        )
        for i in range(6)
    ]
    report = compute_feedback_sma_pipeline(records=records)
    md = format_sma_pipeline_summary_markdown(report)
    assert "Phân Tích Xu Hướng Phản Hồi SMA(20)" in md
    assert "Hàng Đợi Cảnh Báo Chuyên Gia" in md
    assert "Ứng Viên Tri Thức Chuẩn" in md
    assert "Can chinh sensor?" in md
    assert "ms" in md
