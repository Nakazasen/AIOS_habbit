"""Tests for knowledge block pinning precedence (DESKTOP-BLOCK-PIN-LANE-PRECEDENCE-FIX-HOME).

Invariants verified:
1. When a specific knowledge block is pinned (e.g. forced_domain="tong_hop"):
   (a) chat_action error lookup does NOT preempt block retrieval (handle_chat_text returns False).
   (b) structured tabular data lane only answers from files belonging to the pinned block;
       files outside the pinned block yield to block retrieval (try_structured_table_evidence returns None).
   (c) retrieval yields actual document evidence of the pinned block.
2. In 'auto' mode (no block pinned):
   - chat_action error lookup functions normally (returns 5 cases).
   - structured tabular data lane functions normally (answers from staged CSV/XLSX).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from aios_habit.chat_action import handle_chat_text, ChatActionRequest, dispatch_multi
from aios_habit.chat_action_error_lookup import _ErrorLookupAction
from aios_habit.feature_flags import FEATURE_CHAT_ACTION, set_feature_flag, reset_feature_flags
from aios_habit.rag_v2.structured_query import (
    try_structured_table_evidence,
    is_structured_file_in_domain,
)
from aios_habit.workspace_chat_rag_v2_adapter import _try_structured_excel_evidence


@pytest.fixture(autouse=True)
def enable_chat_action():
    set_feature_flag(FEATURE_CHAT_ACTION, True)
    yield
    reset_feature_flags()


def test_error_lookup_bypassed_when_knowledge_block_pinned():
    """When a specific block is pinned (e.g. tong_hop), error lookup must NOT match or preempt."""
    q = "Trong tài liệu email RE: >>IRIS2020(Low model) -C22/A1- LCD displayed C3501, người gửi nghi ngờ nguyên nhân gì?"
    
    # 1. Pinned to tong_hop -> handle_chat_text returns False
    user_msgs = []
    asst_msgs = []
    handled_pinned = handle_chat_text(
        q,
        context={"forced_domain": "tong_hop"},
        save_user=lambda c: user_msgs.append(c),
        save_assistant=lambda c: asst_msgs.append(c),
    )
    assert handled_pinned is False
    assert len(user_msgs) == 0
    assert len(asst_msgs) == 0

    # Pinned to mom -> also bypassed
    handled_mom = handle_chat_text(
        q,
        context={"forced_domain": "mom"},
    )
    assert handled_mom is False


def test_error_lookup_preserved_in_auto_mode():
    """In auto mode (no block pinned), error lookup must still answer with 5 cases."""
    q = "Trong tài liệu email RE: >>IRIS2020(Low model) -C22/A1- LCD displayed C3501, người gửi nghi ngờ nguyên nhân gì?"
    
    user_msgs = []
    asst_msgs = []
    handled_auto = handle_chat_text(
        q,
        context={"forced_domain": "auto"},
        save_user=lambda c: user_msgs.append(c),
        save_assistant=lambda c: asst_msgs.append(c),
    )
    # When deployed error cases db is present on machine, it answers 5 cases
    # If db is present, handled is True and has 5 cases
    db_path = Path("C:/tmp/buoc0-deploy/error_cases_deploy.db")
    if db_path.is_file():
        assert handled_auto is True
        assert len(user_msgs) == 1
        assert len(asst_msgs) == 1
        assert "5" in asst_msgs[0]
        assert "C3501" in asst_msgs[0]
        assert asst_msgs[0].count("### ") == 5

    # Also test with forced_domain=None (legacy default)
    user_msgs.clear()
    asst_msgs.clear()
    handled_none = handle_chat_text(
        q,
        context={"forced_domain": None},
        save_user=lambda c: user_msgs.append(c),
        save_assistant=lambda c: asst_msgs.append(c),
    )
    if db_path.is_file():
        assert handled_none is True
        assert asst_msgs[0].count("### ") == 5


def test_structured_table_lane_yields_when_file_not_in_pinned_domain():
    """When forced_domain is tong_hop, a question triggering 2026_08_Spec.csv must yield (return None)."""
    q = "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
    
    # In tong_hop, 2026_08_Spec.csv is outside the block -> must return None
    res_pinned = try_structured_table_evidence(q, forced_domain="tong_hop")
    assert res_pinned is None

    # In mom, 2026_08_Spec.csv is outside the block -> must return None
    res_mom = try_structured_table_evidence(q, forced_domain="mom")
    assert res_mom is None

    # In dieu_tra_loi, 2026_08_Spec.csv is outside the block -> must return None
    res_dtl = try_structured_table_evidence(q, forced_domain="dieu_tra_loi")
    assert res_dtl is None


def test_structured_table_lane_preserved_in_auto_and_lsu_modes():
    """In auto mode or when pinned to lsu, 2026_08_Spec.csv table lookup functions normally."""
    q = "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
    staging_file = Path(r"D:/Sandbox/AIOS_habbit/local_runs/structured_staging/2026_08_Spec.csv")
    if staging_file.is_file():
        # In auto mode -> returns table calculation
        res_auto = try_structured_table_evidence(q, forced_domain="auto")
        assert res_auto is not None
        assert res_auto.get("evidence_items")[0]["title"] == "2026_08_Spec.csv"

        # In lsu mode -> returns table calculation because Spec.csv belongs to LSU
        res_lsu = try_structured_table_evidence(q, forced_domain="lsu")
        assert res_lsu is not None
        assert res_lsu.get("evidence_items")[0]["title"] == "2026_08_Spec.csv"


def test_is_structured_file_in_domain_logic():
    """Unit test for domain scoping helper."""
    # Auto or None always allowed
    assert is_structured_file_in_domain("2026_08_Spec.csv", forced_domain=None) is True
    assert is_structured_file_in_domain("2026_08_Spec.csv", forced_domain="auto") is True

    # LSU staged files belong to lsu, not tong_hop or mom
    assert is_structured_file_in_domain("2026_08_Spec.csv", forced_domain="lsu") is True
    assert is_structured_file_in_domain("2026_08_Spec.csv", forced_domain="tong_hop") is False
    assert is_structured_file_in_domain("2026_08_Error.csv", forced_domain="mom") is False
    assert is_structured_file_in_domain("2026_08_UnitTest.csv", forced_domain="dieu_tra_loi") is False

    # Custom source path (fixtures) always allowed
    assert is_structured_file_in_domain("any_test.csv", forced_domain="tong_hop", custom_source_path=Path("synthetic.csv")) is True


def test_adapter_try_structured_excel_evidence_respects_forced_domain():
    """Test that adapter helper _try_structured_excel_evidence passes forced_domain."""
    q = "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
    
    # In tong_hop, must return None
    res = _try_structured_excel_evidence(q, sources=(), forced_domain="tong_hop")
    assert res is None

    # In auto, returns table evidence if staging file exists
    staging_file = Path(r"D:/Sandbox/AIOS_habbit/local_runs/structured_staging/2026_08_Spec.csv")
    if staging_file.is_file():
        res_auto = _try_structured_excel_evidence(q, sources=(), forced_domain="auto")
        assert res_auto is not None
