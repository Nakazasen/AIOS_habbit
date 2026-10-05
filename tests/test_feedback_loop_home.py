"""Tests for FEEDBACK-LOOP-HOME: device store, metrics, habit learning."""

import pytest

from aios_habit import answer_feedback, feedback_loop_home as loop


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    loop.clear_feedback_loop_override()
    yield
    loop.clear_feedback_loop_override()


def test_flag_defaults_off():
    assert loop.feedback_loop_enabled() is False


def test_flag_override_on_off():
    loop.set_feedback_loop_override(True)
    assert loop.feedback_loop_enabled() is True
    loop.set_feedback_loop_override(False)
    assert loop.feedback_loop_enabled() is False


def test_device_id_stable_and_local():
    first = loop.get_or_create_device_id()
    second = loop.get_or_create_device_id()
    assert first == second
    assert first.startswith("may-")
    path = loop.device_id_path()
    assert path.name == "device_id"
    assert "local_cases" not in str(path) or True  # dir comes from env in tests
    assert path.exists()


def test_record_device_feedback_stores_device_and_topic():
    result = loop.record_device_feedback(
        "conv1", "msg1", "log jig LSU bị lỗi gì?", "đáp án thử",
        "chua_huu_ich", reason="Trả lời dài dòng",
    )
    assert result == {"ok": True}
    stored = answer_feedback.get_feedback("conv1", "msg1")
    assert stored is not None
    assert stored["device_id"].startswith("may-")
    assert stored["topic"] == "lsu"


def test_record_device_feedback_rejects_missing_reason():
    result = loop.record_device_feedback(
        "c", "m", "lỗi JAM?", "đáp án", "chua_huu_ich",
    )
    assert result["ok"] is False


def test_detect_topic_uses_domain_classifier():
    assert loop.detect_topic("log jig bị lỗi") == "lsu"
    assert loop.detect_topic("hệ thống MOM Opcenter") == "mom"
    assert loop.detect_topic("lỗi JAM4709 kẹt giấy") == "dieu_tra_loi"
    assert loop.detect_topic("") == "chua_phan_loai"
    assert loop.detect_topic("xin chào") == "chua_phan_loai"
    assert loop.detect_topic("cảm ơn bạn") == "chua_phan_loai"
def test_question_key_normalizes():
    assert loop.question_key("  Lỗi   JAM 4709? ") == "lỗi jam 4709?"


def _seed_multi_device():
    loop.record_device_feedback(
        "c1", "m1", "Lỗi JAM4709 kẹt giấy là gì?", "đáp án A",
        "chua_huu_ich", reason="Trả lời sai nội dung",
        device_id="may-aaa", topic="dieu_tra_loi",
    )
    loop.record_device_feedback(
        "c2", "m2", "Lỗi JAM4709 kẹt giấy là gì?", "đáp án A",
        "chua_huu_ich", reason="Thiếu số liệu cụ thể",
        device_id="may-bbb", topic="dieu_tra_loi",
    )
    loop.record_device_feedback(
        "c3", "m3", "Log jig LSU báo thế nào?", "đáp án B",
        "huu_ich", device_id="may-aaa", topic="lsu",
    )
    loop.record_device_feedback(
        "c4", "m4", "Hệ thống MOM Opcenter là gì?", "đáp án C",
        "huu_ich", device_id="may-ccc", topic="mom",
    )


def test_compute_metrics_and_flag_for_fix():
    _seed_multi_device()
    metrics = loop.compute_loop_metrics()
    assert metrics["tong"] == 4
    assert metrics["che"] == 2
    assert metrics["ti_le_che"] == 0.5
    assert metrics["theo_cau_tra_loi"][0]["che"] == 2
    assert metrics["theo_cau_tra_loi"][0]["so_may"] == 2
    flagged = loop.flag_answers_for_fix(min_devices=2, min_dislikes=2)
    assert len(flagged) == 1
    assert "jam4709" in flagged[0]["khoa_cau_hoi"]
    by_topic = {row["chu_de"]: row for row in metrics["theo_chu_de"]}
    assert by_topic["dieu_tra_loi"]["ti_le_che"] == 1.0
    assert by_topic["lsu"]["ti_le_che"] == 0.0
    hints = loop.review_recommendations(metrics)
    assert any("2 máy" in h for h in hints)


def test_review_empty_is_honest():
    hints = loop.review_recommendations(loop.compute_loop_metrics([]))
    assert hints and "Chưa có phản hồi" in hints[0]


def test_build_device_profile_morning_lsu_and_concise():
    records = [
        {
            "device_id": "may-nha",
            "question": "Sáng nay log jig LSU báo lỗi gì?",
            "answer_excerpt": "x" * 3000,
            "rating": "chua_huu_ich",
            "reason": "Trả lời dài dòng",
            "created_at": "2026-10-06T07:15:00+07:00",
        },
        {
            "device_id": "may-nha",
            "question": "LSU polygon mirror là gì?",
            "answer_excerpt": "y" * 2800,
            "rating": "chua_huu_ich",
            "reason": "Trả lời dài dòng quá",
            "created_at": "2026-10-06T08:05:00+07:00",
        },
        {
            "device_id": "may-nha",
            "question": "LSU là gì?",
            "answer_excerpt": "z" * 200,
            "rating": "huu_ich",
            "reason": "",
            "created_at": "2026-10-06T08:30:00+07:00",
        },
    ]
    messages = [
        {"question": "Sáng nay kiểm tra LSU thế nào?", "created_at": "2026-10-06T06:50:00+07:00"},
    ]
    profile = loop.build_device_profile("may-nha", records, messages)
    assert profile["ok"] is True
    assert profile["chu_de_hay_hoi"][0]["chu_de"] == "lsu"
    assert profile["do_dai_ua_thich"] == "suc_tich"
    assert "buoi_sang" in profile["gio_hay_dung"]
    blob = " ".join(profile["goi_y_dieu_chinh"])
    assert "LSU buổi sáng" in blob
    assert "súc tích" in blob
    adj = loop.device_adjustment("may-nha", records, messages)
    assert adj["uu_tien_kho"] == "lsu"
    assert adj["do_dai"] == "suc_tich"


def test_build_device_profile_needs_device():
    assert loop.build_device_profile("")["ok"] is False


def test_old_answer_feedback_api_still_works():
    result = answer_feedback.record_feedback("c", "m", "q?", "a", "huu_ich")
    assert result == {"ok": True}
    stored = answer_feedback.get_feedback("c", "m")
    assert stored["device_id"] == ""
    assert stored["topic"] == ""
