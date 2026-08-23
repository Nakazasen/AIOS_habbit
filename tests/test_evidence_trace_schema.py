# -*- coding: utf-8 -*-
"""Automated Unit Tests for Evidence Trace Contract & Schema (Milestone 1).

Validates:
- EvidenceNode, EvidenceEdge, and EvidenceTrace dataclass instantiation & field aliases.
- Dictionary and JSON serialization & deserialization with strict UTF-8 anti-mojibake guarantee.
- EvidenceTraceContract validation rules (schema versions, locales, dangling edge nodes, confidence boundaries).
- Trace factory & builder helpers: create_evidence_trace, build_evidence_trace_from_citations, extract_cited_evidence_ids.
- ChatMessage trace_id binding and backward compatibility.
- Insufficient evidence detection and strict source filtering.
- Re-exports in aios_habit.evidence_trace module.
"""
from __future__ import annotations

import json
import pytest

from aios_habit.evidence_trace import (
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
    build_evidence_trace_from_citations,
    create_evidence_trace,
    extract_cited_evidence_ids,
    is_insufficient_evidence,
)
from aios_habit.workspace_chat_models import ChatMessage


def test_evidence_node_instantiation_and_aliases() -> None:
    """Verify EvidenceNode fields, convenience aliases, and dictionary round-trip."""
    node = EvidenceNode(
        id="node_src_001",
        node_type="source",
        title="Tài liệu quy trình vận hành.pdf",
        snippet="Đoạn trích dẫn nguyên văn từ hệ thống.",
        source_id="docs/op_manual.pdf",
        confidence=0.98,
        citation_id="[E1]",
        verification_status="verified",
        privacy_label="cloud_safe",
        metadata={"author": "Team Lead", "section": 4},
    )

    # Test property aliases
    assert node.node_id == "node_src_001"
    assert node.label == "Tài liệu quy trình vận hành.pdf"
    assert node.content == "Đoạn trích dẫn nguyên văn từ hệ thống."
    assert node.source_path == "docs/op_manual.pdf"

    # Serialization
    node_dict = node.to_dict()
    assert node_dict["id"] == "node_src_001"
    assert node_dict["node_id"] == "node_src_001"
    assert node_dict["title"] == "Tài liệu quy trình vận hành.pdf"
    assert node_dict["snippet"] == "Đoạn trích dẫn nguyên văn từ hệ thống."
    assert node_dict["citation_id"] == "[E1]"

    # Deserialization from dictionary
    reconstructed = EvidenceNode.from_dict(node_dict)
    assert reconstructed.id == node.id
    assert reconstructed.title == node.title
    assert reconstructed.snippet == node.snippet
    assert reconstructed.source_id == node.source_id
    assert reconstructed.confidence == node.confidence
    assert reconstructed.citation_id == "[E1]"
    assert reconstructed.metadata == {"author": "Team Lead", "section": 4}


def test_evidence_edge_instantiation_and_aliases() -> None:
    """Verify EvidenceEdge fields, convenience aliases, and dictionary round-trip."""
    edge = EvidenceEdge(
        source_id="node_claim_001",
        target_id="node_src_001",
        relation_type="cites",
        label="Dẫn nguồn trực tiếp",
        weight=0.95,
        metadata={"rule": "strict_grounding"},
        edge_id="edge_001",
    )

    # Test property aliases
    assert edge.source_node_id == "node_claim_001"
    assert edge.target_node_id == "node_src_001"
    assert edge.confidence == 0.95

    # Serialization
    edge_dict = edge.to_dict()
    assert edge_dict["source_id"] == "node_claim_001"
    assert edge_dict["target_id"] == "node_src_001"
    assert edge_dict["relation_type"] == "cites"
    assert edge_dict["weight"] == 0.95
    assert edge_dict["edge_id"] == "edge_001"

    # Deserialization from dictionary
    reconstructed = EvidenceEdge.from_dict(edge_dict)
    assert reconstructed.source_id == edge.source_id
    assert reconstructed.target_id == edge.target_id
    assert reconstructed.relation_type == edge.relation_type
    assert reconstructed.weight == edge.weight
    assert reconstructed.edge_id == "edge_001"


