"""Unit tests for DESKTOP-PC0575-SYNC-DEDUP parity, deduplication, and invariants."""
from __future__ import annotations

import base64
from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.chat_intent_router import VE_BIEU_DO
from aios_habit.production_prediction.chart_selection import hieu_lenh_ve_bieu_do
from aios_habit.production_prediction.jig_chat_wire import JigChatOutcome
from aios_habit.workspace_chat_app import _xu_ly_mot_y_dinh


def test_jig_code_sorting_longest_first_parity():
    """Verify hieu_lenh_ve_bieu_do prefers longer JIG names and metric codes over shorter prefixes."""
    danh_sach_jig = ["BOW", "BOW_B", "BOW_B_EXTRA", "B"]
    danh_sach_chi_so = ["do_lech", "do_lech_tam_truc", "tam"]

    # When query mentions BOW_B, it must match 'BOW_B', not 'BOW' or 'B'
    res_jig = hieu_lenh_ve_bieu_do("vẽ biểu đồ cho BOW_B", danh_sach_jig, danh_sach_chi_so)
    assert res_jig.ma_jig == "BOW_B"

    # When query mentions do_lech_tam_truc, it must match 'do_lech_tam_truc', not 'do_lech' or 'tam'
    res_metric = hieu_lenh_ve_bieu_do("vẽ biểu đồ do_lech_tam_truc", danh_sach_jig, danh_sach_chi_so)
    assert res_metric.ten_chi_so == "do_lech_tam_truc"


def test_xu_ly_mot_y_dinh_returns_chart_without_duplication():
    """Verify _xu_ly_mot_y_dinh returns assistant text with exactly 1 chart embedding."""
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_data"
    b64_data = base64.b64encode(fake_png).decode("ascii")
    pre_embedded_md = f"Đã vẽ biểu đồ BOW_B.\n\n![biểu đồ](data:image/png;base64,{b64_data})"

    mock_outcome = JigChatOutcome(
        handled=True,
        assistant_text=pre_embedded_md,
        chart_png=fake_png,
        chart_meta={"ma_jig": "JIG-01", "ten_chi_so": "bowskew"},
    )

    mock_conv = MagicMock(id="conv_dedup_test")
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_ve_bieu_do", return_value=mock_outcome):
        result = _xu_ly_mot_y_dinh(
            VE_BIEU_DO,
            slots={},
            q_text="vẽ biểu đồ bowskew cho JIG-01",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )

    assert result is not None
    chart_marker = f"data:image/png;base64,{b64_data}"
    assert result.count(chart_marker) == 1


def test_workspace_chat_app_source_dedup_lock():
    """AST / text scan ensuring no consecutive duplicate disclaimer caption after render_ai_answer_header."""
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    assert app_path.exists()
    content = app_path.read_text(encoding="utf-8")

    # Locate AI Answer Badge render block
    start_idx = content.find('badge_data.get("operational_mode") == "local_grounded_fallback"')
    assert start_idx != -1
    block = content[start_idx:start_idx + 3500]

    # No immediate redundant st.caption(t("ai_disclaimer")) after render_ai_answer_header
    redundant_ext = re.search(
        r'render_ai_answer_header\([^)]*operational_mode="external_ai"[^)]*\)\s*\n\s*(st\.caption\(t\("ai_disclaimer"[^)]*\)\))',
        block,
    )
    assert redundant_ext is None

    redundant_grounded = re.search(
        r'render_ai_answer_header\([^)]*badge_data\.get\("source_count"\)[^)]*\)\s*\n(?:[^\n]*\n){1,4}\s*(st\.caption\(t\("ai_disclaimer"[^)]*\)\))',
        block,
    )
    assert redundant_grounded is None


def test_local_fallback_no_disclaimer_invariant():
    """FR-030 Invariant: local fallback block must not render disclaimer or AI header."""
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    content = app_path.read_text(encoding="utf-8")

    local_idx = content.find('badge_data.get("operational_mode") == "local_grounded_fallback"')
    assert local_idx != -1
    next_idx = content.find('elif (', local_idx)
    assert next_idx != -1

    local_block = content[local_idx:next_idx]
    assert "ai_disclaimer" not in local_block
    assert "render_ai_answer_header" not in local_block
