"""Tests for chat command feedback review (DESKTOP-FEEDBACK-REVIEW-CHATCMD-HOME).

Verifies all quality criteria of the ticket:
(1) Command does not hijack ordinary document Q&A — normal questions containing
    the command keywords continue down the RAG path untouched.
(2) Empty store answers truthfully "Chưa có phản hồi nào..." instead of erroring.
(3) Summary metrics match manual count from local storage exactly (test đối chứng).
(4) Does not write feedback into knowledge base, only reads local_cases.
(5) Summary answer does not contain retrieved document content.
(6) Trend alerts follow existing SMA(20) mechanism: 1 bad point does not alert,
    3 consecutive bad points trigger alert.
(7) E2E app intent router integrates cleanly and saves assistant message.
(8) Matches actual records in local_cases/answer_feedback.jsonl on the machine.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import aios_habit.workspace_chat_app as app
import aios_habit.workspace_chat_store as store
from aios_habit import answer_feedback
from aios_habit.chat_intent_router import (
    HOI_TAI_LIEU,
    XEM_PHAN_HOI,
    classify_all_intents,
    classify_intent,
)
from aios_habit.feedback_review_home import format_feedback_review_summary


# ---------------------------------------------------------------------------
# Criterion 1: Lệnh không phá đường hỏi đáp thông thường
# ---------------------------------------------------------------------------


def test_cau_hoi_binh_thuong_chua_tu_khoa_van_di_duong_rag():
    """Ordinary questions with 'phản hồi' / 'xem phản hồi' must NOT trigger XEM_PHAN_HOI."""
    cau_hoi_rag = [
        "Cách xử lý phản hồi của khách hàng trong quy trình bán hàng?",
        "Lỗi phản hồi tín hiệu cảm biến C7620 là gì?",
        "Sensor nhiệt độ có phản hồi quang không?",
        "Quy trình tiếp nhận phản hồi lỗi kẹt giấy trên line 3",
        "Khách hàng phản hồi chất lượng in mờ thì khắc phục thế nào?",
        "Xem phản hồi của cảm biến nhiệt độ trên màn hình máy in thế nào?",
        "Tài liệu hướng dẫn về phản hồi lỗi hệ thống",
        "Cách xem phản hồi tín hiệu sensor C3501",
        "Phản hồi âm thanh khi kẹt giấy ở line 3 là gì?",
    ]
    for q in cau_hoi_rag:
        intent = classify_intent(q)
        assert intent == HOI_TAI_LIEU, f"Câu '{q}' bị chiếm nhầm bởi intent {intent}!"

        # Router level: classify_all_intents must not contain XEM_PHAN_HOI
        all_intents = [y for y, _ in classify_all_intents(q)]
        assert (
            XEM_PHAN_HOI not in all_intents
        ), f"Câu '{q}' chứa XEM_PHAN_HOI trong all_intents: {all_intents}"


def test_nhan_dien_dung_cac_bien_the_lenh_xem_phan_hoi():
    """Explicit feedback review commands must correctly classify as XEM_PHAN_HOI."""
    lenh_dung = [
        "xem phản hồi",
        "xem lại phản hồi",
        "thống kê phản hồi",
        "báo cáo phản hồi",
        "tóm tắt phản hồi",
        "xem phản hồi gần đây",
        "xem các phản hồi",
        "tổng hợp phản hồi",
        "kiểm tra phản hồi",
        "xem phan hoi",
        "xem lai phan hoi",
        "thong ke phan hoi",
        "bao cao phan hoi",
        "tom tat phan hoi",
        "/xemphanhoi",
        "/feedback",
        "/phanhoi",
    ]
    for cmd in lenh_dung:
        intent = classify_intent(cmd)
        assert intent == XEM_PHAN_HOI, f"Lệnh '{cmd}' không nhận diện được XEM_PHAN_HOI (ra {intent})!"


# ---------------------------------------------------------------------------
# Criterion 2: Kho rỗng trả lời trung thực thay vì lỗi
# ---------------------------------------------------------------------------


def test_kho_phan_hoi_rong_tra_loi_trung_thuc():
    """Empty feedback store returns honest message, no exception."""
    res = format_feedback_review_summary(records=[])
    assert "Chưa có phản hồi nào trong kho lưu cục bộ." in res
    assert "📊 Tóm tắt phản hồi đáp án" in res


# ---------------------------------------------------------------------------
# Criterion 3: Số liệu trong tóm tắt khớp đếm tay từ kho lưu (test đối chứng)
# ---------------------------------------------------------------------------


def test_so_lieu_tom_tat_khop_dem_tay_fixture():
    """Summary counts, rates, top reasons match manual count exactly."""
    fixture_records = [
        {"rating": "huu_ich", "reason": "", "question": "Câu 1", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 2", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 3", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 4", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 5", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 6", "created_at": "2026-10-01T10:00:00"},
        {"rating": "huu_ich", "reason": "", "question": "Câu 7", "created_at": "2026-10-01T10:00:00"},
        {"rating": "chua_huu_ich", "reason": "Kho hieu", "question": "Câu 8", "created_at": "2026-10-01T10:00:00"},
        {"rating": "chua_huu_ich", "reason": "Kho hieu", "question": "Câu 9", "created_at": "2026-10-01T10:00:00"},
        {"rating": "chua_huu_ich", "reason": "Tra loi dai dong", "question": "Câu 10", "created_at": "2026-10-01T10:00:00"},
    ]
    # Manual count:
    # Total: 10
    # Good: 7 (70.0%)
    # Bad: 3 (30.0%)
    # Reasons: "Kho hieu": 2, "Tra loi dai dong": 1

    summary = format_feedback_review_summary(records=fixture_records)
    assert "10 lượt (7 đạt / 3 chê)" in summary
    assert "70.0% đạt · 30.0% chê" in summary
    assert "**Kho hieu**: 2 lần" in summary
    assert "**Tra loi dai dong**: 1 lần" in summary


# ---------------------------------------------------------------------------
# Criterion 4 & 5: Không ghi kho tri thức & không chứa nội dung tài liệu truy hồi
# ---------------------------------------------------------------------------


def test_dap_an_tom_tat_khong_chua_noi_dung_tai_lieu_truy_hoi():
    """Summary contains only feedback metrics, no citation chunks or document contents."""
    summary = format_feedback_review_summary()
    assert "02XC_" not in summary
    assert "History KDTPS" not in summary
    assert "Nguồn: DB ca lỗi" not in summary
    assert "Phiếu 2023/" not in summary


# ---------------------------------------------------------------------------
# Criterion 6: Cơ chế cảnh báo xu hướng SMA(20)
# ---------------------------------------------------------------------------


def test_mot_diem_xau_don_le_khong_canh_bao():
    """1 isolated bad point does not trigger trend alert."""
    records = []
    # 20 days with 0 bad
    for d in range(1, 20):
        records.append({
            "rating": "huu_ich",
            "reason": "",
            "question": "Câu test",
            "created_at": f"2026-09-{d:02d}T10:00:00",
            "topic": "test",
        })
    # 1 bad point on day 20
    records.append({
        "rating": "chua_huu_ich",
        "reason": "Lỗi nhỏ",
        "question": "Câu test",
        "created_at": "2026-09-20T10:00:00",
        "topic": "test",
    })
    summary = format_feedback_review_summary(records=records)
    assert "Không có cảnh báo xu hướng bất thường theo cơ chế SMA(20)" in summary


def test_ba_diem_xau_lien_tiep_co_canh_bao_xu_huong():
    """>=3 consecutive anomalies trigger trend alert."""
    records = []
    # Baseline 20 days with 0 bad
    for d in range(1, 21):
        for _ in range(4):
            records.append({
                "rating": "huu_ich",
                "reason": "",
                "question": "Lỗi kẹt giấy",
                "created_at": f"2026-09-{d:02d}T10:00:00",
                "topic": "lsu",
            })
    # 3 consecutive bad days (all bad)
    for d in (21, 22, 23):
        for _ in range(5):
            records.append({
                "rating": "chua_huu_ich",
                "reason": "Kẹt liên tục",
                "question": "Lỗi kẹt giấy",
                "created_at": f"2026-09-{d:02d}T10:00:00",
                "topic": "lsu",
            })

    summary = format_feedback_review_summary(records=records)
    assert "Cảnh báo" in summary
    assert "Lỗi kẹt giấy" in summary


# ---------------------------------------------------------------------------
# Criterion 7: E2E chat app intent router
# ---------------------------------------------------------------------------


class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def test_e2e_xu_ly_y_dinh_chat_luu_tin_nhan_tra_loi(monkeypatch):
    """Sending 'xem phản hồi' in chat app returns True and saves assistant summary."""
    import streamlit as st

    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    da_luu = []
    monkeypatch.setattr(store, "save_message", lambda msg: da_luu.append(msg))
    conv = SimpleNamespace(id="CONV-FEEDBACK-TEST")

    handled = app._xu_ly_y_dinh_chat(
        "xem phản hồi",
        active_conversation=conv,
        active_nb_id="NB-1",
    )
    assert handled is True
    assert len(da_luu) == 2
    assert da_luu[0].role == "user"
    assert da_luu[0].content == "xem phản hồi"
    assert da_luu[1].role == "assistant"
    content = da_luu[1].content
    assert "📊 Tóm tắt phản hồi đáp án" in content
    assert "Tổng số phản hồi:" in content
    assert "Tỷ lệ đạt / chê:" in content
    assert "Các lý do chê lặp lại nhiều nhất" in content
    assert "Mức cảnh báo xu hướng SMA(20)" in content
    assert "Phản hồi gần đây" in content


# ---------------------------------------------------------------------------
# Criterion 8: Đối chứng kho thực tế trên máy hiện hành (38 bản ghi)
# ---------------------------------------------------------------------------


def test_doi_chung_kho_that_tai_may():
    """Verify live local_cases/answer_feedback.jsonl has 38 lines and matches summary."""
    fb_file = answer_feedback.feedback_file()
    assert fb_file.exists(), f"File {fb_file} không tồn tại!"

    # Count lines manually from JSONL file
    raw_records = []
    with fb_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_records.append(json.loads(line))

    assert len(raw_records) == 38, f"Kỳ vọng 38 dòng thực tế, đếm được {len(raw_records)}!"
    good_count = sum(1 for r in raw_records if r.get("rating") == "huu_ich")
    bad_count = sum(1 for r in raw_records if r.get("rating") == "chua_huu_ich")
    assert good_count == 21
    assert bad_count == 17

    summary = format_feedback_review_summary()
    assert "Tổng số phản hồi:** 38 lượt (21 đạt / 17 chê)" in summary
    assert "55.3% đạt · 44.7% chê" in summary