def test_evidence_trace_defaults_and_normalization() -> None:
    """Verify EvidenceTrace default initialization and locale normalization."""
    trace = EvidenceTrace(
        trace_id="tr_001",
        query="Quy trình xử lý sự cố như thế nào?",
        answer_text="Theo tài liệu [E1], cần thực hiện 3 bước.",
        ui_locale="ja_JP",  # Should normalize to 'ja'
        answer_language="zh-Hans",  # Should normalize to 'zh-CN'
    )

    assert trace.schema_version in SUPPORTED_SCHEMA_VERSIONS
    assert trace.trace_id == "tr_001"
    assert trace.ui_locale == "ja"
    assert trace.answer_language == "zh-CN"
    assert trace.source_language == "auto"
    assert trace.answer == "Theo tài liệu [E1], cần thực hiện 3 bước."
    assert len(trace.created_at) > 0


def test_evidence_trace_rag_trace_v1_full_fields() -> None:
    """Verify EvidenceTrace rag-trace/v1 schema with all mandatory fields and provenance."""
    node1 = EvidenceNode(id="n_q", node_type="question", title="Câu hỏi")
    node2 = EvidenceNode(id="n_ans", node_type="answer", title="Câu trả lời")
    edge = EvidenceEdge(source_id="n_ans", target_id="n_q", relation_type="derives_from")

    trace = EvidenceTrace(
        trace_id="trc_test_full_001",
        schema_version=SCHEMA_VERSION_RAG_TRACE_V1,
        notebook_id="NB-2026-001",
        conversation_id="CONV-2026-001",
        user_message_id="MSG-USER-001",
        assistant_message_id="MSG-ASSISTANT-001",
        query="Kiểm toán doanh thu quý 3?",
        answer_text="Doanh thu quý 3 đạt 150 tỷ [1].",
        ui_locale="vi",
        answer_language="vi",
        source_language="auto",
        provenance={
            "operational_mode": "direct",
            "provider_name": "Gemini Web Stream",
            "model_name": "gemini-2.5-flash",
        },
        nodes=[node1, node2],
        edges=[edge],
        metadata={"status": "valid", "insufficient_evidence": False},
    )

    assert trace.schema_version == "rag-trace/v1"
    assert trace.notebook_id == "NB-2026-001"
    assert trace.conversation_id == "CONV-2026-001"
    assert trace.user_message_id == "MSG-USER-001"
    assert trace.assistant_message_id == "MSG-ASSISTANT-001"
    assert trace.provenance["operational_mode"] == "direct"

    # Validate dictionary round-trip
    d = trace.to_dict()
    assert d["notebook_id"] == "NB-2026-001"
    assert d["assistant_message_id"] == "MSG-ASSISTANT-001"
    assert d["provenance"]["model_name"] == "gemini-2.5-flash"

    reconstructed = EvidenceTrace.from_dict(d)
    assert reconstructed.trace_id == trace.trace_id
    assert reconstructed.notebook_id == trace.notebook_id
    assert reconstructed.conversation_id == trace.conversation_id
    assert reconstructed.user_message_id == trace.user_message_id
    assert reconstructed.assistant_message_id == trace.assistant_message_id
    assert reconstructed.provenance == trace.provenance
    assert len(reconstructed.nodes) == 2
    assert len(reconstructed.edges) == 1

    valid, errors = EvidenceTraceContract.validate(reconstructed)
    assert valid is True
    assert errors == []


