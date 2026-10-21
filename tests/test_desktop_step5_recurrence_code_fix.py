"""Automated test suite for ticket DESKTOP-HOME-STEP5-RECURRENCE-CODE-FIX.

Tests:
1. Recurrence detection against historical database (reconciled DB with 30,075 cases or sample DB):
   - Error code present in DB (e.g. C7620) -> is_recurrence=True, count >= 1 matches DB direct count,
     most recent case (ticket/date/model) and its countermeasure surfaced.
   - Error code not present in DB (e.g. X9999) -> is_recurrence=False, count=0, no false recurrence alert.
2. Conflict resolution: Error code glossary (C_CALL) priority over contradictory symptom keywords:
   - "kẹt giấy cụm sấy lỗi C7620" -> overrides 'In ấn' to 'Điều chỉnh' stage, declares provenance & conflict note.
3. Preview card rendering:
   - Renders recurrence warning banner and countermeasure.
   - Renders conflict note when symptom contradicts code definition.
   - Negative control renders cleanly without recurrence warning.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.chat_action_create_case import (
    extract_case_preview_marker,
    render_preview_card_text,
)
from aios_habit.error_cases import init_db, start_batch, upsert_case
from aios_habit.error_cases.auto_classifier import (
    classify_error,
    classify_new_error,
    detect_recurrence,
)


@pytest.fixture
def sample_db(tmp_path):
    """Create a sample error_cases DB with historical cases for positive & negative tests."""
    db_path = tmp_path / "sample_error_cases.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Add error_glossary table for glossary lookups
    conn.execute(
        """CREATE TABLE IF NOT EXISTS error_glossary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_family TEXT,
            code TEXT,
            code_sub TEXT,
            name_ja TEXT,
            name_vi TEXT,
            name_en TEXT,
            cause TEXT,
            remedy TEXT,
            rank TEXT,
            unit TEXT,
            models TEXT,
            source_file TEXT,
            imported_at TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO error_glossary (code_family, code, code_sub, name_ja, name_vi, cause, remedy)
           VALUES ('C_CALL', 'C7620', '', 'カラーレジストタイミング異常', 'Lỗi thời gian đăng ký màu',
                   'Khi tự động sửa màu đăng ký không thành công', 'VI 1. Reset nguồn điện chính')"""
    )

    batch_id = start_batch(
        conn,
        source_file="test_sample.xlsx",
        file_sha256="1" * 64,
        sheet_name="History",
        sheet_type="Máy in",
    )

    # 3 cases for C7620 with realistic metadata and countermeasures
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=10,
        fields={
            "no_dvd": "2025/1107",
            "sheet_type": "Máy in",
            "department": "Bảo trì",
            "machine_type": "Sirius2",
            "line": "C23",
            "error_code_c": "C7620",
            "process_stage": "調整A2.1",
            "countermeasure": "Phân chia lại thao tác dán Tape Lens A. Công đoạn K6 dán và lắp Mirror C luôn.",
            "investigation": "Lỗi lệch màu C7620",
            "occurred_at": "2025-06-30",
        },
    )
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=20,
        fields={
            "no_dvd": "2026/2836",
            "sheet_type": "Máy in",
            "department": "製造技術",
            "machine_type": "Virgo",
            "line": "C21",
            "error_code_c": "C7620",
            "process_stage": "調整A2.2",
            "countermeasure": "不要",
            "investigation": "要因不明(電気)",
            "occurred_at": "2026-09-23",
        },
    )
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=30,
        fields={
            "no_dvd": "FY27H2/263",
            "sheet_type": "Máy in",
            "department": "機器製造",
            "machine_type": "Virgo",
            "line": "C21",
            "error_code_c": "C7620",
            "process_stage": "調整A2.2",
            "countermeasure": "不要",
            "investigation": "Thay BLADE CLN mới + IMAGE UNIT cũ",
            "occurred_at": "2026-10-15",
        },
    )
    # Ensure countermeasure column is populated
    conn.execute("UPDATE error_cases SET countermeasure = '不要' WHERE no_dvd = 'FY27H2/263'")
    conn.execute("UPDATE error_cases SET countermeasure = '不要' WHERE no_dvd = '2026/2836'")
    conn.execute("UPDATE error_cases SET countermeasure = 'Phân chia lại thao tác dán Tape Lens A. Công đoạn K6 dán và lắp Mirror C luôn.' WHERE no_dvd = '2025/1107'")
    conn.commit()
    yield db_path
    conn.close()


def test_recurrence_detection_positive_case_code_c7620(sample_db):
    """Test positive recurrence: code C7620 exists in DB -> triggers recurrence with exact count, recent ticket & remedy."""
    conn = sqlite3.connect(sample_db)
    conn.row_factory = sqlite3.Row

    alert = detect_recurrence(conn, error_code="C7620")
    assert alert is not None
    assert alert.count == 3
    assert alert.code == "C7620"
    assert "FY27H2/263" in alert.message_vi
    assert "2026-10-15" in alert.message_vi
    assert "Virgo" in alert.message_vi
    assert alert.suggested_remedy == "不要"
    assert alert.suggested_from == "FY27H2/263"
    conn.close()


def test_recurrence_detection_negative_case_code_x9999(sample_db):
    """Test negative control: code X9999 does not exist in DB -> returns None (zero false recurrence alert)."""
    conn = sqlite3.connect(sample_db)
    conn.row_factory = sqlite3.Row

    alert = detect_recurrence(conn, error_code="X9999")
    assert alert is None
    conn.close()


def test_conflict_resolution_glossary_priority_over_symptom(sample_db):
    """Test conflict handling: symptom contains 'kẹt giấy' (paper jam) but code is C7620 (C_CALL color registration).

    The classifier must prioritize the code's inherent meaning ('Điều chỉnh') over the symptom keywords ('In ấn'),
    and record explicit provenance declaring the priority.
    """
    conn = sqlite3.connect(sample_db)
    conn.row_factory = sqlite3.Row

    out = classify_new_error(
        conn,
        error_code="C7620",
        phenomenon="kẹt giấy cụm sấy lỗi C7620",
        glossary_conn=conn,
    )
    cls_res = out["classification"]
    assert cls_res.cong_doan == "Điều chỉnh"
    assert "Ưu tiên mã C7620" in cls_res.can_cu.get("cong_doan", "")
    assert "kẹt giấy" in cls_res.can_cu.get("cong_doan", "")
    assert "mau_thuan_ma" in cls_res.can_cu

    # Recurrence alert must also be active
    rec_alert = out["recurrence_alert"]
    assert rec_alert is not None
    assert rec_alert.count == 3
    assert rec_alert.suggested_from == "FY27H2/263"
    conn.close()


def test_preview_card_full_rendering_positive_and_negative(sample_db, monkeypatch):
    """Test Phase 1 Preview Card rendering for both positive C7620 and negative X9999 cases."""
    monkeypatch.setattr("aios_habit.chat_action_error_lookup.resolve_db_path", lambda req: sample_db)

    # 1. Positive case: C7620
    text_pos = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    preview_pos = render_preview_card_text(text_pos, slots={}, conversation_id="CONV-TEST-P1")

    assert "CẢNH BÁO TÁI PHÁT (Bước 5):" in preview_pos
    assert "mã C7620 đã xuất hiện 3 lần" in preview_pos
    assert "FY27H2/263" in preview_pos
    assert "Đối sách đã áp dụng của ca gần nhất: **不要**" in preview_pos
    assert "LƯU Ý ĐỐI CHIẾU MÃ LỖI (Bước 5):" in preview_pos

    marker_pos = extract_case_preview_marker(preview_pos)
    assert marker_pos is not None
    assert marker_pos["is_recurrence"] is True
    assert marker_pos["recurrence_count"] == 3
    assert marker_pos["recurrence_from"] == "FY27H2/263"
    assert marker_pos["recurrence_remedy"] == "不要"
    assert marker_pos["suggested_cong_doan"] == "Điều chỉnh"

    # 2. Negative case: X9999
    text_neg = "Tạo vụ điều tra lỗi mới: máy hỏng mã X9999"
    preview_neg = render_preview_card_text(
        text_neg,
        slots={"error_code": "X9999", "phenomenon": "máy hỏng mã X9999"},
        conversation_id="CONV-TEST-N1",
    )

    assert "CẢNH BÁO TÁI PHÁT" not in preview_neg
    marker_neg = extract_case_preview_marker(preview_neg)
    assert marker_neg is not None
    assert marker_neg["is_recurrence"] is False
    assert marker_neg["recurrence_count"] == 0
    assert marker_neg["recurrence_msg"] == ""
    assert marker_neg["recurrence_remedy"] == ""
    assert marker_neg["recurrence_from"] == ""


def test_real_reconciled_db_c7620_exact_count():
    """Verify against the real reconciled database C:\\tmp\\kdtps_standard\\error_cases_reconciled.db.

    Checks:
    - DB has exactly 30,075 total cases.
    - Code C7620 has exactly 136 matching cases.
    - Most recent case is FY27H2/263 (occurred 2026-10-15, Virgo / C21, countermeasure 不要).
    """
    real_db = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")
    if not real_db.is_file():
        pytest.skip("Real reconciled DB not found on machine")

    uri = real_db.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM error_cases").fetchone()[0]
    assert total == 30075

    # Direct query count
    c7620_count = conn.execute(
        """SELECT COUNT(*) FROM error_cases
           WHERE REPLACE(UPPER(COALESCE(error_code_c, '')), ' ', '') = 'C7620'
              OR REPLACE(UPPER(COALESCE(error_code_h, '')), ' ', '') = 'C7620'
              OR REPLACE(UPPER(COALESCE(error_code_i, '')), ' ', '') = 'C7620'"""
    ).fetchone()[0]
    assert c7620_count == 136

    # Test detect_recurrence directly
    alert = detect_recurrence(conn, error_code="C7620")
    assert alert is not None
    assert alert.count == 136
    assert alert.suggested_from == "FY27H2/263"
    assert alert.suggested_remedy == "不要"
    assert "FY27H2/263" in alert.message_vi
    assert "2026-10-15" in alert.message_vi
    assert "Virgo / C21" in alert.message_vi

    conn.close()
