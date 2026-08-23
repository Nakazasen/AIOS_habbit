# -*- coding: utf-8 -*-
"""Tier 1 & Tier 2 Test Suite for Commit B: Evidence Trace Contract & Schema (`rag-trace/v1`).

Opaque-box and requirement-driven test suite validating:
1. EvidenceTrace dataclass structure and mandatory fields:
   - trace_id, notebook_id, conversation_id, user_message_id, assistant_message_id
   - created_at (ISO 8601 UTC), ui_locale, answer_language, source_language
   - provenance (operational_mode, provider_name, model_name)
   - nodes (EvidenceNode) and edges (EvidenceEdge)
2. Schema version support ('rag-trace/v1', 'evidence_trace_v1', '1.0.0') and rejection of invalid versions.
3. Locale validation ('vi', 'ja', 'zh-CN') and normalization.
4. Node & Edge validation:
   - Allowed node types (source, chunk, evidence, claim, citation, answer, etc.)
   - Allowed edge types (cites, supports, extracted_from, refutes, etc.)
   - Confidence and weight range constraints [0.0, 1.0]
   - Node ID uniqueness and duplicate rejection
   - Referential integrity: rejection of dangling edges (unknown source_id / target_id)
5. Strict serialization and round-trip fidelity (to_dict/from_dict, to_json/from_json).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest

from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_V1,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.i18n import SUPPORTED_LOCALES


@pytest.fixture
def valid_evidence_nodes() -> list[EvidenceNode]:
    """Create a standard set of valid evidence nodes."""
    return [
        EvidenceNode(
            id="src_doc_001",
            node_type="source",
            title="Quy trình vận hành kho InterStock v2.1",
            snippet="Hướng dẫn tiếp nhận và kiểm đếm hàng hóa tại kho.",
            source_id="local_cases/docs/interstock_v2.docx",
            confidence=1.0,
            privacy_label="local_only",
            language="vi",
        ),
        EvidenceNode(
            id="chk_doc_001_p1",
            node_type="chunk",
            title="Đoạn 1 - Kiểm đếm tự động",
            snippet="Khi hàng về, nhân viên quét mã vạch bằng thiết bị PDA chuyên dụng.",
            source_id="src_doc_001",
            confidence=0.95,
            privacy_label="local_only",
            language="vi",
        ),
        EvidenceNode(
            id="cit_001",
            node_type="citation",
            title="[1]",
            snippet="quét mã vạch bằng thiết bị PDA",
            source_id="src_doc_001",
            citation_id="[1]",
            confidence=1.0,
        ),
        EvidenceNode(
            id="clm_001",
            node_type="claim",
            title="Sử dụng PDA quét mã",
            snippet="Hàng hóa được kiểm đếm tự động bằng PDA khi nhập kho.",
            confidence=0.9,
            verification_status="verified",
        ),
        EvidenceNode(
            id="ans_001",
            node_type="answer",
            title="Câu trả lời hoàn chỉnh",
            snippet="Theo quy trình [1], hàng hóa được kiểm đếm tự động bằng thiết bị PDA.",
            confidence=1.0,
        ),
    ]


@pytest.fixture
def valid_evidence_edges() -> list[EvidenceEdge]:
    """Create a standard set of valid evidence edges connecting the fixture nodes."""
    return [
        EvidenceEdge(
            source_id="chk_doc_001_p1",
            target_id="src_doc_001",
            relation_type="extracted_from",
            weight=1.0,
        ),
        EvidenceEdge(
            source_id="cit_001",
            target_id="chk_doc_001_p1",
            relation_type="derived_from",
            weight=1.0,
        ),
        EvidenceEdge(
            source_id="clm_001",
            target_id="cit_001",
            relation_type="supports",
            weight=0.95,
        ),
        EvidenceEdge(
            source_id="ans_001",
            target_id="cit_001",
            relation_type="cites",
            weight=1.0,
        ),
    ]


@pytest.fixture
def valid_provenance() -> dict[str, str]:
    """Standard provenance payload."""
    return {
        "operational_mode": "direct",
        "provider_name": "Gemini Web Stream",
        "model_name": "gemini-2.5-flash",
    }


@pytest.fixture
def complete_valid_trace(
    valid_evidence_nodes: list[EvidenceNode],
    valid_evidence_edges: list[EvidenceEdge],
    valid_provenance: dict[str, str],
) -> EvidenceTrace:
    """Construct a complete, valid EvidenceTrace instance adhering to rag-trace/v1."""
    return EvidenceTrace(
        schema_version=getattr(EvidenceTrace, "SCHEMA_VERSION_RAG_V1", "rag-trace/v1"),
        trace_id="trc_20260823_001",
        query="Quy trình kiểm đếm hàng hóa tại kho InterStock thực hiện như thế nào?",
        answer_text="Theo quy trình [1], hàng hóa được kiểm đếm tự động bằng thiết bị PDA.",
        ui_locale="vi",
        answer_language="vi",
        source_language="vi",
        created_at=datetime.now(timezone.utc).isoformat(),
        nodes=valid_evidence_nodes,
        edges=valid_evidence_edges,
        metadata={
            "notebook_id": "nb_interstock_wms",
            "conversation_id": "conv_001",
            "user_message_id": "msg_usr_001",
            "assistant_message_id": "msg_ast_001",
            "provenance": valid_provenance,
            "status": "valid",
        },
    )


# ---------------------------------------------------------------------------
# Tier 1 Tests: Dataclass Contract & Schema Verification
# ---------------------------------------------------------------------------

class TestEvidenceTraceDataContract:
    """Validates structural properties of EvidenceTrace, EvidenceNode, and EvidenceEdge."""

    def test_trace_initialization_with_all_fields(
        self, complete_valid_trace: EvidenceTrace
    ) -> None:
        """Verify all mandatory fields are correctly populated and accessible."""
        trace = complete_valid_trace
        assert trace.trace_id == "trc_20260823_001"
        assert trace.query.startswith("Quy trình kiểm đếm")
        assert trace.answer_text.startswith("Theo quy trình [1]")
        assert trace.answer == trace.answer_text  # property alias
        assert trace.ui_locale == "vi"
        assert trace.answer_language == "vi"
        assert trace.source_language == "vi"
        assert len(trace.nodes) == 5
        assert len(trace.edges) == 4
        assert trace.metadata["notebook_id"] == "nb_interstock_wms"
        assert trace.metadata["conversation_id"] == "conv_001"
        assert trace.metadata["user_message_id"] == "msg_usr_001"
        assert trace.metadata["assistant_message_id"] == "msg_ast_001"
        assert trace.metadata["provenance"]["operational_mode"] == "direct"

    @pytest.mark.parametrize(
        "version_tag",
        ["rag-trace/v1", "evidence_trace_v1", "1.0.0"],
    )
    def test_supported_schema_versions(
        self,
        version_tag: str,
        valid_evidence_nodes: list[EvidenceNode],
        valid_evidence_edges: list[EvidenceEdge],
    ) -> None:
        """Verify standard schema version tags are accepted by contract validator."""
        trace = EvidenceTrace(
            schema_version=version_tag,
            trace_id="trc_test_version",
            query="Test query",
            answer_text="Test answer",
            nodes=valid_evidence_nodes,
            edges=valid_evidence_edges,
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Version {version_tag} failed validation: {errors}"

    @pytest.mark.parametrize(
        "invalid_version",
        ["rag-trace/v2", "2.0.0", "invalid_schema", "", "0.1.0-alpha"],
    )
    def test_invalid_schema_version_rejection(
        self,
        invalid_version: str,
        valid_evidence_nodes: list[EvidenceNode],
        valid_evidence_edges: list[EvidenceEdge],
    ) -> None:
        """Verify unrecognized schema versions fail contract validation."""
        trace = EvidenceTrace(
            schema_version=invalid_version,
            trace_id="trc_invalid_ver",
            nodes=valid_evidence_nodes,
            edges=valid_evidence_edges,
        )
        trace.schema_version = invalid_version
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("schema_version" in err for err in errors)

    @pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
    def test_supported_locales(
        self,
        locale: str,
        valid_evidence_nodes: list[EvidenceNode],
        valid_evidence_edges: list[EvidenceEdge],
    ) -> None:
        """Verify all 3 primary supported locales (vi, ja, zh-CN) pass contract validation."""
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id=f"trc_locale_{locale}",
            ui_locale=locale,
            answer_language=locale,
            nodes=valid_evidence_nodes,
            edges=valid_evidence_edges,
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Locale {locale} failed validation: {errors}"

    def test_locale_normalization_on_init(self) -> None:
        """Verify locale strings with regional variants or casing are normalized on initialization."""
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_norm",
            ui_locale="vi_VN",
            answer_language="zh-hans",
            source_language="JA",
        )
        assert trace.ui_locale == "vi"
        assert trace.answer_language == "zh-CN"
        assert trace.source_language == "ja"

    def test_invalid_locale_rejection(
        self,
        valid_evidence_nodes: list[EvidenceNode],
        valid_evidence_edges: list[EvidenceEdge],
    ) -> None:
        """Verify non-supported locales fail contract validation."""
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_invalid_loc",
            nodes=valid_evidence_nodes,
            edges=valid_evidence_edges,
        )
        # Bypass __post_init__ normalization to test validator defense
        object.__setattr__(trace, "ui_locale", "fr-FR")
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("ui_locale" in err for err in errors)


# ---------------------------------------------------------------------------
# Tier 2 Tests: Boundary Conditions, Referential Integrity & Invariant Rules
# ---------------------------------------------------------------------------

class TestEvidenceTraceIntegrityAndBoundaries:
    """Boundary value analysis and integrity checks for nodes, edges, and graphs."""

    @pytest.mark.parametrize("node_type", list(ALLOWED_NODE_TYPES))
    def test_all_allowed_node_types(self, node_type: str) -> None:
        """Ensure every officially allowed node type is valid."""
        node = EvidenceNode(id="node_x", node_type=node_type, title=f"Test {node_type}")
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_node_types",
            nodes=[node],
            edges=[],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Node type {node_type} failed validation: {errors}"

    def test_invalid_node_type_rejection(self) -> None:
        """Reject unapproved or misspelled node types."""
        node = EvidenceNode(id="node_bad", node_type="fraudulent_evidence")
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_bad_node",
            nodes=[node],
            edges=[],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("invalid node_type" in err for err in errors)

    @pytest.mark.parametrize("relation_type", list(ALLOWED_EDGE_TYPES))
    def test_all_allowed_edge_types(self, relation_type: str) -> None:
        """Ensure every officially allowed edge relation type is valid."""
        n1 = EvidenceNode(id="n1", node_type="source")
        n2 = EvidenceNode(id="n2", node_type="claim")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type=relation_type)
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_edge_types",
            nodes=[n1, n2],
            edges=[edge],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Edge type {relation_type} failed validation: {errors}"

    def test_invalid_edge_type_rejection(self) -> None:
        """Reject unapproved edge relation types."""
        n1 = EvidenceNode(id="n1", node_type="source")
        n2 = EvidenceNode(id="n2", node_type="claim")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type="magic_teleport")
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_bad_edge",
            nodes=[n1, n2],
            edges=[edge],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("invalid relation_type" in err for err in errors)

    def test_dangling_edge_source_rejection(
        self, valid_evidence_nodes: list[EvidenceNode]
    ) -> None:
        """Verify dangling edge with non-existent source_id is strictly rejected."""
        dangling_edge = EvidenceEdge(
            source_id="ghost_node_999",
            target_id=valid_evidence_nodes[0].id,
            relation_type="supports",
        )
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_dangling_src",
            nodes=valid_evidence_nodes,
            edges=[dangling_edge],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("ghost_node_999" in err and "source_id" in err for err in errors)

    def test_dangling_edge_target_rejection(
        self, valid_evidence_nodes: list[EvidenceNode]
    ) -> None:
        """Verify dangling edge with non-existent target_id is strictly rejected."""
        dangling_edge = EvidenceEdge(
            source_id=valid_evidence_nodes[0].id,
            target_id="phantom_target_999",
            relation_type="supports",
        )
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_dangling_tgt",
            nodes=valid_evidence_nodes,
            edges=[dangling_edge],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("phantom_target_999" in err and "target_id" in err for err in errors)

    def test_duplicate_node_id_rejection(self) -> None:
        """Verify duplicate node IDs in the same trace graph are rejected."""
        n1 = EvidenceNode(id="node_duplicate", node_type="source", title="First")
        n2 = EvidenceNode(id="node_duplicate", node_type="claim", title="Second")
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_dup_nodes",
            nodes=[n1, n2],
            edges=[],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("Duplicate node id" in err for err in errors)

    def test_duplicate_edge_id_rejection(self) -> None:
        """Verify duplicate edge_ids in the same trace graph are rejected."""
        n1 = EvidenceNode(id="n1", node_type="source")
        n2 = EvidenceNode(id="n2", node_type="claim")
        e1 = EvidenceEdge(source_id="n1", target_id="n2", relation_type="supports", edge_id="edge_001")
        e2 = EvidenceEdge(source_id="n1", target_id="n2", relation_type="cites", edge_id="edge_001")
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_dup_edges",
            nodes=[n1, n2],
            edges=[e1, e2],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("Duplicate edge_id" in err for err in errors)

    @pytest.mark.parametrize("invalid_confidence", [-0.1, 1.05, 999.0])
    def test_node_confidence_out_of_range_rejection(self, invalid_confidence: float) -> None:
        """Verify node confidence outside [0.0, 1.0] fails validation."""
        node = EvidenceNode(id="n1", node_type="claim", confidence=invalid_confidence)
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_conf_range",
            nodes=[node],
            edges=[],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("confidence" in err for err in errors)

    @pytest.mark.parametrize("invalid_weight", [-0.5, 1.5, 10.0])
    def test_edge_weight_out_of_range_rejection(self, invalid_weight: float) -> None:
        """Verify edge weight outside [0.0, 1.0] fails validation."""
        n1 = EvidenceNode(id="n1", node_type="source")
        n2 = EvidenceNode(id="n2", node_type="claim")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type="supports", weight=invalid_weight)
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_weight_range",
            nodes=[n1, n2],
            edges=[edge],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("weight" in err for err in errors)

    def test_invalid_iso_timestamp_rejection(self) -> None:
        """Verify malformed created_at timestamp fails contract validation."""
        trace = EvidenceTrace(
            schema_version="evidence_trace_v1",
            trace_id="trc_bad_ts",
            created_at="not-a-valid-iso-timestamp-2026-99-99",
            nodes=[],
            edges=[],
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert not is_valid
        assert any("created_at" in err for err in errors)


# ---------------------------------------------------------------------------
# Tier 2 & 3 Tests: Serialization, Aliases & Round-Trip Fidelity
# ---------------------------------------------------------------------------

class TestEvidenceTraceSerialization:
    """Verifies dict/JSON serialization, property aliases, and round-trip consistency."""

    def test_node_property_aliases(self) -> None:
        """Verify EvidenceNode aliases work seamlessly for both getters and from_dict."""
        node = EvidenceNode(
            id="nd_001",
            node_type="evidence",
            title="Title text",
            snippet="Snippet text",
            source_id="src_001",
            confidence=0.88,
        )
        assert node.node_id == "nd_001"
        assert node.label == "Title text"
        assert node.content == "Snippet text"
        assert node.source_path == "src_001"

        # Construct from alternative alias dictionary keys
        alt_data = {
            "node_id": "nd_alt_002",
            "node_type": "chunk",
            "label": "Alt Title",
            "content": "Alt Content",
            "source_path": "alt_src_path",
            "confidence": 0.77,
        }
        node_from_alt = EvidenceNode.from_dict(alt_data)
        assert node_from_alt.id == "nd_alt_002"
        assert node_from_alt.title == "Alt Title"
        assert node_from_alt.snippet == "Alt Content"
        assert node_from_alt.source_id == "alt_src_path"
        assert node_from_alt.confidence == 0.77

    def test_edge_property_aliases(self) -> None:
        """Verify EvidenceEdge aliases for source/target node IDs and confidence/weight."""
        edge = EvidenceEdge(
            source_id="src_a",
            target_id="tgt_b",
            relation_type="cites",
            weight=0.92,
        )
        assert edge.source_node_id == "src_a"
        assert edge.target_node_id == "tgt_b"
        assert edge.confidence == 0.92

        # Construct from alias dictionary keys
        alt_edge_data = {
            "source_node_id": "src_x",
            "target_node_id": "tgt_y",
            "relation_type": "supports",
            "confidence": 0.85,
        }
        edge_from_alt = EvidenceEdge.from_dict(alt_edge_data)
        assert edge_from_alt.source_id == "src_x"
        assert edge_from_alt.target_id == "tgt_y"
        assert edge_from_alt.weight == 0.85

    def test_json_roundtrip_fidelity(self, complete_valid_trace: EvidenceTrace) -> None:
        """Verify complete serialize -> JSON -> deserialize cycle preserves all fields."""
        orig = complete_valid_trace
        json_str = orig.to_json(ensure_ascii=False)
        recovered = EvidenceTrace.from_json(json_str)

        assert recovered.schema_version == orig.schema_version
        assert recovered.trace_id == orig.trace_id
        assert recovered.query == orig.query
        assert recovered.answer_text == orig.answer_text
        assert recovered.ui_locale == orig.ui_locale
        assert recovered.answer_language == orig.answer_language
        assert recovered.source_language == orig.source_language
        assert len(recovered.nodes) == len(orig.nodes)
        assert len(recovered.edges) == len(orig.edges)
        assert recovered.metadata == orig.metadata

        # Re-validate recovered trace against contract
        is_valid, errors = EvidenceTraceContract.validate_trace(recovered)
        assert is_valid, f"Recovered trace failed contract validation: {errors}"
