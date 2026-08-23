# -*- coding: utf-8 -*-
"""Tier 1, Tier 2, & Tier 3 Test Suite for Commit B: Local Persistence & Storage Lifecycle.

Opaque-box and requirement-driven test suite validating:
1. `workspace_chat_store.py` persistence functions:
   - `save_evidence_trace(trace)`
   - `load_evidence_trace(trace_id)`
   - `load_conversation_traces(conversation_id)`
   - `load_message_trace(message_id)`
   - `WorkspaceChatStore` class wrapper parity.
2. Idempotency guarantees:
   - Saving multiple times with the same `assistant_message_id` replaces in place,
     resulting in exactly 1 record in `traces.jsonl`.
3. Restart survival:
   - Preserves complete trace graph, nodes, edges, and provenance across store re-initializations
     and cache clearing.
4. Cascade deletion:
   - `delete_conversation(conv_id)` purges all associated traces atomically.
   - `delete_notebook_permanently(notebook_id)` purges all associated traces across all conversations.
5. Error handling and boundary resilience:
   - Missing IDs return None / empty lists.
   - Corrupted JSONL lines are skipped safely without crashing the store.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pytest

import aios_habit.workspace_chat_store as chat_store
from aios_habit.evidence_trace_schema import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.local_jsonl import clear_jsonl_cache
from aios_habit.workspace_chat_models import (
    ChatMessage,
    DocumentNotebook,
    WorkspaceConversation,
)


@pytest.fixture(autouse=True)
def sandboxed_chat_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sandbox all Workspace Chat storage files to an isolated temporary directory."""
    test_dir = tmp_path / "workspace_chat"
    test_dir.mkdir(parents=True, exist_ok=True)
    traces_file = test_dir / "traces.jsonl"

    monkeypatch.setattr(chat_store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(chat_store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(chat_store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(chat_store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(chat_store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(chat_store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(chat_store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    monkeypatch.setattr(chat_store, "TRACES_FILE", traces_file, raising=False)

    clear_jsonl_cache()
    chat_store.init_chat_store()
    yield test_dir
    clear_jsonl_cache()


def _create_sample_trace(
    trace_id: str,
    conversation_id: str = "conv_100",
    assistant_message_id: str = "msg_ast_100",
    user_message_id: str = "msg_usr_100",
    notebook_id: str = "nb_main",
    query: str = "Câu hỏi thử nghiệm?",
    answer_text: str = "Câu trả lời có trích dẫn [1].",
) -> EvidenceTrace:
    """Helper to construct a populated EvidenceTrace for persistence testing."""
    nodes = [
        EvidenceNode(
            id=f"{trace_id}_src1",
            node_type="source",
            title="Tài liệu mẫu",
            snippet="Nội dung nguồn tài liệu.",
            source_id="local_cases/docs/sample.txt",
        ),
        EvidenceNode(
            id=f"{trace_id}_chk1",
            node_type="chunk",
            title="Đoạn 1",
            snippet="Nội dung trích đoạn.",
            source_id=f"{trace_id}_src1",
        ),
        EvidenceNode(
            id=f"{trace_id}_cit1",
            node_type="citation",
            title="[1]",
            snippet="Trích dẫn đoạn 1",
            source_id=f"{trace_id}_src1",
            citation_id="[1]",
        ),
        EvidenceNode(
            id=f"{trace_id}_ans1",
            node_type="answer",
            title="Câu trả lời",
            snippet=answer_text,
        ),
    ]
    edges = [
        EvidenceEdge(
            source_id=f"{trace_id}_chk1",
            target_id=f"{trace_id}_src1",
            relation_type="extracted_from",
        ),
        EvidenceEdge(
            source_id=f"{trace_id}_cit1",
            target_id=f"{trace_id}_chk1",
            relation_type="derived_from",
        ),
        EvidenceEdge(
            source_id=f"{trace_id}_ans1",
            target_id=f"{trace_id}_cit1",
            relation_type="cites",
        ),
    ]
    return EvidenceTrace(
        schema_version="rag-trace/v1",
        trace_id=trace_id,
        query=query,
        answer_text=answer_text,
        ui_locale="vi",
        answer_language="vi",
        source_language="vi",
        nodes=nodes,
        edges=edges,
        metadata={
            "notebook_id": notebook_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "provenance": {
                "operational_mode": "direct",
                "provider_name": "Gemini Web Stream",
                "model_name": "gemini-2.5-flash",
            },
            "status": "valid",
        },
    )


# ---------------------------------------------------------------------------
# Tier 1 & 2 Tests: CRUD & Function Interface Validation
# ---------------------------------------------------------------------------

class TestEvidenceTraceStoreCRUD:
    """Verifies basic CRUD operations on evidence traces."""

    def test_save_and_load_evidence_trace_by_id(self) -> None:
        """Verify saving an EvidenceTrace and loading it back by trace_id."""
        trace = _create_sample_trace("trc_crud_001")
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_fn = getattr(chat_store, "load_evidence_trace", None)

        assert callable(save_fn), "chat_store.save_evidence_trace must be callable"
        assert callable(load_fn), "chat_store.load_evidence_trace must be callable"

        saved = save_fn(trace)
        assert saved is not None
        assert saved.trace_id == "trc_crud_001"

        loaded = load_fn("trc_crud_001")
        assert loaded is not None
        assert loaded.trace_id == "trc_crud_001"
        assert loaded.query == trace.query
        assert loaded.answer_text == trace.answer_text
        assert loaded.metadata["assistant_message_id"] == "msg_ast_100"
        assert len(loaded.nodes) == len(trace.nodes)
        assert len(loaded.edges) == len(trace.edges)

    def test_load_conversation_traces(self) -> None:
        """Verify loading all traces for a specific conversation filters accurately."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_conv_fn = getattr(chat_store, "load_conversation_traces", None)

        assert callable(save_fn) and callable(load_conv_fn)

        t1 = _create_sample_trace("trc_c1_01", conversation_id="conv_alpha", assistant_message_id="ast_1")
        t2 = _create_sample_trace("trc_c1_02", conversation_id="conv_alpha", assistant_message_id="ast_2")
        t3 = _create_sample_trace("trc_c2_01", conversation_id="conv_beta", assistant_message_id="ast_3")

        save_fn(t1)
        save_fn(t2)
        save_fn(t3)

        alpha_traces = load_conv_fn("conv_alpha")
        assert len(alpha_traces) == 2
        alpha_ids = {t.trace_id for t in alpha_traces}
        assert alpha_ids == {"trc_c1_01", "trc_c1_02"}

        beta_traces = load_conv_fn("conv_beta")
        assert len(beta_traces) == 1
        assert beta_traces[0].trace_id == "trc_c2_01"

    def test_load_message_trace(self) -> None:
        """Verify loading trace by either assistant_message_id or user_message_id."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_msg_fn = getattr(chat_store, "load_message_trace", None)

        assert callable(save_fn) and callable(load_msg_fn)

        trace = _create_sample_trace(
            "trc_msg_001",
            user_message_id="msg_usr_specific",
            assistant_message_id="msg_ast_specific",
        )
        save_fn(trace)

        # Match by assistant_message_id
        loaded_by_ast = load_msg_fn("msg_ast_specific")
        assert loaded_by_ast is not None
        assert loaded_by_ast.trace_id == "trc_msg_001"

        # Match by user_message_id
        loaded_by_usr = load_msg_fn("msg_usr_specific")
        assert loaded_by_usr is not None
        assert loaded_by_usr.trace_id == "trc_msg_001"

    def test_load_non_existent_records_returns_none_or_empty(self) -> None:
        """Verify querying non-existent trace/conversation/message IDs returns None / empty list."""
        load_trace_fn = getattr(chat_store, "load_evidence_trace", None)
        load_conv_fn = getattr(chat_store, "load_conversation_traces", None)
        load_msg_fn = getattr(chat_store, "load_message_trace", None)

        assert callable(load_trace_fn) and callable(load_conv_fn) and callable(load_msg_fn)

        assert load_trace_fn("non_existent_trace_id") is None
        assert load_conv_fn("non_existent_conv_id") == []
        assert load_msg_fn("non_existent_msg_id") is None

    def test_workspace_chat_store_class_wrapper_methods(self) -> None:
        """Verify WorkspaceChatStore class wrapper provides identical trace methods."""
        store_instance = chat_store.WorkspaceChatStore()
        trace = _create_sample_trace("trc_class_wrapper_01", assistant_message_id="ast_wrapper_01")

        assert hasattr(store_instance, "save_evidence_trace")
        assert hasattr(store_instance, "load_evidence_trace")
        assert hasattr(store_instance, "load_conversation_traces")
        assert hasattr(store_instance, "load_message_trace")

        store_instance.save_evidence_trace(trace)
        loaded = store_instance.load_evidence_trace("trc_class_wrapper_01")
        assert loaded is not None
        assert loaded.trace_id == "trc_class_wrapper_01"


# ---------------------------------------------------------------------------
# Tier 2 Tests: Idempotency & Upsert Guarantees
# ---------------------------------------------------------------------------

class TestEvidenceTraceIdempotency:
    """Verifies atomic, in-place upsert on duplicate assistant_message_id."""

    def test_idempotent_save_same_assistant_message_id_replaces_in_place(
        self, sandboxed_chat_store: Path
    ) -> None:
        """Saving multiple times with the same assistant_message_id must produce exactly 1 record."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_fn = getattr(chat_store, "load_evidence_trace", None)
        load_msg_fn = getattr(chat_store, "load_message_trace", None)
        assert callable(save_fn) and callable(load_fn) and callable(load_msg_fn)

        # Initial save
        trace_v1 = _create_sample_trace(
            "trc_idemp_01",
            assistant_message_id="msg_ast_repeat",
            query="Initial question?",
            answer_text="Initial answer [1].",
        )
        save_fn(trace_v1)

        # Repeated save with updated content and different trace_id but same assistant_message_id
        trace_v2 = _create_sample_trace(
            "trc_idemp_02",
            assistant_message_id="msg_ast_repeat",
            query="Updated question?",
            answer_text="Updated refined answer [1].",
        )
        save_fn(trace_v2)

        # Verify only 1 record exists in traces.jsonl
        traces_file = sandboxed_chat_store / "traces.jsonl"
        assert traces_file.exists()
        lines = [line.strip() for line in traces_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 1, f"Expected exactly 1 line in traces.jsonl, found {len(lines)}"

        # Verify loaded trace reflects the updated trace
        loaded = load_msg_fn("msg_ast_repeat")
        assert loaded is not None
        assert loaded.trace_id == "trc_idemp_02"
        assert loaded.answer_text == "Updated refined answer [1]."


# ---------------------------------------------------------------------------
# Tier 2 & 3 Tests: Restart Survival & Persistence Recovery
# ---------------------------------------------------------------------------

class TestEvidenceTraceRestartSurvival:
    """Verifies full recovery of traces after application restart or cache wipe."""

    def test_restart_recovery_preserves_complete_graph_and_metadata(
        self, sandboxed_chat_store: Path
    ) -> None:
        """Save traces, wipe in-memory cache, reinitialize store, and verify exact recovery."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_fn = getattr(chat_store, "load_evidence_trace", None)
        assert callable(save_fn) and callable(load_fn)

        orig_trace = _create_sample_trace(
            "trc_restart_001",
            conversation_id="conv_restart",
            assistant_message_id="ast_restart",
            query="Cách kết nối hệ thống MOM?",
            answer_text="Hệ thống MOM được cấu hình thông qua cổng kết nối [1].",
        )
        save_fn(orig_trace)

        # Simulate full restart: clear JSONL cache and instantiate new store
        clear_jsonl_cache()
        fresh_store = chat_store.WorkspaceChatStore()
        fresh_store.init_store()

        recovered = fresh_store.load_evidence_trace("trc_restart_001")
        assert recovered is not None
        assert recovered.trace_id == "trc_restart_001"
        assert recovered.query == orig_trace.query
        assert recovered.answer_text == orig_trace.answer_text
        assert recovered.metadata["provenance"]["model_name"] == "gemini-2.5-flash"
        assert len(recovered.nodes) == len(orig_trace.nodes)
        assert len(recovered.edges) == len(orig_trace.edges)

        # Check nodes detail
        node_ids = {n.id for n in recovered.nodes}
        assert "trc_restart_001_src1" in node_ids
        assert "trc_restart_001_cit1" in node_ids

    def test_corrupt_jsonl_row_resilience(self, sandboxed_chat_store: Path) -> None:
        """Store skips corrupt rows without crashing or losing neighboring valid traces."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_fn = getattr(chat_store, "load_evidence_trace", None)
        assert callable(save_fn) and callable(load_fn)

        t1 = _create_sample_trace("trc_valid_before", assistant_message_id="ast_v1")
        t2 = _create_sample_trace("trc_valid_after", assistant_message_id="ast_v2")

        save_fn(t1)

        # Manually inject a corrupted JSON line into traces.jsonl
        traces_file = sandboxed_chat_store / "traces.jsonl"
        with traces_file.open("a", encoding="utf-8") as f:
            f.write("CORRUPT_NOT_JSON_LINE_ERROR_###\n")

        save_fn(t2)

        clear_jsonl_cache()
        loaded_1 = load_fn("trc_valid_before")
        loaded_2 = load_fn("trc_valid_after")

        assert loaded_1 is not None
        assert loaded_1.trace_id == "trc_valid_before"
        assert loaded_2 is not None
        assert loaded_2.trace_id == "trc_valid_after"


# ---------------------------------------------------------------------------
# Tier 3 Tests: Cascade Deletion Lifecycle
# ---------------------------------------------------------------------------

class TestEvidenceTraceCascadeDeletion:
    """Verifies atomic cascade deletion of traces when deleting conversations or notebooks."""

    def test_delete_conversation_purges_associated_traces(self) -> None:
        """Deleting a conversation purges all associated traces while preserving other conversations."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_trace_fn = getattr(chat_store, "load_evidence_trace", None)
        load_conv_fn = getattr(chat_store, "load_conversation_traces", None)
        assert callable(save_fn) and callable(load_trace_fn) and callable(load_conv_fn)

        # Create 2 conversations
        conv_del = WorkspaceConversation(id="conv_to_delete", notebook_id="nb_1", title="Conv To Delete")
        conv_keep = WorkspaceConversation(id="conv_to_keep", notebook_id="nb_1", title="Conv To Keep")
        chat_store.save_conversation(conv_del)
        chat_store.save_conversation(conv_keep)

        # Add messages and traces to both
        t_del_1 = _create_sample_trace("trc_del_1", conversation_id="conv_to_delete", assistant_message_id="ast_d1")
        t_del_2 = _create_sample_trace("trc_del_2", conversation_id="conv_to_delete", assistant_message_id="ast_d2")
        t_keep_1 = _create_sample_trace("trc_keep_1", conversation_id="conv_to_keep", assistant_message_id="ast_k1")

        save_fn(t_del_1)
        save_fn(t_del_2)
        save_fn(t_keep_1)

        assert len(load_conv_fn("conv_to_delete")) == 2
        assert len(load_conv_fn("conv_to_keep")) == 1

        # Execute conversation deletion
        deleted = chat_store.delete_conversation("conv_to_delete")
        assert deleted is True

        # Traces for deleted conversation must be purged
        assert load_conv_fn("conv_to_delete") == []
        assert load_trace_fn("trc_del_1") is None
        assert load_trace_fn("trc_del_2") is None

        # Traces for retained conversation must remain intact
        assert len(load_conv_fn("conv_to_keep")) == 1
        assert load_trace_fn("trc_keep_1") is not None

    def test_delete_notebook_permanently_purges_all_contained_traces(self) -> None:
        """Permanently deleting a notebook purges all traces from all conversations in that notebook."""
        save_fn = getattr(chat_store, "save_evidence_trace", None)
        load_trace_fn = getattr(chat_store, "load_evidence_trace", None)
        assert callable(save_fn) and callable(load_trace_fn)

        nb_del = DocumentNotebook(id="nb_to_purge", title="Notebook To Purge")
        nb_keep = DocumentNotebook(id="nb_to_retain", title="Notebook To Retain")
        chat_store.save_notebook(nb_del)
        chat_store.save_notebook(nb_keep)

        conv_nb1 = WorkspaceConversation(id="conv_nb1", notebook_id="nb_to_purge", title="Conv in NB1")
        conv_nb2 = WorkspaceConversation(id="conv_nb2", notebook_id="nb_to_retain", title="Conv in NB2")
        chat_store.save_conversation(conv_nb1)
        chat_store.save_conversation(conv_nb2)

        t_nb1 = _create_sample_trace("trc_nb1_01", notebook_id="nb_to_purge", conversation_id="conv_nb1", assistant_message_id="ast_nb1")
        t_nb2 = _create_sample_trace("trc_nb2_01", notebook_id="nb_to_retain", conversation_id="conv_nb2", assistant_message_id="ast_nb2")
        save_fn(t_nb1)
        save_fn(t_nb2)

        # Permanently delete notebook nb_to_purge
        deleted = chat_store.delete_notebook_permanently("nb_to_purge")
        assert deleted is True

        # Verify nb1 trace is purged and nb2 trace is preserved
        assert load_trace_fn("trc_nb1_01") is None
        assert load_trace_fn("trc_nb2_01") is not None
        assert load_trace_fn("trc_nb2_01").trace_id == "trc_nb2_01"
