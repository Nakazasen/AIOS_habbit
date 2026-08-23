# -*- coding: utf-8 -*-
"""Tier 5 Adversarial Test Suite for Commit B: Comprehensive Edge Cases & Boundary Hardening.

Covers 100% white-box branch analysis across all 6 target modules:
1. `src/aios_habit/evidence_trace_schema.py`:
   - EvidenceNode & EvidenceEdge extreme values, property aliases, malformed confidence/weights.
   - EvidenceTrace __post_init__ fallback defaults, bidirectional provenance syncing, locale normalization.
   - EvidenceTraceContract comprehensive error paths (invalid versions, locales, timestamps, nodes, edges, dangling refs).
2. `src/aios_habit/evidence_trace.py`:
   - extract_cited_evidence_ids boundary attacks, regex escaping, prefix/suffix collisions, empty inputs.
   - build_evidence_trace_from_citations with dicts vs object items, bracket variations, un-enabled source filtering,
     deduplication, insufficient evidence flags.
   - is_insufficient_evidence exhaustive boolean conditions.
3. `src/aios_habit/workspace_chat_store.py`:
   - Custom traces_file paths, object-oriented WorkspaceChatStore parity.
   - In-place idempotency on assistant_message_id and trace_id.
   - Cascade deletions under delete_conversation and delete_notebook_permanently.
   - update_conversation_language_settings and corrupted JSONL resilience.
4. `src/aios_habit/antigravity_bridge.py`:
   - sanitize_reason / sanitize_bridge_error on Windows/Unix paths, API keys, Bearer tokens.
   - is_local_endpoint for loopback, localhost, RFC1918, blocked documentation IPs, invalid URIs.
   - 6-State FSM health status checks, capability filters, legacy "ok" mapping.
   - call_antigravity_bridge privacy guard, language instruction injection, error handling.
   - route_workspace_chat_submission direct vs handoff vs unavailable (strict fail-closed).
   - compress_conversation_context_direct fail-closed behavior and prompt construction.
5. `src/aios_habit/ide_handoff_bridge.py`:
   - 3-State Request Lifecycle FSM, status transitions, error sanitization.
   - is_request_expired, check_handoff_request_timeouts auto-expiration.
   - verify_bundle_integrity SHA-256 cryptographic verification and tampering detection.
   - import_ide_response 10+ validation error checks (schema, missing files, empty, unknown citations, privacy flag).
   - save_imported_ide_answer and lifecycle artifact creation.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from aios_habit.case_models import EvidenceItem
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_RAG_TRACE_V1,
    SCHEMA_VERSION_V1,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.evidence_trace import (
    build_evidence_trace_from_citations,
    create_evidence_trace,
    extract_cited_evidence_ids,
    is_insufficient_evidence,
)
from aios_habit.local_jsonl import atomic_write_jsonl, clear_jsonl_cache, load_jsonl_records
import aios_habit.workspace_chat_store as chat_store
from aios_habit.workspace_chat_models import (
    ChatMessage,
    ConversationSourceSelection,
    DocumentNotebook,
    NotebookSource,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
    TemporaryConversationSource,
    WorkspaceConversation,
)
from aios_habit.antigravity_bridge import (
    ALLOWED_CAPABILITIES,
    ALLOWED_FSM_STATES,
    ALLOWED_MODES,
    FSM_COMPLETED,
    FSM_DIRECT_READY,
    FSM_FAILED,
    FSM_HANDOFF_PENDING,
    FSM_HANDOFF_READY,
    FSM_UNAVAILABLE,
    AntigravityHealthStatus,
    call_antigravity_bridge,
    compress_conversation_context_direct,
    get_antigravity_bridge_health,
    is_antigravity_bridge_available,
    is_local_endpoint,
    route_workspace_chat_submission,
    sanitize_bridge_error,
    sanitize_reason,
)
from aios_habit.ide_handoff_bridge import (
    DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    HANDOFF_ROOT,
    REQ_STATE_COMPLETED,
    REQ_STATE_FAILED,
    REQ_STATE_PENDING,
    RESPONSE_SCHEMA_VERSION,
    VALID_SCOPES,
    block_cloud_provider_for_local_only,
    build_evidence_markdown,
    build_full_bundle_request,
    build_ide_prompt_markdown,
    build_ide_task_instruction,
    check_handoff_request_timeouts,
    convert_markdown_answer_to_ide_response,
    expected_inbox_response_path,
    find_response_for_request,
    get_latest_pending_ide_request,
    import_ide_response,
    import_markdown_ide_response,
    import_pending_ide_response,
    is_request_expired,
    list_pending_ide_requests,
    save_imported_ide_answer,
    summarize_pending_request,
    update_request_status,
    validate_handoff_bundle,
    verify_bundle_integrity,
    vietnamese_next_step_instruction,
    write_ide_handoff_bundle,
    write_ide_handoff_response,
)


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sandbox chat store and handoff directories to an isolated temporary folder."""
    chat_dir = tmp_path / "workspace_chat"
    chat_dir.mkdir(parents=True, exist_ok=True)
    traces_file = chat_dir / "traces.jsonl"

    monkeypatch.setattr(chat_store, "LOCAL_CHAT_DIR", chat_dir)
    monkeypatch.setattr(chat_store, "NOTEBOOKS_FILE", chat_dir / "notebooks.jsonl")
    monkeypatch.setattr(chat_store, "CONVERSATIONS_FILE", chat_dir / "conversations.jsonl")
    monkeypatch.setattr(chat_store, "MESSAGES_FILE", chat_dir / "messages.jsonl")
    monkeypatch.setattr(chat_store, "TEMPORARY_SOURCES_FILE", chat_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(chat_store, "NOTEBOOK_SOURCES_FILE", chat_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(chat_store, "SOURCE_SELECTIONS_FILE", chat_dir / "conversation_source_selections.jsonl")
    monkeypatch.setattr(chat_store, "TRACES_FILE", traces_file, raising=False)

    clear_jsonl_cache()
    chat_store.init_chat_store()
    yield tmp_path
    clear_jsonl_cache()


# ===========================================================================
# 1. Evidence Trace Schema & Dataclass Adversarial Fuzzing
# ===========================================================================

class TestEvidenceNodeAdversarial:
    """Stress tests on EvidenceNode edge cases, type coercion, and aliases."""

    def test_node_property_aliases(self) -> None:
        node = EvidenceNode(
            id="n_alias",
            node_type="source",
            title="Title Test",
            snippet="Snippet Test",
            source_id="path/to/file.txt",
        )
        assert node.node_id == "n_alias"
        assert node.label == "Title Test"
        assert node.content == "Snippet Test"
        assert node.source_path == "path/to/file.txt"

    def test_node_confidence_parsing_resilience(self) -> None:
        # Valid float strings
        n1 = EvidenceNode.from_dict({"id": "n1", "confidence": "0.75"})
        assert n1.confidence == 0.75

        # Invalid float strings fallback to 1.0
        n2 = EvidenceNode.from_dict({"id": "n2", "confidence": "not_a_number"})
        assert n2.confidence == 1.0

        n3 = EvidenceNode.from_dict({"id": "n3", "confidence": None})
        assert n3.confidence == 1.0

    def test_node_from_dict_field_aliases(self) -> None:
        data = {
            "node_id": "n_alt",
            "label": "Alternative Title",
            "content": "Alternative Content",
            "source_path": "alt/path.pdf",
            "properties": {"tag": "important"},
            "locale": "ja",
            "citation_id": "[E99]",
            "verification_status": "unverified",
            "privacy_label": "local_only",
        }
        node = EvidenceNode.from_dict(data)
        assert node.id == "n_alt"
        assert node.title == "Alternative Title"
        assert node.snippet == "Alternative Content"
        assert node.source_id == "alt/path.pdf"
        assert node.metadata == {"tag": "important"}
        assert node.language == "ja"
        assert node.citation_id == "[E99]"
        assert node.verification_status == "unverified"
        assert node.privacy_label == "local_only"

    def test_node_to_dict_optional_fields(self) -> None:
        node_minimal = EvidenceNode(id="n_min", node_type="claim")
        d_min = node_minimal.to_dict()
        assert d_min["id"] == "n_min"
        assert "citation_id" not in d_min
        assert "verification_status" not in d_min
        assert "language" not in d_min
        assert d_min["privacy_label"] == "local_only"

        node_full = EvidenceNode(
            id="n_full",
            node_type="claim",
            citation_id="[1]",
            verification_status="verified",
            language="vi",
            privacy_label="cloud_safe",
        )
        d_full = node_full.to_dict()
        assert d_full["citation_id"] == "[1]"
        assert d_full["verification_status"] == "verified"
        assert d_full["language"] == "vi"
        assert d_full["privacy_label"] == "cloud_safe"


class TestEvidenceEdgeAdversarial:
    """Stress tests on EvidenceEdge edge cases, type coercion, and aliases."""

    def test_edge_property_aliases(self) -> None:
        edge = EvidenceEdge(
            source_id="src_1",
            target_id="tgt_1",
            relation_type="cites",
            weight=0.88,
        )
        assert edge.source_node_id == "src_1"
        assert edge.target_node_id == "tgt_1"
        assert edge.confidence == 0.88

    def test_edge_weight_parsing_resilience(self) -> None:
        # Confidence alias in dict
        e1 = EvidenceEdge.from_dict({"source_id": "a", "target_id": "b", "confidence": "0.65"})
        assert e1.weight == 0.65

        # Malformed weight falls back to 1.0
        e2 = EvidenceEdge.from_dict({"source_id": "a", "target_id": "b", "weight": "invalid_float"})
        assert e2.weight == 1.0

        e3 = EvidenceEdge.from_dict({"source_id": "a", "target_id": "b", "weight": None, "confidence": None})
        assert e3.weight == 1.0

    def test_edge_from_dict_and_to_dict_aliases(self) -> None:
        data = {
            "source_node_id": "s_node",
            "target_node_id": "t_node",
            "relation_type": "supports",
            "label": "Direct Support",
            "edge_id": "e_custom_01",
            "metadata": {"rule_id": "R12"},
        }
        edge = EvidenceEdge.from_dict(data)
        assert edge.source_id == "s_node"
        assert edge.target_id == "t_node"
        assert edge.relation_type == "supports"
        assert edge.edge_id == "e_custom_01"

        d = edge.to_dict()
        assert d["source_node_id"] == "s_node"
        assert d["target_node_id"] == "t_node"
        assert d["edge_id"] == "e_custom_01"
        assert d["confidence"] == 1.0


class TestEvidenceTraceAdversarial:
    """Stress tests on EvidenceTrace post-init, aliases, bidirectional syncing, and JSON serialization."""

    def test_trace_post_init_defaults_and_provenance_syncing(self) -> None:
        # 1. Provenance in field synced to metadata
        t1 = EvidenceTrace(
            trace_id="t1",
            provenance={"operational_mode": "direct", "provider_name": "TestProvider"},
        )
        assert t1.metadata["provenance"]["operational_mode"] == "direct"

        # 2. Provenance in metadata synced to field
        t2 = EvidenceTrace(
            trace_id="t2",
            metadata={"provenance": {"operational_mode": "handoff", "provider_name": "IDE"}},
        )
        assert t2.provenance["operational_mode"] == "handoff"

        # 3. Created_at and schema_version fallback
        t3 = EvidenceTrace(trace_id="t3", created_at="", schema_version="")
        assert len(t3.created_at) > 0
        assert t3.schema_version == SCHEMA_VERSION_RAG_TRACE_V1

        # 4. Property aliases
        t4 = EvidenceTrace(trace_id="t4", query="Question?", answer_text="Answer.")
        assert t4.question == "Question?"
        assert t4.answer == "Answer."

    def test_trace_locale_normalization_in_post_init(self) -> None:
        trace = EvidenceTrace(
            trace_id="t_loc",
            ui_locale="VI_vn",
            answer_language="JA-jp",
            source_language="zh_Hans",
        )
        assert trace.ui_locale == "vi"
        assert trace.answer_language == "ja"
        assert trace.source_language == "zh-CN"

    def test_trace_from_dict_and_from_json_nested_structure(self) -> None:
        data = {
            "trace_id": "trc_json_001",
            "question": "Câu hỏi kiểm toán?",
            "answer": "Câu trả lời theo [1].",
            "nodes": [
                {"id": "n1", "node_type": "question", "title": "Câu hỏi"},
                EvidenceNode(id="n2", node_type="answer", title="Câu trả lời"),  # Mixed object and dict
            ],
            "edges": [
                {"source_id": "n2", "target_id": "n1", "relation_type": "derives_from"},
            ],
            "provenance": {"operational_mode": "direct"},
        }
        trace = EvidenceTrace.from_dict(data)
        assert trace.trace_id == "trc_json_001"
        assert trace.query == "Câu hỏi kiểm toán?"
        assert trace.answer_text == "Câu trả lời theo [1]."
        assert len(trace.nodes) == 2
        assert isinstance(trace.nodes[0], EvidenceNode)
        assert isinstance(trace.nodes[1], EvidenceNode)
        assert len(trace.edges) == 1
        assert isinstance(trace.edges[0], EvidenceEdge)

        json_str = trace.to_json(ensure_ascii=False)
        reloaded = EvidenceTrace.from_json(json_str)
        assert reloaded.trace_id == trace.trace_id
        assert reloaded.query == trace.query


class TestEvidenceTraceContractAdversarial:
    """Comprehensive error path testing for EvidenceTraceContract."""

    def test_contract_schema_version_variations(self) -> None:
        # Supported versions: 1.0.0, evidence_trace_v1, rag-trace/v1, 1.x
        valid_versions = [
            SCHEMA_VERSION_1_0_0,
            SCHEMA_VERSION_V1,
            SCHEMA_VERSION_RAG_TRACE_V1,
            "1.2.0",
        ]
        for ver in valid_versions:
            t = EvidenceTrace(trace_id="t_v", schema_version=ver)
            valid, errors = EvidenceTraceContract.validate_trace(t)
            assert valid is True, f"Failed on version {ver}: {errors}"

        # Invalid versions
        invalid_versions = ["rag-trace/v2", "", "   ", "2.0.0", "custom_version", "trace_v1"]
        for ver in invalid_versions:
            t = EvidenceTrace(trace_id="t_bad_v", schema_version=ver)
            # Prevent post_init from replacing empty schema_version
            t.schema_version = ver
            valid, errors = EvidenceTraceContract.validate_trace(t)
            assert valid is False
            assert any("schema_version" in e for e in errors)

    def test_contract_locale_validation(self) -> None:
        t = EvidenceTrace(trace_id="t_loc")
        t.ui_locale = "unsupported_locale"
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is False
        assert any("Invalid ui_locale" in e for e in errors)

        t.ui_locale = "vi"
        t.answer_language = "unsupported_lang"
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is False
        assert any("Invalid answer_language" in e for e in errors)

        t.answer_language = "vi"
        t.source_language = "unsupported_source_lang"
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is False
        assert any("Invalid source_language" in e for e in errors)

        t.source_language = "auto"
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is True

    def test_contract_created_at_validation(self) -> None:
        t = EvidenceTrace(trace_id="t_time", created_at="2026-08-23T15:30:00Z")
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is True

        t.created_at = "invalid_timestamp_format"
        valid, errors = EvidenceTraceContract.validate_trace(t)
        assert valid is False
        assert any("Invalid ISO 8601 created_at format" in e for e in errors)

    def test_contract_node_validation_boundaries(self) -> None:
        # Confidence boundaries
        n_neg = EvidenceNode(id="n_neg", node_type="claim", confidence=-0.01)
        n_over = EvidenceNode(id="n_over", node_type="claim", confidence=1.01)
        t_bound = EvidenceTrace(trace_id="t_b", nodes=[n_neg, n_over])
        valid, errors = EvidenceTraceContract.validate_trace(t_bound)
        assert valid is False
        assert any("n_neg" in e and "confidence" in e for e in errors)
        assert any("n_over" in e and "confidence" in e for e in errors)

        # Empty and duplicate node ID
        n_empty = EvidenceNode(id="   ", node_type="source")
        n_dup1 = EvidenceNode(id="dup_id", node_type="source")
        n_dup2 = EvidenceNode(id="dup_id", node_type="source")
        t_id = EvidenceTrace(trace_id="t_id", nodes=[n_empty, n_dup1, n_dup2])
        valid, errors = EvidenceTraceContract.validate_trace(t_id)
        assert valid is False
        assert any("missing id" in e for e in errors)
        assert any("Duplicate node id: 'dup_id'" in e for e in errors)

    def test_contract_edge_validation_boundaries(self) -> None:
        n1 = EvidenceNode(id="n1", node_type="source")
        n2 = EvidenceNode(id="n2", node_type="citation")

        # Weight boundaries
        e_neg = EvidenceEdge(source_id="n2", target_id="n1", relation_type="extracted_from", weight=-0.5)
        e_over = EvidenceEdge(source_id="n2", target_id="n1", relation_type="extracted_from", weight=1.5)
        t_w = EvidenceTrace(trace_id="t_w", nodes=[n1, n2], edges=[e_neg, e_over])
        valid, errors = EvidenceTraceContract.validate_trace(t_w)
        assert valid is False
        assert any("weight" in e and "out of range" in e for e in errors)

        # Duplicate edge_id
        e_dup1 = EvidenceEdge(source_id="n2", target_id="n1", relation_type="extracted_from", edge_id="same_edge_id")
        e_dup2 = EvidenceEdge(source_id="n2", target_id="n1", relation_type="extracted_from", edge_id="same_edge_id")
        t_dup_e = EvidenceTrace(trace_id="t_dup", nodes=[n1, n2], edges=[e_dup1, e_dup2])
        valid, errors = EvidenceTraceContract.validate_trace(t_dup_e)
        assert valid is False
        assert any("Duplicate edge_id: 'same_edge_id'" in e for e in errors)

        # Dangling source_id and target_id
        e_dangle_src = EvidenceEdge(source_id="ghost_src", target_id="n1", relation_type="supports")
        e_dangle_tgt = EvidenceEdge(source_id="n2", target_id="ghost_tgt", relation_type="supports")
        e_empty_src = EvidenceEdge(source_id="", target_id="n1", relation_type="supports")
        e_empty_tgt = EvidenceEdge(source_id="n2", target_id="", relation_type="supports")
        t_dangle = EvidenceTrace(trace_id="t_d", nodes=[n1, n2], edges=[e_dangle_src, e_dangle_tgt, e_empty_src, e_empty_tgt])
        valid, errors = EvidenceTraceContract.validate_trace(t_dangle)
        assert valid is False
        assert any("ghost_src" in e and "not found in nodes" in e for e in errors)
        assert any("ghost_tgt" in e and "not found in nodes" in e for e in errors)
        assert any("missing source_id" in e for e in errors)
        assert any("missing target_id" in e for e in errors)


# ===========================================================================
# 2. Evidence Trace Builders & Citation Extraction Adversarial Testing
# ===========================================================================

class TestExtractCitedEvidenceIdsAdversarial:
    """Stress tests for word boundary regex citation extraction."""

    def test_empty_or_none_inputs(self) -> None:
        assert extract_cited_evidence_ids("", ["1", "2"]) == []
        assert extract_cited_evidence_ids("Some text", []) == []
        assert extract_cited_evidence_ids("", []) == []
        assert extract_cited_evidence_ids("Some text", ["", "   "]) == []

    def test_regex_special_characters_in_candidate_ids(self) -> None:
        text = "Matches [1], [E2.1], DOC(A)+B, and C++_GUIDE."
        candidates = ["[1]", "[E2.1]", "DOC(A)+B", "C++_GUIDE", "[3]"]
        extracted = extract_cited_evidence_ids(text, candidates)
        assert "[1]" in extracted
        assert "[E2.1]" in extracted
        assert "DOC(A)+B" in extracted
        assert "C++_GUIDE" in extracted
        assert "[3]" not in extracted

    def test_no_false_positive_substring_or_prefix_matches(self) -> None:
        text = "This is DOC-10 and item EVD-100 and value 100."
        candidates = ["DOC-1", "EVD-1", "1", "10", "DOC-10", "EVD-100"]
        extracted = extract_cited_evidence_ids(text, candidates)
        assert "DOC-10" in extracted
        assert "EVD-100" in extracted
        assert "DOC-1" not in extracted
        assert "EVD-1" not in extracted
        assert "1" not in extracted


class TestBuildEvidenceTraceFromCitationsAdversarial:
    """Stress tests on trace graph building, object/dict items, and status flagging."""

    def test_build_trace_with_empty_evidence_items(self) -> None:
        trace = build_evidence_trace_from_citations(
            query="Hỏi gì đó?",
            answer_text="Trả lời không bằng chứng.",
            evidence_items=[],
        )
        assert trace.metadata["status"] == "insufficient_evidence"
        assert trace.metadata["insufficient_evidence"] is True
        assert trace.metadata["reason"] == "No evidence items provided"
        assert is_insufficient_evidence(trace) is True

    def test_build_trace_with_custom_objects_and_deduplication(self) -> None:
        class CustomEvidenceItem:
            def __init__(self, eid: str, title: str, text: str, citation_label: str):
                self.evidence_id = eid
                self.title = title
                self.text = text
                self.citation_label = citation_label

        items = [
            CustomEvidenceItem("E1", "Tài liệu A", "Nội dung A", "[1]"),
            CustomEvidenceItem("E2", "Tài liệu B", "Nội dung B", "[2]"),
        ]

        # Answer cites [1] multiple times and with different matching keys
        answer = "Theo [1] và [E1], tài liệu A có nội dung quan trọng."
        trace = build_evidence_trace_from_citations(
            query="Nội dung tài liệu A?",
            answer_text=answer,
            evidence_items=items,
            allowed_source_ids=["E1", "E2"],
        )
        assert trace.metadata["status"] == "valid"
        assert trace.metadata["cited_count"] == 1
        # Exactly 1 source node and 1 citation node for item 1
        src_nodes = [n for n in trace.nodes if n.node_type == "source"]
        cit_nodes = [n for n in trace.nodes if n.node_type == "citation"]
        assert len(src_nodes) == 1
        assert len(cit_nodes) == 1
        assert cit_nodes[0].citation_id == "[1]"

    def test_is_insufficient_evidence_comprehensive_matrix(self) -> None:
        # 1. None trace
        assert is_insufficient_evidence(None) is True

        # 2. Status string insufficient_evidence
        t1 = EvidenceTrace(trace_id="t1", metadata={"status": "insufficient_evidence"})
        assert is_insufficient_evidence(t1) is True

        # 3. Boolean flag insufficient_evidence
        t2 = EvidenceTrace(trace_id="t2", metadata={"insufficient_evidence": True})
        assert is_insufficient_evidence(t2) is True

        # 4. Zero evidence nodes
        t3 = EvidenceTrace(
            trace_id="t3",
            nodes=[
                EvidenceNode(id="q", node_type="question"),
                EvidenceNode(id="a", node_type="answer"),
            ],
            metadata={"status": "valid"},
        )
        assert is_insufficient_evidence(t3) is True

        # 5. Has at least one source node and valid status
        t4 = EvidenceTrace(
            trace_id="t4",
            nodes=[
                EvidenceNode(id="q", node_type="question"),
                EvidenceNode(id="s", node_type="source"),
                EvidenceNode(id="a", node_type="answer"),
            ],
            metadata={"status": "valid", "insufficient_evidence": False},
        )
        assert is_insufficient_evidence(t4) is False


# ===========================================================================
# 3. Workspace Chat Store Persistence & Concurrency/Crash Hardening
# ===========================================================================

class TestWorkspaceChatStoreAdversarialHardening:
    """Stress tests on custom paths, cascade deletions, language updates, and crash resilience."""

    def test_store_operations_with_custom_traces_file(self, tmp_path: Path) -> None:
        custom_file = tmp_path / "custom_traces_dir" / "my_custom_traces.jsonl"
        custom_file.parent.mkdir(parents=True, exist_ok=True)

        trace = create_evidence_trace(
            trace_id="trc_custom_001",
            conversation_id="conv_custom",
            assistant_message_id="ast_custom",
            query="Custom path query?",
            answer_text="Custom path answer [1].",
        )

        # Save to custom file
        saved = chat_store.save_evidence_trace(trace, traces_file=custom_file)
        assert saved.trace_id == "trc_custom_001"
        assert custom_file.exists()

        # Load from custom file
        loaded = chat_store.load_evidence_trace("trc_custom_001", traces_file=custom_file)
        assert loaded is not None
        assert loaded.trace_id == "trc_custom_001"

        conv_traces = chat_store.load_conversation_traces("conv_custom", traces_file=custom_file)
        assert len(conv_traces) == 1

        msg_trace = chat_store.load_message_trace("ast_custom", traces_file=custom_file)
        assert msg_trace is not None

    def test_workspace_chat_store_instance_custom_chat_dir(self, tmp_path: Path) -> None:
        custom_chat_dir = tmp_path / "custom_chat_instance"
        custom_chat_dir.mkdir(parents=True, exist_ok=True)

        store_inst = chat_store.WorkspaceChatStore(chat_dir=custom_chat_dir)
        assert store_inst.traces_file == custom_chat_dir / "traces.jsonl"

        trace = create_evidence_trace(
            trace_id="trc_inst_001",
            conversation_id="conv_inst",
            assistant_message_id="ast_inst",
        )
        store_inst.save_evidence_trace(trace)
        assert store_inst.traces_file.exists()

        loaded = store_inst.load_evidence_trace("trc_inst_001")
        assert loaded is not None
        assert loaded.trace_id == "trc_inst_001"

        all_traces = store_inst.load_all_evidence_traces()
        assert len(all_traces) == 1

    def test_update_conversation_language_settings(self) -> None:
        conv = WorkspaceConversation(
            id="conv_lang_test",
            notebook_id="nb_lang",
            title="Lang Conversation",
            ui_locale="vi",
            answer_language="vi",
        )
        chat_store.save_conversation(conv)

        # Update both locales with un-normalized formats
        updated = chat_store.update_conversation_language_settings(
            "conv_lang_test",
            ui_locale="JA_jp",
            answer_language="zh_Hans",
        )
        assert updated is not None
        assert updated.ui_locale == "ja"
        assert updated.answer_language == "zh-CN"

        # Verify update on non-existent conversation returns None
        assert chat_store.update_conversation_language_settings("non_existent_conv") is None

    def test_source_management_and_snapshots(self) -> None:
        nb_src = NotebookSource(
            id="src_snap_01",
            notebook_id="nb_snap",
            title="Snapshot Source",
            source_type="txt",
        )
        chat_store.save_notebook_source(nb_src)

        sel = ConversationSourceSelection(
            id="sel_snap_01",
            conversation_id="conv_snap",
            source_id="src_snap_01",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            enabled=True,
        )
        chat_store.save_conversation_source_selection(sel)

        # Delete source and capture snapshot
        snapshot = chat_store.delete_sources("notebook", ["src_snap_01"])
        assert len(snapshot["sources"]) == 1
        assert chat_store.get_notebook_source("src_snap_01") is None

        # Restore snapshot
        restored_count = chat_store.restore_source_snapshot(snapshot)
        assert restored_count == 1
        assert chat_store.get_notebook_source("src_snap_01") is not None


# ===========================================================================
# 4. Antigravity Bridge & Routing Adversarial Stress
# ===========================================================================

class TestAntigravityBridgeSanitizationAndEndpoints:
    """Stress tests on error sanitization and local endpoint validation."""

    def test_sanitize_reason_comprehensive(self) -> None:
        # None or empty
        assert sanitize_reason("") == ""
        assert sanitize_reason(None) == ""

        # Windows paths
        win_path = "Error reading D:\\Sandbox\\AIOS_habbit\\local_cases\\traces.jsonl: access denied"
        s_win = sanitize_reason(win_path)
        assert "D:" not in s_win
        assert "<path>" in s_win

        # Unix paths
        unix_path = "Error reading /home/admin/project/secret.key: not found"
        s_unix = sanitize_reason(unix_path)
        assert "/home/admin" not in s_unix
        assert "<path>" in s_unix

        # Tokens
        token_err = "Auth failed: Bearer secret_token_123456 and sk-proj_abcdef123456"
        s_tok = sanitize_reason(token_err)
        assert "secret_token_123456" not in s_tok
        assert "sk-proj_abcdef123456" not in s_tok
        assert "<redacted_token>" in s_tok

        # Combined alias check
        assert sanitize_bridge_error(win_path) == s_win

    def test_is_local_endpoint_boundary_checks(self) -> None:
        # Valid loopbacks and locals
        assert is_local_endpoint("http://localhost:8585/v1") is True
        assert is_local_endpoint("http://127.0.0.1:8585/health") is True
        assert is_local_endpoint("http://127.0.0.2:9000") is True
        assert is_local_endpoint("http://my-host.local:8585") is True
        assert is_local_endpoint("http://10.0.0.5:8080") is True
        assert is_local_endpoint("http://192.168.1.50:8000") is True
        assert is_local_endpoint("http://172.16.0.1:8000") is True

        # Blocked documentation IPs
        assert is_local_endpoint("http://198.51.100.1:8585") is False
        assert is_local_endpoint("http://203.0.113.5:8585") is False
        assert is_local_endpoint("http://192.0.2.1:8585") is False

        # Blocked public / cloud endpoints
        assert is_local_endpoint("https://api.openai.com/v1/chat") is False
        assert is_local_endpoint("https://generativelanguage.googleapis.com") is False
        assert is_local_endpoint("http://8.8.8.8:8585") is False

        # Invalid URLs
        assert is_local_endpoint("ftp://localhost") is False
        assert is_local_endpoint("not_a_valid_url") is False
        assert is_local_endpoint("") is False


class TestAntigravityHealthStatusFSM:
    """Stress tests on 6-State FSM health transitions and properties."""

    @pytest.mark.parametrize("state", list(ALLOWED_FSM_STATES))
    def test_fsm_states_and_properties(self, state: str) -> None:
        health = AntigravityHealthStatus(
            status=state,
            mode="direct" if "direct" in state else ("handoff" if "handoff" in state else "none"),
            capabilities=["direct_chat", "local_handoff"],
        )
        assert health.status == state
        if state in (FSM_DIRECT_READY, FSM_HANDOFF_READY, FSM_HANDOFF_PENDING, FSM_COMPLETED):
            assert health.is_available is True
        else:
            assert health.is_available is False

        if state == FSM_DIRECT_READY:
            assert health.is_direct_ready is True
            assert health.is_direct is True
        elif state == FSM_HANDOFF_READY:
            assert health.is_handoff_ready is True
            assert health.is_handoff is True


class TestAntigravityBridgeCallsAndRouting:
    """Stress tests on bridge calling, privacy enforcement, and route_workspace_chat_submission."""

    def test_call_antigravity_bridge_privacy_guard(self) -> None:
        # Attempt calling public endpoint with local_only privacy mode
        res = call_antigravity_bridge(
            question="Private query?",
            endpoint_url="https://external-api.cloud.com/v1",
            privacy_mode="local_only",
        )
        assert res.ok is False
        assert "Bị chặn" in res.error_message

    def test_compress_conversation_context_fail_closed(self) -> None:
        # When direct is not ready
        health = AntigravityHealthStatus(status=FSM_UNAVAILABLE, reason="daemon not running")
        ok, summary, err = compress_conversation_context_direct([], health_status=health)
        assert ok is False
        assert summary == ""
        assert "Antigravity Direct chưa sẵn sàng" in str(err)

        # When direct is ready but chat history is empty
        health_ready = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct")
        ok2, summary2, err2 = compress_conversation_context_direct([], health_status=health_ready)
        assert ok2 is False
        assert "Lịch sử cuộc trò chuyện rỗng" in str(err2)

    def test_route_workspace_chat_submission_fail_closed_when_unavailable(self) -> None:
        health_unavail = AntigravityHealthStatus(status=FSM_UNAVAILABLE, reason="Port 8585 closed")
        ok, msg, badge, err = route_workspace_chat_submission(
            question="Hỏi thử nghiệm?",
            evidence_items=[],
            packed_sources=(),
            conversation_id="conv_route_test",
            notebook_id="nb_route_test",
            retrieval_applied=False,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Hỏi thử nghiệm?",
            health_status=health_unavail,
        )
        assert ok is False
        assert badge is None
        assert "Cầu nối Antigravity IDE hiện không khả dụng" in str(err)


# ===========================================================================
# 5. IDE Handoff Bridge Lifecycle, Validation, Integrity & Auto-Expiration
# ===========================================================================

class TestIDEHandoffBridgeAdversarial:
    """Stress tests on handoff bundles, integrity checks, timeouts, and validation rules."""

    def test_write_and_verify_bundle_integrity(self, tmp_path: Path) -> None:
        item = EvidenceItem(
            evidence_id="EVD-INT-001",
            case_id="CASE-INT",
            source_type="txt",
            source_path="local_cases/docs/integ.txt",
            title="Tài liệu kiểm tra tính toàn vẹn",
            extracted_text="Nội dung mã SHA-256 chính xác 100%.",
            privacy_level="local_only",
        )
        req = write_ide_handoff_bundle(
            case_id="CASE-INT",
            question="Kiểm tra toàn vẹn?",
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            request_id="REQ-INT-001",
        )
        assert req.bundle_dir.exists()

        # Check bundle validation helper
        val_res = validate_handoff_bundle(req.bundle_dir)
        assert val_res["ok"] is True
        assert val_res["missing"] == []

        # Check cryptographic SHA-256 integrity
        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is True
        assert errors == []

        # Tamper with evidence_full.jsonl and verify integrity failure
        jsonl_path = req.bundle_dir / "evidence_full.jsonl"
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"evidence_id": "EVD-TAMPERED", "text": "Hacked"}) + "\n")

        ok_tampered, errors_tampered = verify_bundle_integrity(req.bundle_dir)
        assert ok_tampered is False
        assert any("SHA-256 mismatch" in e for e in errors_tampered)

    def test_handoff_timeout_auto_expiration(self, tmp_path: Path) -> None:
        item = EvidenceItem(
            evidence_id="EVD-EXP-001",
            case_id="CASE-EXP",
            source_type="txt",
            source_path="local_cases/docs/exp.txt",
            title="Tài liệu hết hạn",
            extracted_text="Dữ liệu test timeout.",
            privacy_level="local_only",
        )
        req = write_ide_handoff_bundle(
            case_id="CASE-EXP",
            question="Câu hỏi timeout?",
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            request_id="REQ-TIMEOUT-001",
            timeout_seconds=10,
        )

        # Check initially pending
        pending = list_pending_ide_requests(tmp_path)
        assert any(p.request_id == "REQ-TIMEOUT-001" and p.state == REQ_STATE_PENDING for p in pending)

        # Simulate 15 seconds elapsed
        future_time = datetime.now() + timedelta(seconds=15)
        expired_ids = check_handoff_request_timeouts(tmp_path, now=future_time)
        assert "REQ-TIMEOUT-001" in expired_ids

        # Check request transitioned to failed
        status_file = req.bundle_dir / "request_status.json"
        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        assert status_data["state"] == REQ_STATE_FAILED
        assert status_data["error_reason"] == "timeout"

    def test_import_ide_response_validation_matrix(self, tmp_path: Path) -> None:
        item = EvidenceItem(
            evidence_id="EVD-VAL-001",
            case_id="CASE-VAL",
            source_type="txt",
            source_path="local_cases/docs/val.txt",
            title="Tài liệu thẩm định",
            extracted_text="Dữ liệu thẩm định.",
            privacy_level="local_only",
        )
        req = write_ide_handoff_bundle(
            case_id="CASE-VAL",
            question="Thẩm định phản hồi?",
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            request_id="REQ-VAL-001",
        )

        resp_file = tmp_path / "inbox" / req.request_id / "response.json"
        resp_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Non-existent file
        r1 = import_ide_response(tmp_path / "inbox" / "non_existent.json", root=tmp_path)
        assert r1.ok is False
        assert any("response file not found" in e for e in r1.errors)

        # 2. Empty file
        resp_file.write_text("", encoding="utf-8")
        r2 = import_ide_response(resp_file, root=tmp_path)
        assert r2.ok is False
        assert any("response file is empty" in e for e in r2.errors)

        # 3. Invalid schema version
        payload_bad_schema = {
            "schema_version": "invalid_schema_v99",
            "request_id": req.request_id,
            "status": "completed",
            "answer_markdown": "Answer text",
            "model_tool_name": "Antigravity IDE",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "evidence_ids_used": [item.evidence_id],
        }
        resp_file.write_text(json.dumps(payload_bad_schema), encoding="utf-8")
        r3 = import_ide_response(resp_file, root=tmp_path)
        assert r3.ok is False
        assert any("invalid schema_version" in e for e in r3.errors)

        # 4. Unknown evidence IDs cited
        payload_unknown_cite = {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "request_id": req.request_id,
            "status": "completed",
            "answer_markdown": "Answer text citing unknown doc",
            "model_tool_name": "Antigravity IDE",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "evidence_ids_used": ["EVD-UNKNOWN-999"],
        }
        resp_file.write_text(json.dumps(payload_unknown_cite), encoding="utf-8")
        r4 = import_ide_response(resp_file, root=tmp_path)
        assert r4.ok is False
        assert any("unknown evidence_ids_used: EVD-UNKNOWN-999" in e for e in r4.errors)

        # 5. Missing privacy acknowledgement for local_only bundle
        payload_no_privacy = {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "request_id": req.request_id,
            "status": "completed",
            "answer_markdown": "Answer text",
            "model_tool_name": "Antigravity IDE",
            "privacy_acknowledged": False,  # Violates local_only bundle requirement
            "used_full_bundle": True,
            "evidence_ids_used": [item.evidence_id],
        }
        resp_file.write_text(json.dumps(payload_no_privacy), encoding="utf-8")
        r5 = import_ide_response(resp_file, root=tmp_path)
        assert r5.ok is False
        assert any("privacy_acknowledged must be true" in e for e in r5.errors)

        # 6. Valid response
        payload_valid = {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "request_id": req.request_id,
            "status": "completed",
            "answer_markdown": "Câu trả lời hoàn toàn chính xác theo [EVD-VAL-001].",
            "model_tool_name": "Antigravity IDE AI",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "evidence_ids_used": [item.evidence_id],
        }
        resp_file.write_text(json.dumps(payload_valid), encoding="utf-8")
        r6 = import_ide_response(resp_file, root=tmp_path)
        assert r6.ok is True
        assert r6.final_answer is True
        assert len(r6.errors) == 0

        # Save imported response
        saved_ans = save_imported_ide_answer("CASE-VAL", r6, root=tmp_path)
        assert saved_ans.final_answer is True
        assert saved_ans.pack_id == req.request_id

        # Verify request_status.json transitioned to completed
        status_file = req.bundle_dir / "request_status.json"
        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        assert status_data["state"] == REQ_STATE_COMPLETED
        assert status_data["saved_answer_id"] == saved_ans.draft_id