def test_evidence_trace_roundtrip_dict_and_json_utf8() -> None:
    """Verify complete EvidenceTrace round-trip through dict and JSON with multi-language characters."""
    node1 = EvidenceNode(
        id="n_claim",
        node_type="claim",
        title="Báo cáo tiến độ quý 3 (四半期進捗報告 / 季度进度报告)",
        snippet="Nội dung kiểm toán hoàn thành 100%. (監査完了 / 审计完成)",
        confidence=1.0,
    )
    node2 = EvidenceNode(
        id="n_source",
        node_type="source",
        title="audit_report_2026.pdf",
        snippet="Raw snippet: ERR_CODE_00, [1] Section 2.1",
        source_id="audit_report_2026.pdf",
        confidence=0.99,
    )
    edge = EvidenceEdge(
        source_id="n_claim",
        target_id="n_source",
        relation_type="cites",
        label="Dẫn nguồn bằng chứng",
        weight=0.99,
    )

    trace = EvidenceTrace(
        trace_id="trace_test_01",
        schema_version="1.0.0",
        query="Kiểm toán viên đã kết luận gì?",
        answer_text="Kiểm toán viên xác nhận 100% hoàn thành theo [1].",
        ui_locale="vi",
        answer_language="vi",
        nodes=[node1, node2],
        edges=[edge],
        metadata={"eval_run": "test_run_01"},
    )

    # To JSON
    json_str = trace.to_json(indent=2)
    assert "四半期進捗報告" in json_str
    assert "季度进度报告" in json_str
    assert "audit_report_2026.pdf" in json_str

    # From JSON
    reconstructed = EvidenceTrace.from_json(json_str)
    assert reconstructed.trace_id == trace.trace_id
    assert len(reconstructed.nodes) == 2
    assert len(reconstructed.edges) == 1
    assert reconstructed.nodes[0].title == node1.title
    assert reconstructed.nodes[1].snippet == node2.snippet
    assert reconstructed.edges[0].relation_type == edge.relation_type


def test_contract_validation_success() -> None:
    """Verify EvidenceTraceContract passes on valid trace."""
    node1 = EvidenceNode(id="n1", node_type="question", title="Question 1")
    node2 = EvidenceNode(id="n2", node_type="source", title="Source doc.pdf")
    edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type="references")

    trace = EvidenceTrace(
        trace_id="tr_valid",
        schema_version="1.0.0",
        ui_locale="vi",
        answer_language="ja",
        nodes=[node1, node2],
        edges=[edge],
    )

    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is True
    assert errors == []


def test_contract_validation_detects_errors() -> None:
    """Verify EvidenceTraceContract catches missing IDs, dangling edges, and invalid ranges."""
    node1 = EvidenceNode(id="n1", node_type="claim", confidence=1.5)  # Invalid confidence
    node2 = EvidenceNode(id="n1", node_type="source")  # Duplicate node id
    node3 = EvidenceNode(id="", node_type="evidence")  # Missing id

    # Dangling edge pointing to non-existent node 'n_missing'
    dangling_edge = EvidenceEdge(source_id="n1", target_id="n_missing", relation_type="", weight=-0.5)

    trace = EvidenceTrace(
        trace_id="tr_invalid",
        schema_version="invalid_v99",
        nodes=[node1, node2, node3],
        edges=[dangling_edge],
    )

    # Force invalid locales to test validator rejection
    trace.ui_locale = "invalid_locale"
    trace.answer_language = "invalid_lang"

    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is False
    assert any("Invalid schema_version" in e for e in errors)
    assert any("Invalid ui_locale" in e for e in errors)
    assert any("Invalid answer_language" in e for e in errors)
    assert any("Duplicate node id" in e for e in errors)
    assert any("missing id" in e for e in errors)
    assert any("confidence" in e for e in errors)
    assert any("not found in nodes" in e for e in errors)
    assert any("missing relation_type" in e for e in errors)
    assert any("weight" in e for e in errors)


def test_contract_timestamp_and_v1_version() -> None:
    """Verify EvidenceTraceContract validates ISO 8601 timestamps and supports SCHEMA_VERSION_V1."""
    node = EvidenceNode(id="n_v1", node_type="claim", title="Claim V1")
    trace_v1 = EvidenceTrace(
        trace_id="tr_v1",
        schema_version=SCHEMA_VERSION_V1,
        ui_locale="vi",
        answer_language="vi",
        created_at="2026-08-23T11:00:00+00:00",
        nodes=[node],
        edges=[],
    )
    valid_v1, errors_v1 = EvidenceTraceContract.validate(trace_v1)
    assert valid_v1 is True
    assert errors_v1 == []

    # Invalid timestamp format
    trace_bad_time = EvidenceTrace(
        trace_id="tr_bad_time",
        schema_version="1.0.0",
        created_at="not_a_timestamp_at_all",
        nodes=[node],
        edges=[],
    )
    valid_bad, errors_bad = EvidenceTraceContract.validate(trace_bad_time)
    assert valid_bad is False
    assert any("Invalid ISO 8601 created_at format" in e for e in errors_bad)


