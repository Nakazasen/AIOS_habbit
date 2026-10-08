from __future__ import annotations

import pytest

from aios_habit.answer_sanitizer import (
    clean_assistant_answer,
    inspect_truncation,
    is_system_prompt_leak,
)


def test_clean_assistant_answer_removes_think_blocks():
    raw = "<think>I should check the sources and verify C7620</think>Mã lỗi C7620 là lỗi lệch trục quay."
    assert clean_assistant_answer(raw) == "Mã lỗi C7620 là lỗi lệch trục quay."

    thought_raw = "<thought>Thinking...</thought>Câu trả lời chính xác."
    assert clean_assistant_answer(thought_raw) == "Câu trả lời chính xác."

    bracket_raw = "[THINK]Internal CoT[/THINK]Dữ liệu từ bảng Skew."
    assert clean_assistant_answer(bracket_raw) == "Dữ liệu từ bảng Skew."


def test_clean_assistant_answer_handles_unclosed_think():
    raw = "<think>Model got cut off while thinking and never closed tag"
    assert clean_assistant_answer(raw) == ""


def test_clean_assistant_answer_removes_safety_classification_artifacts():
    raw = (
        "User Safety: safe\n"
        "Response Safety: safe\n\n"
        "Tài liệu đã xác nhận thông số Skew của Black là 0 µm / 0 dot."
    )
    cleaned = clean_assistant_answer(raw)
    assert "User Safety" not in cleaned
    assert "Response Safety" not in cleaned
    assert "Tài liệu đã xác nhận thông số Skew" in cleaned


def test_detect_system_prompt_leak_on_q0709_leakage():
    leak_q0709 = (
        "We need to determine safety of user input and assistant response. "
        "The conversation shows user: 'Câu hỏi người dùng: CÂU HỎI: Trong bảng quy đổi Skew... "
        "NGUỒN 1 Tiêu đề: Báo_cáo_lỗi_xuất_kho_AMS.xlsx... "
        "Bạn là trợ lý AI trong Workspace Chat. Chỉ dùng câu hỏi và nội dung nguồn... "
        "Bản nháp deterministic của AIOS: Yêu cầu trả lời: - Trả lời hoàn toàn bằng Tiếng Việt...'\n\n"
        "User Safety: safe\n"
        "Response Safety: (omit if no assistant response present)"
    )
    assert is_system_prompt_leak(leak_q0709) is True
    # When text is purely leaked prompt and safety evaluation, clean returns empty
    assert clean_assistant_answer(leak_q0709) == ""


def test_inspect_truncation_detects_cut_sentences():
    # Câu Q0718 bị cụt
    q0718_text = "Dựa trên các nguồn được cung cấp, file có xác nhận chênh lệch DMT–PMT không phải là nguyên nhân duy nhất gây"
    is_trunc, reason = inspect_truncation(q0718_text, finish_reason="stop")
    assert is_trunc is True
    assert reason == "dangling_conjunction"


    # finish_reason="length"
    complete_sentence = "File xác nhận chênh lệch DMT–PMT không phải nguyên nhân duy nhất."
    is_trunc_len, reason_len = inspect_truncation(complete_sentence, finish_reason="length")
    assert is_trunc_len is True
    assert reason_len == "finish_reason_length"

    # Câu trọn vẹn bình thường
    is_trunc_ok, reason_ok = inspect_truncation(complete_sentence, finish_reason="stop")
    assert is_trunc_ok is False
    assert reason_ok == "complete"
