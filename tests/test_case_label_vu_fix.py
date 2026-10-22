# -*- coding: utf-8 -*-
"""Comprehensive verification tests for ticket DESKTOP-HOME-CASE-LABEL-VU-FIX.

Tests:
1. Unit tests for explain_case_number: YEAR/SEQ, FY.../..., Y/D prefixes, fallbacks.
2. C6770 synthesized answer verification:
   - Every case card starts with '**X. Vụ ...**'
   - Every case card has a small explanation line '- _Số đăng ký vụ việc trong sổ gốc: ..._'
   - Total lack of 'Phiếu' in answer body text.
   - Machine, Serial, Date, and citation lines strictly preserved.
3. Bare code cards rendering verification:
   - Headers use '### X. Vụ ...'
   - Explanation lines generated dynamically from number format.
   - Deep-dive footer uses 'VD: vụ 2023/5'.
   - No 'Phiếu' in rendered markdown.
4. Step 5 Recurrence Alert for C7620:
   - Consistent 'vụ' wording: 'vụ FY27H2/263' and '*(từ vụ `FY27H2/263`)*'.
   - Recurrence count preserved at 136 cases.
   - Most recent case registration number preserved as original data.
5. Citation Source Viewer:
   - Title uses 'Hồ sơ ca điều tra lịch sử: Vụ ...'.
   - Column labels use 'Số vụ điều tra'.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from aios_habit.chat_action import ChatActionRequest, dispatch_multi, render_outcome
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_cards,
    _render_synthesized_answer,
    explain_case_number,
    extract_codes,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)
from aios_habit.citation_source_viewer import (
    CitationRef,
    resolve_citation_source,
)

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.fixture(scope="module")
def db_conn():
    if not DB_PATH.is_file():
        pytest.skip(f"Reconciled error_cases DB not found at {DB_PATH}")
    conn = _open_ro(DB_PATH)
    yield conn
    conn.close()


def test_explain_case_number_patterns():
    """Verify dynamic case registration number explanation generation across formats."""
    # Format 1: YEAR/SEQ (e.g. 2025/1155, 2023/38)
    exp1 = explain_case_number("2025/1155")
    assert exp1 == "Số đăng ký vụ việc trong sổ gốc: 2025 là năm, 1155 là số thứ tự vụ trong năm"

    exp1b = explain_case_number("2023/38")
    assert exp1b == "Số đăng ký vụ việc trong sổ gốc: 2023 là năm, 38 là số thứ tự vụ trong năm"

    # Format 2: FY.../... (e.g. FY27H2/263, FY26ET/1)
    exp2 = explain_case_number("FY27H2/263")
    assert exp2 == "Số đăng ký vụ việc trong sổ gốc: kỳ tài khóa FY27H2, vụ thứ 263"

    exp2b = explain_case_number("FY26ET/1")
    assert exp2b == "Số đăng ký vụ việc trong sổ gốc: kỳ tài khóa FY26ET, vụ thứ 1"

    # Format 3: Y/D prefixes (e.g. Y2015/0_r463, D2019/100)
    exp3 = explain_case_number("Y2015/0_r463")
    assert exp3 == "Số đăng ký vụ việc trong sổ gốc: năm 2015, vụ thứ 0 (bản ghi r463)"

    exp3b = explain_case_number("D2019/100")
    assert exp3b == "Số đăng ký vụ việc trong sổ gốc: năm 2019, vụ thứ 100"

    # Format 4: Fallback / other codes
    exp4 = explain_case_number("PV-DTL-20261022-0001")
    assert exp4 == "Số đăng ký vụ việc trong sổ gốc: mã PV-DTL-20261022-0001"

    # Empty / None
    assert explain_case_number("") == ""
    assert explain_case_number("—") == ""
    assert explain_case_number(None) == ""


def test_c6770_synthesized_answer_vu_label_and_explanation(db_conn):
    """Verify C6770 synthesized answer displays 'Vụ' and explanation line without 'Phiếu'."""
    q_text = "Mã lỗi C6770 nguyên nhân là gì?"
    codes = extract_codes(q_text)
    cases, _, total = search_similar(db_conn, q_text)
    gloss = lookup_glossary(db_conn, codes)
    ans = _render_synthesized_answer(cases, codes, gloss, total, q_text)

    # 1. Total cases check
    assert total == 30075
    assert len(cases) >= 3

    # 2. Section 4 header check
    assert "### 4. Danh sách các ca điều tra thực tế đối chiếu" in ans

    # 3. Case card headers must use '**X. Vụ ...**'
    card_headers = re.findall(r"\*\*\d+\.\s+Vụ\s+[^\*]+\*\*", ans)
    assert len(card_headers) == len(cases[:5])

    # 4. Each card must have an explanation line
    exp_lines = re.findall(r"- _Số đăng ký vụ việc trong sổ gốc:[^_\n]+_", ans)
    assert len(exp_lines) == len(cases[:5])

    # 5. Absolutely no 'Phiếu' in the rendered answer
    assert "Phiếu" not in ans
    assert "phiếu" not in ans

    # 6. Preserves Máy | Serial | Ngày phát sinh line
    assert "- **Máy:**" in ans
    assert "| **Serial:**" in ans
    assert "| **Ngày phát sinh:**" in ans

    # 7. Preserves original report location citation
    assert "- **Báo cáo gốc:**" in ans


def test_bare_code_cards_vu_label_and_explanation(db_conn):
    """Verify bare code 'C6770' cards render '### X. Vụ ...' with explanation line."""
    cases, codes, total = search_similar(db_conn, "C6770")
    gloss = lookup_glossary(db_conn, codes)
    cards_text = _render_cards(cases, codes, gloss, total)

    # 1. Headers use '### X. Vụ ...'
    headers = re.findall(r"### \d+\.\s+Vụ\s+", cards_text)
    assert len(headers) == len(cases)

    # 2. Explanation lines present
    assert "- _Số đăng ký vụ việc trong sổ gốc:" in cards_text

    # 3. Footer uses 'vụ'
    assert "Muốn đào sâu một ca, hỏi theo mã vụ (VD: `vụ 2023/5`)." in cards_text

    # 4. Absolutely no 'Phiếu' in cards
    assert "Phiếu" not in cards_text
    assert "phiếu" not in cards_text


def test_step5_recurrence_card_c7620_vu_label():
    """Verify Step 5 Recurrence Alert for C7620 uses consistent 'vụ' label and retains 136 cases."""
    q = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    req = ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL")
    outcome = dispatch_multi(req)
    assert outcome is not None

    rendered = render_outcome(outcome)

    # 1. Recurrence count retained at 136 cases
    assert "136 lần" in rendered or "136 ca" in rendered

    # 2. Most recent case uses 'vụ FY27H2/263'
    assert "vụ FY27H2/263" in rendered
    assert "*(từ vụ `FY27H2/263`)*" in rendered

    # 3. No 'phiếu' in recurrence alert
    alert_section = re.search(r"> ⚠️ \*\*CẢNH BÁO TÁI PHÁT \(Bước 5\):\*\*.*?(?=\n\n|\Z)", rendered, re.DOTALL)
    assert alert_section is not None
    alert_text = alert_section.group(0)
    assert "phiếu" not in alert_text.lower()


def test_citation_source_viewer_vu_label(db_conn):
    """Verify Source Viewer title and column labels use 'Vụ' instead of 'Phiếu'."""
    ref = CitationRef(
        id="case_row_9609",
        ref_type="db_error_case",
        label="Loi KDTPS.xlsx › History KDTPS › dòng 9609",
        source_file="Loi KDTPS.xlsx",
        sheet_name="History KDTPS",
        source_row=9609,
    )
    payload = resolve_citation_source(ref)
    assert payload.found is True
    assert payload.source_type == "db_error_case"
    assert "Vụ 2025/1155" in payload.title
    assert "Phiếu" not in payload.title

    # Column A-B label
    field_ab = next((f for f in payload.fields if f.column_letter == "A-B"), None)
    assert field_ab is not None
    assert field_ab.label_vi == "Số vụ điều tra"
    assert "Phiếu" not in field_ab.label_vi