def test_contract_validation_rejects_invalid_node_type() -> None:
    """Verify EvidenceTraceContract rejects nodes with disallowed or whitespace node_type."""
    node_bad = EvidenceNode(id="n_bad", node_type="invalid_node_type", title="Bad Node")
    trace = EvidenceTrace(
        trace_id="tr_bad_node",
        schema_version="1.0.0",
        nodes=[node_bad],
        edges=[],
    )
    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is False
    assert any("invalid node_type: 'invalid_node_type'" in e for e in errors)
    assert any("allowed:" in e for e in errors)

    node_ws = EvidenceNode(id="n_ws", node_type="   ", title="Whitespace Node")
    trace_ws = EvidenceTrace(
        trace_id="tr_ws_node",
        schema_version="1.0.0",
        nodes=[node_ws],
        edges=[],
    )
    valid_ws, errors_ws = EvidenceTraceContract.validate(trace_ws)
    assert valid_ws is False
    assert any("missing node_type" in e for e in errors_ws)


def test_contract_validation_rejects_invalid_relation_type() -> None:
    """Verify EvidenceTraceContract rejects edges with disallowed or whitespace relation_type."""
    node1 = EvidenceNode(id="n1", node_type="claim", title="Claim 1")
    node2 = EvidenceNode(id="n2", node_type="source", title="Source 1")

    edge_bad = EvidenceEdge(source_id="n1", target_id="n2", relation_type="unknown_edge_type", edge_id="e_bad")
    trace = EvidenceTrace(
        trace_id="tr_bad_edge",
        schema_version="1.0.0",
        nodes=[node1, node2],
        edges=[edge_bad],
    )
    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is False
    assert any("invalid relation_type: 'unknown_edge_type'" in e for e in errors)
    assert any("allowed:" in e for e in errors)

    edge_ws = EvidenceEdge(source_id="n1", target_id="n2", relation_type="  ", edge_id="e_ws")
    trace_ws = EvidenceTrace(
        trace_id="tr_ws_edge",
        schema_version="1.0.0",
        nodes=[node1, node2],
        edges=[edge_ws],
    )
    valid_ws, errors_ws = EvidenceTraceContract.validate(trace_ws)
    assert valid_ws is False
    assert any("missing relation_type" in e for e in errors_ws)


@pytest.mark.parametrize("allowed_node_type", sorted(ALLOWED_NODE_TYPES))
def test_contract_validation_accepts_all_allowed_node_types(allowed_node_type: str) -> None:
    """Verify EvidenceTraceContract accepts each valid node type in ALLOWED_NODE_TYPES (12 types)."""
    node = EvidenceNode(id="n_test", node_type=allowed_node_type, title=f"Testing {allowed_node_type}")
    trace = EvidenceTrace(
        trace_id=f"tr_{allowed_node_type}",
        schema_version="1.0.0",
        nodes=[node],
        edges=[],
    )
    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is True, f"Failed on valid node_type '{allowed_node_type}': {errors}"
    assert errors == []


@pytest.mark.parametrize("allowed_edge_type", sorted(ALLOWED_EDGE_TYPES))
def test_contract_validation_accepts_all_allowed_edge_types(allowed_edge_type: str) -> None:
    """Verify EvidenceTraceContract accepts each valid edge type in ALLOWED_EDGE_TYPES (12 types)."""
    node1 = EvidenceNode(id="n1", node_type="claim", title="Claim Node")
    node2 = EvidenceNode(id="n2", node_type="evidence", title="Evidence Node")
    edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type=allowed_edge_type, edge_id="e1")
    trace = EvidenceTrace(
        trace_id=f"tr_{allowed_edge_type}",
        schema_version="1.0.0",
        nodes=[node1, node2],
        edges=[edge],
    )
    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is True, f"Failed on valid relation_type '{allowed_edge_type}': {errors}"
    assert errors == []


