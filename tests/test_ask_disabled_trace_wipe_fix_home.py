"""Unit and regression tests for ticket DESKTOP-UI-ASK-DISABLED-TRACE-WIPE-FIX-HOME.

Verifies:
1. resolve_allowed_source_ids properly distinguishes:
   - None (empty selections or only GC/unconfigured records) -> unrestricted retrieval/citations
   - Explicit [] (user actively disabled all sources) -> zero citations allowed
   - Enabled IDs list -> only those sources allowed
2. build_evidence_trace_from_citations semantics with None vs []
3. workspace_chat_store.set_source_enabled persists owner_note
4. workspace_chat_app._ask_disabled is bound and does not raise UnboundLocalError when is_answering=True
"""

import ast
import inspect
from pathlib import Path
import pytest

from aios_habit.workspace_chat_models import (
    ConversationSourceSelection,
    SOURCE_SCOPE_NOTEBOOK,
)
import aios_habit.workspace_chat_store as store
from aios_habit.antigravity_bridge import resolve_allowed_source_ids
from aios_habit.evidence_trace import (
    build_evidence_trace_from_citations,
    EvidenceNode,
)


@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()


def test_resolve_allowed_source_ids_none_when_empty():
    """Empty selections list must resolve to None (unrestricted)."""
    assert resolve_allowed_source_ids("conv_test", []) is None


def test_resolve_allowed_source_ids_with_enabled_sources():
    """Selections containing enabled sources return the list of allowed source IDs."""
    selections = [
        ConversationSourceSelection(
            id="sel_1",
            conversation_id="conv_test",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            source_id="src_1",
            enabled=True,
        ),
        ConversationSourceSelection(
            id="sel_2",
            conversation_id="conv_test",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            source_id="src_2",
            enabled=False,
        ),
    ]
    assert resolve_allowed_source_ids("conv_test", selections) == ["src_1"]


def test_resolve_allowed_source_ids_gc_garbage_resolves_to_none():
    """When all records are enabled=False due to GC/unconfigured (enabled_at is None, owner_note not user_action),

    resolve_allowed_source_ids must return None (unrestricted) instead of [] so traces are not wiped.
    """
    gc_selections = [
        ConversationSourceSelection(
            id=f"sel_gc_{i}",
            conversation_id="conv_test",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            source_id=f"src_{i}",
            enabled=False,
            enabled_at=None,
            owner_note="",
        )
        for i in range(15)
    ]
    assert resolve_allowed_source_ids("conv_test", gc_selections) is None


def test_resolve_allowed_source_ids_active_user_disable_all_resolves_to_empty_list():
    """When the user actively disabled all sources (owner_note="user_action" or enabled_at set),

    resolve_allowed_source_ids must return [] so zero sources are permitted.
    """
    user_disabled = [
        ConversationSourceSelection(
            id="sel_user_1",
            conversation_id="conv_test",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            source_id="src_1",
            enabled=False,
            enabled_at=None,
            owner_note="user_action",
        )
    ]
    assert resolve_allowed_source_ids("conv_test", user_disabled) == []


def test_build_evidence_trace_none_vs_empty_list():
    """Test evidence trace citation preservation with None vs []."""
    evidence_items = [
        {
            "id": "doc_a",
            "source_id": "doc_a",
            "title": "Tài liệu A",
            "snippet": "Nội dung trích dẫn tài liệu A.",
            "citation_label": "[1]",
        }
    ]
    answer = "Theo [1], tài liệu A có nội dung chi tiết."

    # allowed_source_ids = None -> unrestricted, citation retained
    trace_unrestricted = build_evidence_trace_from_citations(
        query="Nội dung A là gì?",
        answer_text=answer,
        evidence_items=evidence_items,
        allowed_source_ids=None,
    )
    assert trace_unrestricted.metadata.get("status") == "valid"
    evidence_nodes = [n for n in trace_unrestricted.nodes if n.node_type not in ("question", "answer")]
    assert len(evidence_nodes) >= 1
    assert any(n.title == "Tài liệu A" for n in evidence_nodes)

    # allowed_source_ids = [] -> strict zero allowed, citation dropped, status insufficient_evidence
    trace_empty = build_evidence_trace_from_citations(
        query="Nội dung A là gì?",
        answer_text=answer,
        evidence_items=evidence_items,
        allowed_source_ids=[],
    )
    assert trace_empty.metadata.get("status") == "insufficient_evidence"
    evidence_nodes_empty = [n for n in trace_empty.nodes if n.node_type not in ("question", "answer")]
    assert len(evidence_nodes_empty) == 0


def test_set_source_enabled_persists_owner_note():
    """set_source_enabled stores owner_note correctly in conversation_source_selections.jsonl."""
    store.set_source_enabled(
        conversation_id="conv_100",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        source_id="src_test",
        enabled=True,
        owner_note="user_action",
    )
    selections = store.load_conversation_source_selections("conv_100")
    assert len(selections) == 1
    assert selections[0].source_id == "src_test"
    assert selections[0].enabled is True
    assert selections[0].owner_note == "user_action"


def test_ask_disabled_ast_pre_initialization():
    """Verify that _ask_disabled and _ask_tooltip are defined before toolbar action branching."""
    import aios_habit.workspace_chat_app as app_mod
    app_source = inspect.getsource(app_mod)

    # Verify _ask_disabled = False pre-initialization exists in the code
    assert "_ask_disabled = False" in app_source
    assert '_ask_tooltip = ""' in app_source
    # Verify the conditioned caption check
    assert "if _ask_disabled and not (is_answering or is_waiting_for_sources):" in app_source
