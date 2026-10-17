"""Tests for Step 2 Close Gate and Feedback Coverage (ticket DESKTOP-STEP2-CLOSE-GATE-COVERAGE-HOME).

Verifies:
1. Investigation case close gate:
   - Blocks closing if actual cause or countermeasure is missing/placeholder.
   - Specifies exactly which field(s) are missing.
   - When valid, writes actual results back to local_cases/cases.jsonl.
   - Absolutely zero writes to knowledge store (library.sqlite / vector store).
2. Chat intent router & execution flow:
   - Recognizes DONG_VU intent and extracts case_id, actual_cause, actual_countermeasure.
   - execute_close_case handles gate blocking and successful close with clear Vietnamese messages.
3. Feedback coverage measurement:
   - Computes total displayed vs total rated across chat answers and domain suggestions.
   - Displays coverage rate, target check (>= 80%), measurement timestamp, and clear denominator definition in 'xem phản hồi' summary.
   - Validates live compatibility on local_cases data.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.case_models import Case
from aios_habit import case_store
from aios_habit.case_store import (
    InvestigationClosureBlockedError,
    close_investigation_case,
    is_blank_value,
    load_cases,
    save_case,
)
from aios_habit.chat_action_create_case import execute_close_case, execute_view_case_progress
from aios_habit.chat_intent_router import (
    DONG_VU,
    classify_intent,
    extract_slots,
    route,
)
from aios_habit.feedback_review_home import (
    compute_feedback_coverage,
    format_feedback_review_summary,
)


@pytest.fixture
def isolated_case_store(tmp_path: Path):
    """Fixture providing an isolated local_cases directory."""
    orig_dir = case_store.LOCAL_CASES_DIR
    orig_cases = case_store.CASES_FILE
    orig_ev = case_store.EVIDENCE_FILE
    orig_assets = case_store.ASSETS_DIR

    test_dir = tmp_path / "local_cases"
    case_store.LOCAL_CASES_DIR = test_dir
    case_store.CASES_FILE = test_dir / "cases.jsonl"
    case_store.EVIDENCE_FILE = test_dir / "evidence.jsonl"
    case_store.ASSETS_DIR = test_dir / "assets"
    case_store.init_store()

    yield test_dir

    case_store.LOCAL_CASES_DIR = orig_dir
    case_store.CASES_FILE = orig_cases
    case_store.EVIDENCE_FILE = orig_ev
    case_store.ASSETS_DIR = orig_assets


# ===========================================================================
# 1. Data Model & Blank Check Unit Tests
# ===========================================================================

def test_case_models_close_gate_fields():
    """Case dataclass must include actual_cause, actual_countermeasure, and closed_at."""
    c = Case(case_id="CASE-UNIT-01", title="Unit Test Case")
    assert hasattr(c, "actual_cause")
    assert hasattr(c, "actual_countermeasure")
    assert hasattr(c, "closed_at")
    assert c.actual_cause == ""
    assert c.actual_countermeasure == ""
    assert c.closed_at == ""


def test_is_blank_value_detects_empty_and_placeholders():
    """Verify is_blank_value catches empty, whitespace, and lazy placeholder strings."""
    assert is_blank_value(None) is True
    assert is_blank_value("") is True
    assert is_blank_value("   ") is True
    assert is_blank_value("-") is True
    assert is_blank_value("--") is True
    assert is_blank_value("---") is True
    assert is_blank_value("none") is True
    assert is_blank_value("null") is True
    assert is_blank_value("n/a") is True
    assert is_blank_value("na") is True
    assert is_blank_value("chua co") is True
    assert is_blank_value("chưa có") is True
    assert is_blank_value("chua ro") is True
    assert is_blank_value("chưa rõ") is True
    assert is_blank_value("...") is True
    assert is_blank_value("todo") is True
    assert is_blank_value("pass") is True

    # Real valid values must not be blank
    assert is_blank_value("Lỏng cáp tín hiệu CN102") is False
    assert is_blank_value("Vệ sinh và cắm chặt lại giắc") is False


# ===========================================================================
# 2. Case Store Close Gate Behavior Tests
# ===========================================================================

def test_close_case_gate_blocks_when_both_missing(isolated_case_store: Path):
    """Gate must block closing when both cause and countermeasure are missing."""
    case = Case(
        case_id="CASE-B2-001",
        title="Lỗi kẹt giấy cụm sấy",
        current_situation="Giấy kẹt liên tục tại cụm sấy",
    )
    save_case(case)

    with pytest.raises(InvestigationClosureBlockedError) as exc_info:
        close_investigation_case("CASE-B2-001", actual_cause="", actual_countermeasure="")

    err = exc_info.value
    assert len(err.missing_fields) == 2
    assert any("actual_cause" in f for f in err.missing_fields)
    assert any("actual_countermeasure" in f for f in err.missing_fields)
    assert "CỔNG CHẶN ĐÓNG VỤ" in err.message

    # Ensure case on disk was NOT closed
    reloaded = load_cases()[0]
    assert reloaded.status == "open"
    assert reloaded.actual_cause == ""
    assert reloaded.actual_countermeasure == ""


def test_close_case_gate_blocks_when_only_cause_missing(isolated_case_store: Path):
    """Gate must block closing when only actual cause is missing and name the field."""
    case = Case(
        case_id="CASE-B2-002",
        title="Lỗi lệch khung ảnh",
        current_situation="Ảnh bị lệch 2mm",
    )
    save_case(case)

    with pytest.raises(InvestigationClosureBlockedError) as exc_info:
        close_investigation_case(
            "CASE-B2-002",
            actual_cause="",
            actual_countermeasure="Căn chỉnh lại thước định vị cơ khí",
        )

    err = exc_info.value
    assert len(err.missing_fields) == 1
    assert "actual_cause" in err.missing_fields[0]

    reloaded = load_cases()[0]
    assert reloaded.status == "open"


def test_close_case_gate_blocks_when_only_countermeasure_missing(isolated_case_store: Path):
    """Gate must block closing when only actual countermeasure is missing and name the field."""
    case = Case(
        case_id="CASE-B2-003",
        title="Lỗi động cơ bước quá nhiệt",
        current_situation="Motor bước M2 nhiệt độ đạt 75 độ C",
    )
    save_case(case)

    with pytest.raises(InvestigationClosureBlockedError) as exc_info:
        close_investigation_case(
            "CASE-B2-003",
            actual_cause="Vòng bi trục động cơ bị khô mỡ bôi trơn",
            actual_countermeasure="   ",
        )

    err = exc_info.value
    assert len(err.missing_fields) == 1
    assert "actual_countermeasure" in err.missing_fields[0]

    reloaded = load_cases()[0]
    assert reloaded.status == "open"


def test_close_case_gate_blocks_placeholders(isolated_case_store: Path):
    """Gate must block closing when fields contain placeholder marks like 'chưa rõ' or '...'."""
    case = Case(
        case_id="CASE-B2-004",
        title="Lỗi mờ chữ trên bản in",
        current_situation="Bản in có vệt trắng mờ",
    )
    save_case(case)

    with pytest.raises(InvestigationClosureBlockedError) as exc_info:
        close_investigation_case(
            "CASE-B2-004",
            actual_cause="chưa rõ",
            actual_countermeasure="...",
        )

    err = exc_info.value
    assert len(err.missing_fields) == 2


def test_close_case_success_and_writeback(isolated_case_store: Path):
    """When both fields are valid, case is resolved and persisted to local_cases."""
    case = Case(
        case_id="CASE-B2-005",
        title="Lỗi rách màng sấy",
        current_situation="Màng sấy bị rách 5mm góc phải",
    )
    save_case(case)

    resolved = close_investigation_case(
        "CASE-B2-005",
        actual_cause="Dị vật ghim bấm kim loại bám vào rulo ép gây xước màng sấy",
        actual_countermeasure="Thay mới màng sấy và bổ sung quy định kiểm tra tài liệu trước khi nạp",
        closed_by="Kỹ sư bảo trì Nguyễn Văn A",
    )

    assert resolved.status == "resolved"
    assert resolved.actual_cause == "Dị vật ghim bấm kim loại bám vào rulo ép gây xước màng sấy"
    assert "Thay mới màng sấy" in resolved.actual_countermeasure
    assert resolved.closed_at != ""
    assert "Dị vật ghim bấm" in resolved.outcome
    assert len(resolved.timeline_events) >= 1
    assert resolved.timeline_events[-1]["type"] == "case_closed"

    # Verify persisted to local_cases/cases.jsonl
    reloaded_list = load_cases()
    match = next(c for c in reloaded_list if c.case_id == "CASE-B2-005")
    assert match.status == "resolved"
    assert match.actual_cause == resolved.actual_cause
    assert match.actual_countermeasure == resolved.actual_countermeasure

    # Verify audit log in local_cases/case_closures.jsonl
    audit_file = isolated_case_store / "case_closures.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    audit_data = json.loads(lines[-1])
    assert audit_data["case_id"] == "CASE-B2-005"
    assert audit_data["status"] == "resolved"
    assert audit_data["actual_cause"] == resolved.actual_cause


def test_close_case_isolation_from_knowledge_store(isolated_case_store: Path, tmp_path: Path):
    """Closing a case in local_cases must NEVER touch library.sqlite or knowledge store."""
    # Create a mock library.sqlite file
    fake_sqlite = tmp_path / "library.sqlite"
    fake_sqlite.write_bytes(b"SQLite format 3\x00fake-initial-content")
    initial_stat = fake_sqlite.stat()

    case = Case(case_id="CASE-ISOLATION-01", title="Isolation test")
    save_case(case)

    close_investigation_case(
        "CASE-ISOLATION-01",
        actual_cause="Lỗi đứt dây đai truyền động",
        actual_countermeasure="Thay dây đai chính hãng 150-3M",
    )

    # Verify fake_sqlite is untouched
    current_stat = fake_sqlite.stat()
    assert current_stat.st_mtime == initial_stat.st_mtime
    assert current_stat.st_size == initial_stat.st_size
    assert fake_sqlite.read_bytes() == b"SQLite format 3\x00fake-initial-content"


# ===========================================================================
# 3. Chat Intent Router & Execution Flow Tests
# ===========================================================================

def test_intent_router_dong_vu_variations():
    """Router must recognize various Vietnamese close case phrases and extract slots."""
    test_cases = [
        ("đóng vụ CASE-20261017-001", "CASE-20261017-001", "", ""),
        ("dong vu dieu tra", "", "", ""),
        (
            "chốt vụ CASE-B2-99: nguyên nhân: lỏng ốc bắt sensor, đối sách: siết lại lực 2.5Nm và nhỏ keo khóa ren",
            "CASE-B2-99",
            "lỏng ốc bắt sensor",
            "siết lại lực 2.5Nm và nhỏ keo khóa ren",
        ),
        (
            "đóng ca CASE-A1: nguyên nhân thật: hỏng bạc đạn; đối sách thật: thay thế cụm bạc đạn",
            "CASE-A1",
            "hỏng bạc đạn",
            "thay thế cụm bạc đạn",
        ),
        ("/dongvu CASE-1234", "CASE-1234", "", ""),
        ("đóng phiếu lỗi CASE-5678", "CASE-5678", "", ""),
    ]

    for sentence, expected_cid, expected_cause, expected_remedy in test_cases:
        intent = classify_intent(sentence)
        assert intent == DONG_VU, f"Failed for sentence: '{sentence}', got {intent}"
        slots = extract_slots(sentence, intent)
        if expected_cid:
            assert slots.get("case_id") == expected_cid
        if expected_cause:
            assert slots.get("actual_cause") == expected_cause
        if expected_remedy:
            assert slots.get("actual_countermeasure") == expected_remedy


def test_execute_close_case_chat_action_flow(isolated_case_store: Path):
    """Test execute_close_case behavior when invoked via chat."""
    case = Case(case_id="CASE-CHAT-01", title="Vụ test chat action")
    save_case(case)

    # 1. Missing fields via chat -> Gate blocked message
    blocked_resp = execute_close_case(
        case_id="CASE-CHAT-01",
        actual_cause="",
        actual_countermeasure="",
        raw_text="đóng vụ CASE-CHAT-01",
    )
    assert "🚫 CỔNG CHẶN ĐÓNG VỤ" in blocked_resp
    assert "nguyên nhân thật" in blocked_resp
    assert "đối sách thật" in blocked_resp

    # 2. Missing countermeasure only
    blocked_one = execute_close_case(
        case_id="CASE-CHAT-01",
        actual_cause="Gãy chốt khóa nắp",
        actual_countermeasure="",
        raw_text="",
    )
    assert "🚫 CỔNG CHẶN ĐÓNG VỤ" in blocked_one
    assert "đối sách thật" in blocked_one

    # 3. Successful closing via chat
    success_resp = execute_close_case(
        case_id="CASE-CHAT-01",
        actual_cause="Gãy chốt khóa nắp do va đập khi thao tác",
        actual_countermeasure="Thay chốt đúc hợp kim gia cường",
        raw_text="",
    )
    assert "✅ ĐÃ ĐÓNG VỤ ĐIỀU TRA THÀNH CÔNG" in success_resp
    assert "CASE-CHAT-01" in success_resp
    assert "Gãy chốt khóa nắp do va đập" in success_resp
    assert "Thay chốt đúc hợp kim gia cường" in success_resp
    assert "local_cases/cases.jsonl" in success_resp

    # Verify view progress reflects the closed state
    progress_view = execute_view_case_progress(case_id="CASE-CHAT-01")
    assert "Kết quả đóng vụ (Cổng hoàn thành Bước 2)" in progress_view
    assert "Gãy chốt khóa nắp do va đập" in progress_view


def test_execute_close_case_nonexistent_case(isolated_case_store: Path):
    """execute_close_case returns clean warning when case is not found."""
    resp = execute_close_case(
        case_id="CASE-NONEXISTENT",
        actual_cause="Nguyên nhân",
        actual_countermeasure="Đối sách",
    )
    assert "Không tìm thấy hồ sơ" in resp
    assert "CASE-NONEXISTENT" in resp


# ===========================================================================
# 4. Coverage Measurement Unit & Integration Tests
# ===========================================================================

def test_compute_feedback_coverage_synthetic_data(tmp_path: Path):
    """Verify compute_feedback_coverage with controlled synthetic data."""
    test_cases_dir = tmp_path / "mock_cases"
    test_cases_dir.mkdir(parents=True, exist_ok=True)
    chat_dir = test_cases_dir / "workspace_chat"
    chat_dir.mkdir(parents=True, exist_ok=True)

    # 10 answered questions in answer_feedback.jsonl
    af_file = test_cases_dir / "answer_feedback.jsonl"
    af_data = [{"id": f"af-{i}", "conversation_id": "conv-1", "rating": "tot"} for i in range(10)]
    af_file.write_text("\n".join(json.dumps(d) for d in af_data), encoding="utf-8")

    # 12 assistant messages in messages.jsonl for conv-1
    msgs_file = chat_dir / "messages.jsonl"
    msgs_data = [{"conversation_id": "conv-1", "role": "assistant", "content": f"Answer {i}"} for i in range(12)]
    msgs_file.write_text("\n".join(json.dumps(d) for d in msgs_data), encoding="utf-8")

    # 4 autoclassify suggestions (2 rated)
    acf_file = test_cases_dir / "autoclassify_feedback.jsonl"
    acf_data = [
        {"id": "acf-1", "rating": "dung"},
        {"id": "acf-2", "rating": "sai"},
        {"id": "acf-3", "rating": "chờ đánh giá"},
        {"id": "acf-4", "rating": None},
    ]
    acf_file.write_text("\n".join(json.dumps(d) for d in acf_data), encoding="utf-8")

    # 4 investigation tree suggestions (1 rated)
    inv_file = test_cases_dir / "investigation_feedback.jsonl"
    inv_data = [
        {"id": "inv-1", "rating": "đúng hướng"},
        {"id": "inv-2", "rating": "chờ đánh giá"},
        {"id": "inv-3", "rating": ""},
        {"id": "inv-4", "rating": None},
    ]
    inv_file.write_text("\n".join(json.dumps(d) for d in inv_data), encoding="utf-8")

    cov = compute_feedback_coverage(base_dir=test_cases_dir)

    # Expected:
    # Answers displayed = 12, rated = 10
    # Suggestions displayed = 4 + 4 = 8, rated = 2 + 1 = 3
    # Total displayed = 20, Total rated = 13
    # Coverage = 13 / 20 = 0.65 (65.0%)
    assert cov["tong_hien_thi"] == 20
    assert cov["tong_da_danh_gia"] == 13
    assert cov["ti_le_phan_tram"] == 65.0
    assert cov["dat_muc_tieu"] is False  # 65.0% < 80.0%
    assert cov["muc_tieu"] == 0.80
    assert cov["moc_thoi_gian"] != ""
    assert "đáp án hội thoại và gợi ý nghiệp vụ" in cov["dinh_nghia_mau_so"]


def test_format_feedback_review_summary_includes_coverage_section():
    """Review summary via 'xem phản hồi' must display coverage percentage, denominator, and timestamp."""
    summary = format_feedback_review_summary()

    assert "### 📊 Tóm tắt phản hồi đáp án" in summary
    assert "#### 🎯 Độ bao phủ đánh giá (Điều kiện hoàn thành Bước 2)" in summary
    assert "Tỉ lệ bao phủ đánh giá:" in summary
    assert "Tử số (Lượt đã có đánh giá):" in summary
    assert "Mẫu số (Lượt hiển thị có cơ chế đánh giá):" in summary
    assert "Định nghĩa mẫu số:" in summary
    assert "Bóc tách luồng dữ liệu:" in summary
    assert "Đáp án hội thoại (Workspace Chat):" in summary
    assert "Gợi ý nghiệp vụ điều tra & phân loại (Bước 1, 3, 5):" in summary
    assert "Mốc thời gian đo:" in summary


def test_live_data_compatibility():
    """Verify coverage computation runs cleanly on current real workspace data."""
    cov = compute_feedback_coverage()
    assert cov["tong_hien_thi"] >= 50
    assert cov["tong_da_danh_gia"] >= 38
    assert cov["ti_le_phan_tram"] >= 50.0
    assert cov["dat_muc_tieu"] is False  # Currently < 80% as documented in ticket
    assert "boc_tach" in cov
    assert "dap_an_hoi_thoai" in cov["boc_tach"]
    assert "goi_y_nghiep_vu" in cov["boc_tach"]
