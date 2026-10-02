"""Tests cho suggestion_feedback: log goi y, cham sai/mot_phan bat buoc 3 truong."""

import pytest

from aios_habit import suggestion_feedback
from aios_habit.suggestion_feedback import (
    feedback_stats,
    get_feedback,
    get_suggestion,
    improvement_report,
    log_suggestion,
    record_feedback,
)


@pytest.fixture(autouse=True)
def _isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    yield


def test_log_suggestion_ok():
    result = log_suggestion("G1", "Kiểm tra áp suất khí nén", source="chat")
    assert result == {"ok": True, "suggestion_id": "G1"}
    assert get_suggestion("G1")["content"] == "Kiểm tra áp suất khí nén"


def test_log_suggestion_requires_id():
    assert log_suggestion("", "x")["ok"] is False


def test_feedback_dung_needs_no_fields():
    log_suggestion("G1", "x")
    assert record_feedback("G1", "chuyen_gia_a", "dung")["ok"] is True


def test_feedback_sai_requires_all_three_fields():
    log_suggestion("G1", "x")
    result = record_feedback("G1", "cg", "sai", reason="thiếu căn cứ")
    assert result["ok"] is False
    assert "nguyên nhân thật" in result["error_vi"]
    assert "nội dung nắn lại" in result["error_vi"]


def test_feedback_sai_with_all_fields_ok():
    log_suggestion("G1", "Thay board mới")
    result = record_feedback(
        "G1", "cg", "sai",
        reason="board cũ vẫn tốt",
        true_cause="lỏng cáp tín hiệu",
        correction="kiểm tra và cắm lại cáp trước khi thay board",
    )
    assert result["ok"] is True
    stored = get_feedback("G1")[0]
    assert stored["true_cause"] == "lỏng cáp tín hiệu"


def test_feedback_mot_phan_also_requires_fields():
    log_suggestion("G1", "x")
    assert record_feedback("G1", "cg", "mot_phan", reason="chỉ đúng 1 nửa")["ok"] is False
    assert (
        record_feedback(
            "G1", "cg", "mot_phan",
            reason="r", true_cause="c", correction="n",
        )["ok"]
        is True
    )


def test_invalid_verdict_rejected():
    log_suggestion("G1", "x")
    assert record_feedback("G1", "cg", "tam_duoc")["ok"] is False


def test_stats_and_improvement_report():
    log_suggestion("G1", "Gợi ý A")
    log_suggestion("G2", "Gợi ý B")
    record_feedback("G1", "cg", "dung")
    record_feedback(
        "G2", "cg", "sai",
        reason="sai hướng", true_cause="nguyên nhân X", correction="làm Y thay vì Z",
    )
    stats = feedback_stats()
    assert stats["total"] == 2
    assert stats["ti_le_dung"] == 0.5
    report = improvement_report()
    assert report["so_muc_can_xem_lai"] == 1
    item = report["can_nan_lai"][0]
    assert item["nguyen_nhan_that"] == "nguyên nhân X"
    assert item["goi_y_goc"] == "Gợi ý B"


def test_never_writes_into_knowledge(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    log_suggestion("G1", "x")
    path = suggestion_feedback.feedback_file()
    assert path.name == "suggestion_feedback.jsonl"
    assert path.parent == tmp_path


def test_chat_action_suggestion_review_renders(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    from aios_habit import suggestion_feedback
    from aios_habit.chat_action_suggestion_review import _handler
    from aios_habit.chat_action import ChatActionRequest

    suggestion_feedback.log_suggestion("G9", "Thay board mới")
    suggestion_feedback.record_feedback(
        "G9", "cg", "sai",
        reason="board còn tốt", true_cause="lỏng cáp", correction="cắm lại cáp",
    )
    outcome = _handler(ChatActionRequest(question="xem báo cáo cải thiện gợi ý", context={}))
    assert outcome is not None
    text = outcome.blocks[0].text
    assert "Tỉ lệ gợi ý đúng" in text
    assert "lỏng cáp" in text
    assert "cắm lại cáp" in text


def test_chat_action_registered():
    from aios_habit.chat_action import BUILTIN_ACTION_MODULES
    assert "aios_habit.chat_action_suggestion_review" in BUILTIN_ACTION_MODULES
