# -*- coding: utf-8 -*-
"""Automated tests for DESKTOP-HOME-CHAT-ERRORCODE-CASE-ROUTE-FIX.

Verifies:
1. Natural questions containing error codes (C7620, JAM4212) route to DB 30.075
   and synthesize answers with real case citations in Sổ Điều tra lỗi (NB-LAZY-DTL).
2. Bare error codes ("C7620", "JAM4212") retain Step 1 card rendering.
3. Cross-notebook trap (C7620 in mom_opcenter) remains locked / store-isolated.
4. Off-topic trap (C7620 + visa) is rejected and does not hit DB cases.
5. Code extraction regex supports JAM and C/F/J/S error codes.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from aios_habit import chat_action as ca
from aios_habit.chat_action_error_lookup import (
    ACTION_NAME,
    extract_codes,
    is_natural_question,
    _CODE_RE,
)
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer


@pytest.fixture(autouse=True)
def _reset_env():
    ca.reset_actions()
    ca.load_builtin_actions()
    yield
    ca.reset_actions()


def test_extract_codes_patterns():
    # Standard C-call
    assert "C7620" in extract_codes("Mã lỗi C7620 nguyên nhân chính là gì?")
    assert "C7620" in extract_codes("c7620")
    assert "C7620" in extract_codes("C-7620")

    # JAM patterns
    assert "JAM4212" in extract_codes("Mã lỗi JAM4212 trên máy Iris2024")
    assert "JAM4212" in extract_codes("jam4212")
    assert "JAM4212" in extract_codes("JAM-4212")
    assert "JAM4212" in extract_codes("J4212")

    # F-call and SCT
    assert "F000" in extract_codes("Mã F000")
    assert "S001" in extract_codes("S001")

    # Non-code queries
    assert extract_codes("Quy trình xin visa Thụy Sĩ") == []
    assert extract_codes("TH01 Touch Panel Storage") == []


def test_is_natural_question_distinction():
    # Bare codes -> False
    assert not is_natural_question("C7620")
    assert not is_natural_question("c7620")
    assert not is_natural_question("JAM4212")
    assert not is_natural_question("tra cứu C7620")

    # Natural questions -> True
    assert is_natural_question("Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?")
    assert is_natural_question("Mã lỗi JAM4212 trên máy Iris2024 có nguyên nhân và đối sách điều tra thế nào?")
    assert is_natural_question("Tại sao máy báo lỗi C7620?")


def test_natural_c7620_routes_to_db_cases_with_citations():
    q = "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?"
    req = ca.ChatActionRequest(
        question=q,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    outcome = ca.dispatch_multi(req)
    assert outcome is not None
    assert outcome.action == ACTION_NAME

    rendered = ca.render_outcome(outcome)
    # Must contain error code, glossary definition, and real citations
    assert "C7620" in rendered
    assert "Lỗi thời gian đăng ký màu" in rendered
    assert "30.075" in rendered or "30075" in rendered
    assert "Loi KDTPS.xlsx" in rendered or "History KDTPS" in rendered
    assert "Vụ" in rendered


def test_natural_jam4212_routes_to_db_cases_with_citations():
    q = "Mã lỗi JAM4212 trên máy Iris2024 có nguyên nhân và đối sách điều tra thế nào?"
    req = ca.ChatActionRequest(
        question=q,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    outcome = ca.dispatch_multi(req)
    assert outcome is not None
    assert outcome.action == ACTION_NAME

    rendered = ca.render_outcome(outcome)
    assert "JAM4212" in rendered
    assert "定着センサー滞留" in rendered or "JAM" in rendered
    assert "Vụ" in rendered
    assert "Loi KDTPS.xlsx" in rendered or "History KDTPS" in rendered


def test_bare_code_c7620_renders_step1_cards():
    q = "C7620"
    req = ca.ChatActionRequest(
        question=q,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    outcome = ca.dispatch_multi(req)
    assert outcome is not None
    rendered = ca.render_outcome(outcome)
    # Bare code renders Step 1 cards format
    assert "### 1. Vụ" in rendered
    assert "Tìm thấy" in rendered
    assert "ca mã lỗi **C7620**" in rendered or "ca lỗi liên quan đến **C7620**" in rendered


def test_cross_notebook_trap_locked():
    # Query with C7620 asked in Sổ MOM (mom_opcenter)
    q = "Mã lỗi C7620 trên cụm sấy có nguyên nhân gốc và đối sách điều tra là gì?"
    req = ca.ChatActionRequest(
        question=q,
        notebook_id="mom_opcenter",
        context={"forced_domain": "mom"},
    )
    outcome = ca.dispatch_multi(req)
    # Store-scope isolation: chat_action MUST NOT hijack MOM query
    assert outcome is None

    # In 5-tier ladder fallback, must provide truthful refusal (has warning banner)
    ok, text, meta, _ = deliver_5tier_ladder_answer(
        q,
        conversation_id="TEST-CROSS-TRAP",
        notebook_id="mom_opcenter",
    )
    assert ok
    assert meta.get("has_warning_banner") is True


def test_offtopic_trap_rejected():
    # Off-topic question containing an error code
    q = "Mã lỗi C7620 làm sao để xin visa du lịch Thụy Sĩ tự túc năm 2026?"
    req = ca.ChatActionRequest(
        question=q,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    outcome = ca.dispatch_multi(req)
    assert outcome is None

    # In 5-tier ladder fallback, must provide truthful refusal
    ok, text, meta, _ = deliver_5tier_ladder_answer(
        q,
        conversation_id="TEST-OFFTOPIC-TRAP",
        notebook_id="NB-LAZY-DTL",
    )
    assert ok
    assert meta.get("has_warning_banner") is True
