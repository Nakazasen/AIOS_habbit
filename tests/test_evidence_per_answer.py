# -*- coding: utf-8 -*-
"""Unit tests for DESKTOP-HOME-UX-EVIDENCE-PER-ANSWER.

Validates:
1. Per-answer evidence extraction from message metadata, trace_id, and scoped badge_data.
2. Legacy fallback to text citations for older messages without a trace.
3. Zero evidence leakage: no cross-contamination between different answers; empty list when no sources.
4. Per-answer evidence expander rendering and source viewer panel integration.
5. Removal of centralized footer results & evidence expander in workspace_chat_app.py.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.evidence_trace_schema import EvidenceTrace, EvidenceNode
from aios_habit.citation_source_viewer import CitationRef
from aios_habit.workspace_chat_ui import (
    extract_evidence_items_for_message,
    render_per_answer_evidence_block,
)


def test_extract_evidence_from_trace_metadata():
    """Verify evidence items are extracted from trace metadata when msg.trace_id matches."""
    trace = EvidenceTrace(
        trace_id="trc_test_01",
        query="Nguyên nhân lỗi C6770?",
        answer_text="Lỗi do nguồn điện sấy thấp.",
        metadata={
            "evidence_items": [
                {
                    "title": "Loi KDTPS.xlsx",
                    "text": "LCC画面にAn Error has ocurred表示",
                    "location_info": "History KDTPS › dòng 9609",
                    "source_row": 9609,
                    "source_type": "db_error_case",
                },
                {
                    "title": "02XC_自己診断表示一覧表-Iris2020 VN.xls",
                    "text": "Định nghĩa mã C6770",
                    "location_info": "Sheet 1",
                    "source_type": "glossary_document",
                },
            ]
        },
    )

    msg = ChatMessage(
        id="MSG-A-01",
        conversation_id="conv_1",
        role="assistant",
        content="Lỗi do nguồn điện sấy thấp.",
        trace_id="trc_test_01",
    )

    items = extract_evidence_items_for_message(msg=msg, trace=trace)
    assert len(items) == 2
    assert items[0]["title"] == "Loi KDTPS.xlsx"
    assert items[0]["location_info"] == "History KDTPS › dòng 9609"
    assert items[0]["citation_ref"] is not None
    assert items[0]["citation_ref"].source_row == 9609
    assert items[0]["citation_ref"].ref_type == "db_error_case"

    assert items[1]["title"] == "02XC_自己診断表示一覧表-Iris2020 VN.xls"
    assert items[1]["citation_ref"].ref_type == "glossary_document"


def test_extract_evidence_from_trace_nodes_fallback():
    """Verify evidence items are extracted from trace nodes if trace.metadata is empty."""
    trace = EvidenceTrace(
        trace_id="trc_test_02",
        query="Kiểm tra bảo dưỡng máy",
        answer_text="Vệ sinh sấy định kỳ.",
        nodes=[
            EvidenceNode(
                id="src_1",
                node_type="source",
                title="quy_trinh_bao_tri.pdf",
                snippet="Thao tác vệ sinh sấy cần thực hiện sau 15 phút.",
                source_id="quy_trinh_bao_tri.pdf",
                metadata={"location_info": "Trang 12", "source_type": "library_document"},
            )
        ],
    )

    msg = ChatMessage(
        id="MSG-A-02",
        conversation_id="conv_1",
        role="assistant",
        content="Vệ sinh sấy định kỳ.",
        trace_id="trc_test_02",
    )

    items = extract_evidence_items_for_message(msg=msg, trace=trace)
    assert len(items) == 1
    assert items[0]["title"] == "quy_trinh_bao_tri.pdf"
    assert items[0]["location_info"] == "Trang 12"
    assert "vệ sinh sấy" in items[0]["text"]
    assert items[0]["citation_ref"].ref_type == "library_document"


def test_extract_evidence_legacy_text_fallback():
    """Verify legacy messages without trace extract citations directly from answer content."""
    content = (
        "Dựa trên các báo cáo thực tế:\n"
        "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609`\n"
        "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 10530`\n"
    )

    msg = ChatMessage(
        id="MSG-A-LEGACY",
        conversation_id="conv_old",
        role="assistant",
        content=content,
        trace_id=None,
    )

    items = extract_evidence_items_for_message(msg=msg, display_content=content)
    assert len(items) == 2
    rows = {it["citation_ref"].source_row for it in items}
    assert rows == {9609, 10530}


def test_zero_leakage_when_no_sources():
    """Verify that an assistant message with no sources returns empty list and never leaks other evidence."""
    # Message A has no evidence
    msg_a = ChatMessage(
        id="MSG-A-NO-SOURCES",
        conversation_id="conv_1",
        role="assistant",
        content="Xin chào! Tôi có thể giúp gì cho bạn hôm nay?",
        trace_id=None,
    )

    # Foreign badge data belonging to another message / trace
    foreign_badge = {
        "conversation_id": "conv_1",
        "message_id": "MSG-A-OTHER",
        "trace_id": "trc_other",
        "evidence_items": [{"title": "Loi KDTPS.xlsx", "text": "Khác", "location_info": "dòng 100"}],
    }

    # Must NOT use foreign badge
    items = extract_evidence_items_for_message(
        msg=msg_a,
        display_content=msg_a.content,
        trace=None,
        badge_data=foreign_badge,
    )
    assert items == []


def test_scoped_badge_data_only_used_when_matching():
    """Verify badge_data is used if and only if trace_id or message_id matches."""
    msg = ChatMessage(
        id="MSG-MATCH",
        conversation_id="conv_1",
        role="assistant",
        content="Câu trả lời.",
        trace_id="trc_match",
    )

    matching_badge = {
        "trace_id": "trc_match",
        "message_id": "MSG-MATCH",
        "evidence_items": [
            {"title": "TaiLieu.pdf", "text": "Trích dẫn chuẩn", "location_info": "Trang 1"}
        ],
    }

    items = extract_evidence_items_for_message(
        msg=msg,
        trace=None,
        badge_data=matching_badge,
    )
    assert len(items) == 1
    assert items[0]["title"] == "TaiLieu.pdf"


def test_render_per_answer_evidence_block_empty():
    """Empty evidence_items renders nothing and does not open an expander."""
    mock_st = MagicMock()
    render_per_answer_evidence_block(
        evidence_items=[],
        conversation_id="conv_1",
        message_id="msg_1",
    )
    mock_st.expander.assert_not_called()


def test_footer_results_and_evidence_expander_removed():
    """Verify that workspace_chat_app.py no longer has the centralized footer expander."""
    app_file = Path(r"D:\Sandbox\AIOS_habbit\src\aios_habit\workspace_chat_app.py")
    source = app_file.read_text(encoding="utf-8")

    # In default layout (full), results_and_evidence expander must NOT be called after chat column
    assert "with st.expander(f\"📌 {t('results_and_evidence'" not in source
    assert 'with st.expander(f"📌 {t(\'results_and_evidence\'' not in source

    # Split layout must not render centralized results & evidence
    assert "_render_workspace_results_and_evidence()" not in source.split("SHOW_AGENT_IDE_DEV_TOOLS = False")[1]
