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
    # Check context mention and corrected exact status
    assert "Ngữ cảnh phiên:" in result
    assert "Mở (`open`)" in result

    # Verify cases.jsonl in tmp_path
    cases_file = test_cases_dir / "cases.jsonl"
    assert cases_file.exists()
    lines = [line.strip() for line in cases_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["case_id"].startswith("CASE-")
    assert "máy in" in record["title"] or "kẹt giấy" in record["title"]
    assert record["status"] == "open"


def test_format_case_status():
    from aios_habit.chat_action_create_case import format_case_status

    assert format_case_status("open") == "Mở (`open`)"
    assert format_case_status("investigating") == "Đang điều tra (`investigating`)"
    assert format_case_status("waiting") == "Chờ xử lý (`waiting`)"
    assert format_case_status("resolved") == "Đã giải quyết (`resolved`)"
    assert format_case_status("archived") == "Đã lưu trữ (`archived`)"


def test_view_case_progress_and_build_tree(tmp_path, monkeypatch):
    from aios_habit.case_models import Case
    from aios_habit.case_store import save_case
    from aios_habit.chat_action_create_case import (
        execute_view_case_progress,
        execute_build_case_tree,
        set_active_case_id,
    )

    test_cases_dir = tmp_path / "local_cases"
    test_cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", test_cases_dir)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", test_cases_dir / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", test_cases_dir / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", test_cases_dir / "assets")

    c = Case(
        case_id="CASE-TEST9999",
        title="Sự cố máy in - máy in báo lỗi kẹt giấy - (Line 3)",
        current_situation="Hiện tượng: máy in báo lỗi kẹt giấy ở line 3. Dây chuyền: Line 3. Model: máy in.",
        status="open",
        priority="normal",
    )
    save_case(c)
    set_active_case_id(c.case_id)

    # 1. Test execute_view_case_progress
    progress_res = execute_view_case_progress(case_id=c.case_id)
    assert "Tiến độ vụ điều tra `CASE-TEST9999`" in progress_res
    assert "Mở (`open`)" in progress_res
    assert "máy in báo lỗi kẹt giấy" in progress_res
    assert "Các trường còn trống cho các bước tiếp theo" in progress_res
    assert "Bước 2 (Giả thuyết nguyên nhân)" in progress_res
    assert "Bước 3 (Cây điều tra 4M & Why-Why)" in progress_res

    # 2. Test execute_build_case_tree
    tree_res = execute_build_case_tree(case_id=c.case_id)
    assert "Cây điều tra 4M & Chuỗi Why-Why (Bước 3) — Vụ `CASE-TEST9999`" in tree_res
    assert "CASE-TEST9999" in tree_res
    assert "Con người (Man)" in tree_res
    assert "Máy móc (Machine)" in tree_res
    assert "Vật liệu (Material)" in tree_res
    assert "Phương pháp (Method)" in tree_res
    assert "Chuỗi Why-Why" in tree_res


def test_missing_case_context():
    from aios_habit.chat_action_create_case import (
        execute_view_case_progress,
        execute_build_case_tree,
    )

    prog = execute_view_case_progress(case_id="CASE-NONEXISTENT")
    assert "Không tìm thấy vụ `CASE-NONEXISTENT`" in prog

    tree = execute_build_case_tree(case_id="CASE-NONEXISTENT")
    assert "Không tìm thấy vụ `CASE-NONEXISTENT`" in tree
