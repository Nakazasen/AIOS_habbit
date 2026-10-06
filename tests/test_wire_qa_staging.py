"""Tests cho kho tham khảo Q&A staging của lane C-Agent (WIRE-QA-CAGENT).

Bao gồm: khớp 3 câu demo trên dữ liệu staging thật (file được commit trong
repo), ngưỡng/ỉ nhiễu của bộ chấm điểm, cổng feature flag, định dạng nhãn bản
thảo và khóa encoding UTF-8 (tiếng Nhật + backtick).
"""
from __future__ import annotations

import json
from pathlib import Path

from aios_habit.feature_flags import override_feature_flags
from aios_habit.wire_qa_staging import (
    DRAFT_LABEL_HEADER,
    WireQaPair,
    build_wire_qa_reference,
    load_staging_pairs,
    select_relevant_pairs,
    strip_echoed_draft_label,
)

DEMO_ERROR_CODE_QUESTION = (
    "Mã lỗi C0980 trên máy in/photocopy báo hiệu lỗi gì và các bước kiểm tra "
    "linh kiện thực tế theo tài liệu gồm những gì?"
)
DEMO_CTRLMODE_QUESTION = (
    "Trong file cấu hình Matecon điều khiển AGV/ACR trên dây chuyền, hai chế độ "
    "ctrlMode = 0 và ctrlMode = 1 khác nhau như thế nào?"
)
DEMO_JIG_QUESTION = (
    "Trong dữ liệu UnitTest của Jig 2ND-1004 tháng 8/2026, mẫu đo Serial "
    "61C999999902 xuất hiện bao nhiêu lần và kết quả đánh giá OK/NG của từng màu như thế nào?"
)


def _synthetic_pair(pair_id: str, question: str, answer: str) -> WireQaPair:
    return WireQaPair(id=pair_id, question=question, answer=answer, source="test/batch.md", category="MOM")


def test_demo_error_code_question_selects_definition_and_component_facts() -> None:
    pairs = select_relevant_pairs(DEMO_ERROR_CODE_QUESTION, load_staging_pairs())
    assert pairs, "câu C0980 phải khớp được cặp staging"
    answer_blob = "\n".join(p.answer for p in pairs)
    # Kỳ vọng tối thiểu của vé: định nghĩa + linh kiện F401/Q402/Q403.
    assert "24V電源断検知" in answer_blob
    assert "F401" in answer_blob
    assert "Q402" in answer_blob and "Q403" in answer_blob


def test_demo_ctrlmode_question_selects_q0001() -> None:
    ids = {p.id for p in select_relevant_pairs(DEMO_CTRLMODE_QUESTION, load_staging_pairs())}
    assert "Q0001" in ids


def test_demo_jig_question_selects_q0825() -> None:
    ids = {p.id for p in select_relevant_pairs(DEMO_JIG_QUESTION, load_staging_pairs())}
    assert "Q0825" in ids


def test_generic_smalltalk_question_selects_nothing() -> None:
    assert select_relevant_pairs("Hôm nay ăn gì ngon nhỉ?", load_staging_pairs()) == ()


def test_reference_is_none_when_flag_off() -> None:
    with override_feature_flags(wire_qa_cagent=False):
        assert build_wire_qa_reference(DEMO_CTRLMODE_QUESTION) is None


def test_reference_contains_draft_label_and_per_source_citation() -> None:
    with override_feature_flags(wire_qa_cagent=True):
        reference = build_wire_qa_reference(DEMO_CTRLMODE_QUESTION)
    assert reference is not None
    assert reference.label_block.startswith("> " + DRAFT_LABEL_HEADER)
    assert "Cặp Q&A #Q0001" in reference.label_block
    # Trích nguồn theo trường `source` của JSONL, không dẫn đường dẫn raw.
    assert "mom/batch-01.md" in reference.prompt_block
    assert "chatgpt-enrichment-raw" not in reference.prompt_block
    # Template 2 mảnh đã chốt: câu hỏi gốc + trả lời gốc, không có trường "Bối cảnh".
    assert "Câu hỏi gốc:" in reference.prompt_block
    assert "Trả lời gốc:" in reference.prompt_block
    assert "Bối cảnh:" not in reference.prompt_block


def test_prompt_block_keeps_japanese_and_backticks_through_utf8_json() -> None:
    """Khóa encoding UTF-8/JSON ngay từ đầu (Q3401 tiếng Nhật + backtick Q3317)."""
    with override_feature_flags(wire_qa_cagent=True):
        reference = build_wire_qa_reference(DEMO_ERROR_CODE_QUESTION)
    assert reference is not None
    payload = json.dumps({"question": reference.prompt_block}, ensure_ascii=False).encode("utf-8")
    decoded = json.loads(payload.decode("utf-8"))["question"]
    assert "24V電源断検知" in decoded
    assert "`" in decoded  # backtick từ các cặp điều-tra-lỗi


def test_code_term_alone_reaches_threshold() -> None:
    pair = _synthetic_pair("Q0001", "C0980 là lỗi gì?", "C0980 là 24V電源断検知.")
    assert [p.id for p in select_relevant_pairs("Cho tôi hỏi về C0980", [pair])] == ["Q0001"]


def test_two_shared_words_stay_below_threshold() -> None:
    pair = _synthetic_pair("Q0001", "kiểm tra linh kiện thực tế", "Không ghi gì thêm.")
    assert select_relevant_pairs("kiểm tra bước nào", [pair]) == ()


def test_limit_caps_selected_pairs() -> None:
    pairs = tuple(
        _synthetic_pair(f"Q{i:04d}", "mã lỗi C0980", "F401 đứt, Q402 short") for i in range(1, 6)
    )
    assert len(select_relevant_pairs("C0980 là gì", pairs, limit=2)) == 2


def test_missing_mapping_file_loads_empty(tmp_path: Path) -> None:
    assert load_staging_pairs(tmp_path / "khong-ton-tai.jsonl") == ()


def test_strip_echoed_draft_label_removes_model_echo() -> None:
    echoed = (
        "> ⚠️ **Bản thảo — chưa qua chuyên gia duyệt**\n"
        "> *Nguồn dữ liệu tham khảo: Khối MOM — Cặp Q&A #Q0001*\n\n"
        "Nội dung trả lời thật."
    )
    assert strip_echoed_draft_label(echoed) == "Nội dung trả lời thật."


def test_strip_echoed_draft_label_keeps_normal_answer() -> None:
    body = "Kết quả: F401 đứt.\n\n> ghi chú nhỏ trong câu trả lời"
    assert strip_echoed_draft_label(body) == body


def test_strip_echoed_draft_label_plain_text_untouched() -> None:
    assert strip_echoed_draft_label("  Đáp án bình thường.  ") == "Đáp án bình thường."
