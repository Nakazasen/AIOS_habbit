# -*- coding: utf-8 -*-
"""Regression and verification tests for ticket DESKTOP-HOME-STRUCTURED-LOOKUP-TRUTH-FIX.

Requirements:
2(a) Honest Count Title:
     - C0060: 2 exact cases, 3 same-family fallback cases (C_CALL).
     - C7620: 136 total cases in DB 30.075 cases, displays 5 most relevant.
2(b) Case Label 'Vụ' + gloss explain_case_number().
2(c) Pure Vietnamese translation: no raw Japanese tokens left standing alone
     (e.g. 不要, 部品要因(電気), 原因不明（メカ）, 要因不明(製造)).
2(d) Step 5 Recurrence Card C7620 clean countermeasure (no raw 不要).
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest

from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_error_lookup import (
    _handler,
    _open_ro,
    explain_case_number,
    count_exact_cases,
    search_similar,
)
from aios_habit.error_cases.auto_classifier import detect_recurrence

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.fixture(scope="module")
def db_conn():
    if not DB_PATH.is_file():
        pytest.skip(f"Reconciled error_cases DB not found at {DB_PATH}")
    conn = _open_ro(DB_PATH)
    yield conn
    conn.close()


def test_count_exact_cases_c0060_and_c7620(db_conn):
    """Verify exact match count logic for rare vs common codes."""
    assert count_exact_cases(db_conn, ["C0060"]) == 2
    assert count_exact_cases(db_conn, ["C7620"]) == 136


def test_c0060_honest_count_and_family_badges(db_conn):
    """Verify C0060 cards output:
    - 2 exact cases + 3 same-family C_CALL cases
    - Honest title separating exact from fallback
    - Badges [Khớp chính xác C0060] and [Tham khảo cùng họ C_CALL]
    """
    req = ChatActionRequest(question="Tra cứu mã lỗi C0060")
    outcome = _handler(req)
    assert outcome is not None
    text = "".join(b.text for b in outcome.blocks if b.kind == "markdown")

    # Honest title check
    assert "Tìm thấy **2** ca **C0060** chính xác;" in text
    assert "hiển thị thêm **3** ca cùng họ **C_CALL** để tham khảo" in text

    # Badges check
    assert "[Khớp chính xác C0060]" in text
    assert "[Tham khảo cùng họ C_CALL]" in text

    # Every case uses 'Vụ'
    assert "### 1. Vụ 2025/1978" in text
    assert "### 2. Vụ 2023/575" in text
    assert "### 3. Vụ 2024/550" in text

    # Explanation gloss
    assert "Số đăng ký vụ việc trong sổ gốc:" in text

    # No raw Japanese in remedy or cause
    assert "不要" not in text
    assert "原因不明" not in text
    assert "部品要因" not in text


def test_c7620_honest_total_and_translated_fields(db_conn):
    """Verify C7620 synthesized answer output:
    - True total 136 cases in DB 30.075 cases
    - Displays 5 most relevant cases
    - Case label 'Vụ' with gloss
    - Translated countermeasure and cause (no raw 不要)
    """
    req = ChatActionRequest(question="Mã lỗi C7620 nguyên nhân thường gặp là gì?")
    outcome = _handler(req)
    assert outcome is not None
    text = "".join(b.text for b in outcome.blocks if b.kind == "markdown")

    # Honest total in Section 4
    assert "Tìm thấy **136** ca điều tra thực tế mã lỗi **C7620** trong CSDL 30.075 ca (hiển thị **5** ca liên quan nhất):" in text

    # Every case uses 'Vụ'
    assert "**1. Vụ 2024/3632**" in text
    assert "Số đăng ký vụ việc trong sổ gốc:" in text

    # No raw Japanese standing alone
    assert "不要" not in text
    assert "原因不明（メカ）" not in text
    assert "部品要因(電気)" not in text
    assert "要因不明(製造)" not in text


def test_step5_recurrence_c7620_translated_remedy(db_conn):
    """Verify Step 5 recurrence alert translates suggested remedy and no raw 不要 appears."""
    alert = detect_recurrence(db_conn, "C7620")
    assert alert is not None
    assert alert.count == 136
    assert alert.suggested_from == "FY27H2/263"
    assert "不要" not in alert.suggested_remedy
    assert "Không cần đối sách" in alert.suggested_remedy
    assert "vụ FY27H2/263" in alert.message_vi


def test_explain_case_number_float_cleaning():
    """Verify float sequence trailing '.0' is stripped."""
    assert explain_case_number("2023/5.0") == "Số đăng ký vụ việc trong sổ gốc: 2023 là năm, 5 là số thứ tự vụ trong năm"
    assert explain_case_number("2025/1155") == "Số đăng ký vụ việc trong sổ gốc: 2025 là năm, 1155 là số thứ tự vụ trong năm"
