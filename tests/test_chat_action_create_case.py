"""Unit tests for chat_action_create_case: two-phase case creation flow (DESKTOP-CASE-CREATE-FLOW)."""

import json
from pathlib import Path
from aios_habit.chat_action_create_case import (
    render_preview_card_text,
    extract_case_preview_marker,
    strip_case_preview_marker,
    execute_confirm_case,
)
from aios_habit.chat_intent_router import extract_case_entities


def test_preview_card_generation():
    text = "Tạo vụ điều tra lỗi mới: máy in báo lỗi kẹt giấy ở line 3"
    entities = extract_case_entities(text)
    preview = render_preview_card_text(text, entities, conversation_id="CONV-TEST-01")

    assert "Thẻ Xem Trước Vụ Điều Tra" in preview
    assert "máy in báo lỗi kẹt giấy" in preview
    assert "Line 3" in preview
    assert "máy in" in preview
    assert "Chờ xác nhận tạo vụ" in preview

    # Marker must be extractable
    marker = extract_case_preview_marker(preview)
    assert marker is not None
    assert marker["phenomenon"] == "máy in báo lỗi kẹt giấy"
    assert marker["line"] == "Line 3"
    assert marker["machine_type"] == "máy in"

    # Stripped text should not contain the raw HTML comment
    clean = strip_case_preview_marker(preview)
    assert "aios_case_preview" not in clean


def test_execute_confirm_case_persists_and_runs_step1(tmp_path, monkeypatch):
    # Direct case store to temporary local_cases for isolation
    test_cases_dir = tmp_path / "local_cases"
    test_cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", test_cases_dir)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", test_cases_dir / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", test_cases_dir / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", test_cases_dir / "assets")

    preview_data = {
        "preview_id": "PREV-TEST-001",
        "phenomenon": "máy in báo lỗi kẹt giấy",
        "line": "Line 3",
        "machine_type": "máy in",
        "error_code": "",
        "conversation_id": "CONV-TEST-01",
    }

    result = execute_confirm_case(preview_data, conversation_id="CONV-TEST-01")

    assert "Đã tạo thành công vụ điều tra" in result
    assert "CASE-" in result
    assert "Bước 1: Tra cứu ca lỗi tương tự" in result
    assert "Đánh giá gợi ý này:" in result

    # Verify cases.jsonl in tmp_path
    cases_file = test_cases_dir / "cases.jsonl"
    assert cases_file.exists()
    lines = [line.strip() for line in cases_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["case_id"].startswith("CASE-")
    assert "máy in" in record["title"] or "kẹt giấy" in record["title"]