def test_allowed_constants_completeness_and_isolation() -> None:
    """Verify count and exact values of ALLOWED_NODE_TYPES (12) and ALLOWED_EDGE_TYPES (12)."""
    expected_node_types = frozenset({
        "source", "chunk", "evidence", "claim", "citation", "answer",
        "question", "inference", "limitation", "action", "verification", "summary",
    })
    expected_edge_types = frozenset({
        "cites", "supports", "contradicts", "refutes", "derived_from",
        "derives_from", "depends_on", "verifies", "limits", "recommends",
        "references", "extracted_from",
    })

    assert len(ALLOWED_NODE_TYPES) == 12
    assert ALLOWED_NODE_TYPES == expected_node_types
    assert EvidenceTraceContract.ALLOWED_NODE_TYPES == expected_node_types

    assert len(ALLOWED_EDGE_TYPES) == 12
    assert ALLOWED_EDGE_TYPES == expected_edge_types
    assert EvidenceTraceContract.ALLOWED_EDGE_TYPES == expected_edge_types


def test_create_evidence_trace_helper() -> None:
    """Verify create_evidence_trace factory correctly sets defaults and flags."""
    trace = create_evidence_trace(
        notebook_id="NB-101",
        conversation_id="CONV-101",
        query="Làm sao để cấu hình?",
        answer_text="Xem tài liệu hướng dẫn.",
        ui_locale="vi",
        answer_language="vi",
        status="valid",
    )
    assert trace.trace_id.startswith("trc_")
    assert trace.schema_version == SCHEMA_VERSION_RAG_TRACE_V1
    assert trace.notebook_id == "NB-101"
    assert trace.metadata["status"] == "valid"
    assert is_insufficient_evidence(trace) is True  # Zero evidence nodes yet


def test_build_evidence_trace_from_citations_valid() -> None:
    """Verify build_evidence_trace_from_citations constructs a verified trace when citations match."""
    evidence_items = [
        {
            "id": "doc_01",
            "source_id": "doc_01",
            "title": "Báo cáo kiểm toán quý 3",
            "snippet": "Doanh thu quý 3 tăng 25%.",
            "source_path": "reports/q3_audit.pdf",
            "citation_label": "[1]",
        },
        {
            "id": "doc_02",
            "source_id": "doc_02",
            "title": "Quy trình vận hành",
            "snippet": "Bước 1 là kiểm tra hệ thống.",
            "source_path": "docs/sop.pdf",
            "citation_label": "[2]",
        }
    ]

    # Answer citing [1]
    trace = build_evidence_trace_from_citations(
        query="Doanh thu quý 3 tăng bao nhiêu?",
        answer_text="Theo báo cáo [1], doanh thu quý 3 đã tăng 25%.",
        evidence_items=evidence_items,
        allowed_source_ids=["doc_01", "doc_02"],
        notebook_id="NB-202",
        conversation_id="CONV-202",
        user_message_id="MSG-U-202",
        assistant_message_id="MSG-A-202",
        ui_locale="vi",
        answer_language="vi",
        provenance={"operational_mode": "direct", "provider_name": "Gemini Web Stream"},
    )

    assert trace.metadata["status"] == "valid"
    assert trace.metadata["insufficient_evidence"] is False
    assert trace.metadata["cited_count"] == 1
    assert not is_insufficient_evidence(trace)

    # Validate graph structure: question, answer, source [1], citation [1]
    node_types = {n.node_type for n in trace.nodes}
    assert "question" in node_types
    assert "answer" in node_types
    assert "source" in node_types
    assert "citation" in node_types

    edge_relations = {e.relation_type for e in trace.edges}
    assert "derives_from" in edge_relations
    assert "cites" in edge_relations
    assert "extracted_from" in edge_relations

    # Trace Contract Validation
    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is True, f"Validation errors: {errors}"


