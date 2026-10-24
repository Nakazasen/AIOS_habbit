# -*- coding: utf-8 -*-
"""Guard tests for DESKTOP-HOME-ERRORLOOKUP-ROUTING-FIX.

Verifies:
1. Document content queries containing error codes (KTD-..., .xlsx, 'tài liệu ... có nội dung gì')
   are NOT intercepted by _ErrorLookupAction and fall through to RAG.
2. Pure error lookup queries ('lỗi C6770 là gì', 'C7620') retain the existing error lookup card route.
3. continuous improvement routing events are logged with correct decisions and metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aios_habit import chat_action as ca
from aios_habit.chat_action_error_lookup import (
    ACTION_NAME,
    _ErrorLookupAction,
    is_document_content_query,
    log_routing_event,
)
from aios_habit.feature_flags import override_feature_flags, reset_feature_flags


@pytest.fixture(autouse=True)
def _reset_env():
    reset_feature_flags()
    ca.reset_actions()
    ca.load_builtin_actions()
    yield
    reset_feature_flags()
    ca.reset_actions()


# ---------------------------------------------------------------------------
# 1. Unit tests for is_document_content_query
# ---------------------------------------------------------------------------


def test_is_document_content_query_detection():
    # R3 problem queries with error codes
    assert is_document_content_query("Tài liệu KTD-2026-06-0647 Iris2024 C33 A JAM4212 có nội dung gì?")
    assert is_document_content_query("Tài liệu KTD-2026-06-0527 Iris2024 C33 A1.2 C3100 có nội dung gì?")
    assert is_document_content_query("Tai lieu KTD-2026-06-0647 Iris2024 C33 A JAM4212 co noi dung gi?")

    # Document code patterns
    assert is_document_content_query("KTD-2026-06-0647 có nội dung gì?")
    assert is_document_content_query("Nội dung báo cáo KTD-2026-06-0527")
    assert is_document_content_query("KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx")

    # Document content phrasing without KTD code
    assert is_document_content_query("Tài liệu Iris2024 C33 A JAM4212 có nội dung gì?")
    assert is_document_content_query("Nội dung tài liệu JAM4212 là gì?")
    assert is_document_content_query("Tóm tắt tài liệu C3100")
    assert is_document_content_query("Tệp KTD-2026-06-0647.xlsx nói về cái gì?")

    # Pure error lookup queries -> False
    assert not is_document_content_query("loi C6770 la gi")
    assert not is_document_content_query("Mã lỗi C6770 là gì?")
    assert not is_document_content_query("C7620")
    assert not is_document_content_query("JAM4212")
    assert not is_document_content_query("Mã lỗi C7620 trên Sirius 2 nguyên nhân là gì?")
    assert not is_document_content_query(
        "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?"
    )
    assert not is_document_content_query(
        "Mã lỗi JAM4212 trên máy Iris2024 có nguyên nhân và đối sách điều tra thế nào?"
    )


# ---------------------------------------------------------------------------
# 2. _ErrorLookupAction.matches routing distinction
# ---------------------------------------------------------------------------


def test_action_does_not_match_document_content_queries():
    q_jam = "Tài liệu KTD-2026-06-0647 Iris2024 C33 A JAM4212 có nội dung gì?"
    req_jam = ca.ChatActionRequest(
        question=q_jam,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    action = ca.match_action(req_jam)
    # Must NOT match _ErrorLookupAction (allows RAG to handle)
    assert action is None or action.name != ACTION_NAME

    q_c3100 = "Tài liệu KTD-2026-06-0527 Iris2024 C33 A1.2 C3100 có nội dung gì?"
    req_c3100 = ca.ChatActionRequest(
        question=q_c3100,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    action_c3100 = ca.match_action(req_c3100)
    assert action_c3100 is None or action_c3100.name != ACTION_NAME


def test_action_matches_pure_error_queries():
    # Pure error code queries in Sổ Điều tra lỗi still match ErrorLookupAction
    q_c6770 = "loi C6770 la gi"
    req_c6770 = ca.ChatActionRequest(
        question=q_c6770,
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    action_c6770 = ca.match_action(req_c6770)
    assert action_c6770 is not None
    assert action_c6770.name == ACTION_NAME

    # Bare code
    req_bare = ca.ChatActionRequest(
        question="C7620",
        notebook_id="NB-LAZY-DTL",
        context={"forced_domain": "dieu_tra_loi"},
    )
    action_bare = ca.match_action(req_bare)
    assert action_bare is not None
    assert action_bare.name == ACTION_NAME


# ---------------------------------------------------------------------------
# 3. handle_chat_text integration
# ---------------------------------------------------------------------------


def test_handle_chat_text_yields_for_document_queries():
    saved_assistant = []
    with override_feature_flags(chat_action=True):
        handled = ca.handle_chat_text(
            "Tài liệu KTD-2026-06-0647 Iris2024 C33 A JAM4212 có nội dung gì?",
            conversation_id="CONV-TEST-JAM",
            notebook_id="NB-LAZY-DTL",
            save_user=lambda c: None,
            save_assistant=lambda c: saved_assistant.append(c),
        )
        # Not handled by chat_action -> must fall through to RAG pipeline
        assert handled is False
        assert len(saved_assistant) == 0


def test_handle_chat_text_handles_pure_error_queries():
    saved_assistant = []
    with override_feature_flags(chat_action=True):
        handled = ca.handle_chat_text(
            "C7620",
            conversation_id="CONV-TEST-C7620",
            notebook_id="NB-LAZY-DTL",
            save_user=lambda c: None,
            save_assistant=lambda c: saved_assistant.append(c),
        )
        assert handled is True
        assert len(saved_assistant) == 1
        assert "Tra cứu lỗi tương tự" in saved_assistant[0] or "C7620" in saved_assistant[0]


# ---------------------------------------------------------------------------
# 4. Continuous improvement routing event logging
# ---------------------------------------------------------------------------


def test_log_routing_event(tmp_path):
    log_routing_event(
        question="Tài liệu KTD-2026-06-0647 Iris2024 C33 A JAM4212 có nội dung gì?",
        decision="rag_pipeline",
        codes=["JAM4212"],
        is_doc_query=True,
        conversation_id="CONV-123",
        base_dir=tmp_path,
    )
    log_file = tmp_path / "errorlookup_routing_events.jsonl"
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["decision"] == "rag_pipeline"
    assert event["is_document_content_query"] is True
    assert event["codes"] == ["JAM4212"]
    assert event["conversation_id"] == "CONV-123"