def test_build_evidence_trace_missing_citations_insufficient_evidence() -> None:
    """Verify that answers without valid citations are marked as insufficient_evidence."""
    evidence_items = [
        {
            "id": "doc_01",
            "title": "Báo cáo kiểm toán",
            "snippet": "Dữ liệu kiểm toán.",
            "citation_label": "[1]",
        }
    ]

    # Answer without citations
    trace = build_evidence_trace_from_citations(
        query="Có thông tin gì mới không?",
        answer_text="Tôi không tìm thấy thông tin phù hợp trong tài liệu.",
        evidence_items=evidence_items,
        allowed_source_ids=["doc_01"],
        notebook_id="NB-303",
        conversation_id="CONV-303",
    )

    assert trace.metadata["status"] == "insufficient_evidence"
    assert trace.metadata["insufficient_evidence"] is True
    assert is_insufficient_evidence(trace) is True

    # No unverified source or citation nodes created
    node_types = {n.node_type for n in trace.nodes}
    assert "source" not in node_types
    assert "citation" not in node_types

    valid, errors = EvidenceTraceContract.validate(trace)
    assert valid is True


def test_build_evidence_trace_unenabled_sources_filtered() -> None:
    """Verify that citations to disabled/un-enabled sources are rejected and not included in graph."""
    evidence_items = [
        {
            "id": "doc_disabled",
            "title": "Tài liệu bí mật",
            "snippet": "Nội dung không được bật.",
            "citation_label": "[1]",
        }
    ]

    # Answer cites [1] but doc_disabled is not in allowed_source_ids
    trace = build_evidence_trace_from_citations(
        query="Nội dung là gì?",
        answer_text="Theo [1], đây là nội dung.",
        evidence_items=evidence_items,
        allowed_source_ids=["doc_enabled_other"],  # doc_disabled is NOT enabled
        notebook_id="NB-404",
        conversation_id="CONV-404",
    )

    assert trace.metadata["status"] == "insufficient_evidence"
    assert trace.metadata["insufficient_evidence"] is True
    assert is_insufficient_evidence(trace) is True


def test_extract_cited_evidence_ids_word_boundaries() -> None:
    """Verify extract_cited_evidence_ids enforces word boundaries without false positives."""
    text = "Theo [1] và [E2], không phải EVD-100 hay doc_12."
    candidates = ["[1]", "[2]", "[E2]", "EVD-1", "EVD-100", "doc_1", "doc_12"]
    extracted = extract_cited_evidence_ids(text, candidates)

    assert "[1]" in extracted
    assert "[E2]" in extracted
    assert "EVD-100" in extracted
    assert "doc_12" in extracted

    # Should not match substrings inside other tokens
    assert "[2]" not in extracted
    assert "EVD-1" not in extracted
    assert "doc_1" not in extracted


def test_chat_message_trace_id_binding_and_serialization() -> None:
    """Verify ChatMessage trace_id field, to_dict, and from_dict backward compatibility."""
    msg = ChatMessage(
        id="MSG-001",
        conversation_id="CONV-001",
        role="assistant",
        content="Câu trả lời với bằng chứng.",
        trace_id="trc_abc123",
    )

    assert msg.trace_id == "trc_abc123"
    d = msg.to_dict()
    assert d["trace_id"] == "trc_abc123"

    # From dict with trace_id
    reconstructed = ChatMessage.from_dict(d)
    assert reconstructed.id == "MSG-001"
    assert reconstructed.trace_id == "trc_abc123"

    # Backward-compatible: from dict without trace_id
    legacy_dict = {
        "id": "MSG-LEGACY-001",
        "conversation_id": "CONV-001",
        "role": "user",
        "content": "Câu hỏi cũ",
        "extra_unknown_field": 12345,
    }
    legacy_msg = ChatMessage.from_dict(legacy_dict)
    assert legacy_msg.id == "MSG-LEGACY-001"
    assert legacy_msg.trace_id is None
