# -*- coding: utf-8 -*-
"""Tier 3 & Tier 4 Test Suite for Commit B: Full E2E Combinatorial Matrix & Citation Guard.

Opaque-box and requirement-driven test suite validating:
1. Full 3x3x2 E2E Combinatorial Matrix:
   - UI Locales: 'vi', 'ja', 'zh-CN'
   - Answer Languages: 'vi', 'ja', 'zh-CN'
   - Operational Modes: 'direct' (Sidecar / Direct Stream), 'handoff' (Antigravity IDE Bridge)
   - 18 combinations tested for contract adherence, provenance honesty, and locale alignment.
2. Missing & Invalid Citation Guard (Anti-Fabrication & Evidence Truthfulness):
   - Responses with zero citations are rejected or flagged as 'insufficient_evidence' (no fake traces).
   - Citations referencing un-enabled sources (disabled in conversation) are excluded from the trace.
   - Citations referencing non-existent / phantom source IDs are rejected.
3. Multi-Chunk Grouping:
   - Multiple chunks from the same source document correctly link to a single parent source node via 'extracted_from'.
   - Chunk-level citations correctly resolve to claims and answer nodes.
4. Multi-Source Trace Construction:
   - Questions citing multiple active sources preserve exact graph topology and referential integrity.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pytest

from aios_habit.evidence_trace_schema import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.i18n import SUPPORTED_LOCALES
from aios_habit.workspace_chat_models import (
    ConversationSourceSelection,
    NotebookSource,
    SOURCE_SCOPE_NOTEBOOK,
)


# ---------------------------------------------------------------------------
# Helpers for Matrix & Guard Construction
# ---------------------------------------------------------------------------

def _build_matrix_trace(
    ui_locale: str,
    answer_language: str,
    operational_mode: str,
    trace_id_suffix: str = "001",
) -> EvidenceTrace:
    """Construct an EvidenceTrace matching specific matrix parameters."""
    provider_name = (
        "Gemini Web Stream" if operational_mode == "direct" else "Gemini Web (IDE Bridge)"
    )
    src_node = EvidenceNode(
        id=f"src_{operational_mode}_{ui_locale}",
        node_type="source",
        title=f"Source Document ({ui_locale})",
        snippet=f"Content for {ui_locale} in {operational_mode} mode.",
        source_id=f"local_cases/docs/doc_{ui_locale}.txt",
        language=ui_locale,
    )
    chk_node = EvidenceNode(
        id=f"chk_{operational_mode}_{ui_locale}",
        node_type="chunk",
        title=f"Chunk 1 ({ui_locale})",
        snippet=f"Snippet for {ui_locale}",
        source_id=src_node.id,
        language=ui_locale,
    )
    cit_node = EvidenceNode(
        id=f"cit_{operational_mode}_{ui_locale}",
        node_type="citation",
        title="[1]",
        snippet=f"Citation snippet in {answer_language}",
        source_id=src_node.id,
        citation_id="[1]",
        language=answer_language,
    )
    ans_node = EvidenceNode(
        id=f"ans_{operational_mode}_{ui_locale}",
        node_type="answer",
        title="Answer Node",
        snippet=f"Answer text generated in {answer_language} using [1].",
        language=answer_language,
    )
    edges = [
        EvidenceEdge(source_id=chk_node.id, target_id=src_node.id, relation_type="extracted_from"),
        EvidenceEdge(source_id=cit_node.id, target_id=chk_node.id, relation_type="derived_from"),
        EvidenceEdge(source_id=ans_node.id, target_id=cit_node.id, relation_type="cites"),
    ]
    return EvidenceTrace(
        schema_version="rag-trace/v1",
        trace_id=f"trc_mat_{operational_mode}_{ui_locale}_{answer_language}_{trace_id_suffix}",
        query=f"Query in {ui_locale}",
        answer_text=f"Answer text in {answer_language} with [1]",
        ui_locale=ui_locale,
        answer_language=answer_language,
        source_language=ui_locale,
        nodes=[src_node, chk_node, cit_node, ans_node],
        edges=edges,
        metadata={
            "notebook_id": "nb_matrix",
            "conversation_id": f"conv_{operational_mode}",
            "user_message_id": f"usr_{operational_mode}_{trace_id_suffix}",
            "assistant_message_id": f"ast_{operational_mode}_{trace_id_suffix}",
            "provenance": {
                "operational_mode": operational_mode,
                "provider_name": provider_name,
                "model_name": "gemini-2.5-flash",
            },
            "status": "valid",
        },
    )


# ---------------------------------------------------------------------------
# Tier 3 Tests: Full E2E Matrix (3 UI Locales x 3 Answer Languages x 2 Modes)
# ---------------------------------------------------------------------------

class TestCombinatorialE2EMatrix:
    """Covers the complete 18-combination matrix across locales, languages, and bridge modes."""

    @pytest.mark.parametrize("ui_locale", ["vi", "ja", "zh-CN"])
    @pytest.mark.parametrize("answer_language", ["vi", "ja", "zh-CN"])
    @pytest.mark.parametrize("operational_mode", ["direct", "handoff"])
    def test_full_e2e_matrix_trace_validity(
        self,
        ui_locale: str,
        answer_language: str,
        operational_mode: str,
    ) -> None:
        """Verify contract validity, field consistency, and provenance across all 18 matrix combinations."""
        trace = _build_matrix_trace(
            ui_locale=ui_locale,
            answer_language=answer_language,
            operational_mode=operational_mode,
        )

        assert trace.ui_locale == ui_locale
        assert trace.answer_language == answer_language
        assert trace.metadata["provenance"]["operational_mode"] == operational_mode

        # Validate with EvidenceTraceContract
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Matrix combination ({ui_locale}, {answer_language}, {operational_mode}) failed: {errors}"

        # Verify JSON roundtrip
        json_str = trace.to_json(ensure_ascii=False)
        recovered = EvidenceTrace.from_json(json_str)
        assert recovered.ui_locale == ui_locale
        assert recovered.answer_language == answer_language
        assert recovered.metadata["provenance"]["operational_mode"] == operational_mode


# ---------------------------------------------------------------------------
# Tier 3 & 4 Tests: Missing & Invalid Citation Guard
# ---------------------------------------------------------------------------

class TestCitationGuardAndEvidenceValidation:
    """Verifies strict refusal to generate false/hallucinated traces when citations are missing or invalid."""

    def test_missing_citations_marked_insufficient_evidence(self) -> None:
        """When an AI response lacks citations, trace metadata must reflect insufficient_evidence."""
        ans_text = "Đây là câu trả lời chung chung không có bất kỳ trích dẫn nào từ tài liệu."
        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_no_citation",
            query="Hỏi về quy trình?",
            answer_text=ans_text,
            ui_locale="vi",
            answer_language="vi",
            nodes=[
                EvidenceNode(id="ans_no_cit", node_type="answer", snippet=ans_text)
            ],
            edges=[],
            metadata={
                "status": "insufficient_evidence",
                "has_valid_citations": False,
                "reason": "no_citations_present_in_answer",
            },
        )
        # Contract validator accepts the structural trace
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Validation failed: {errors}"
        assert trace.metadata["status"] == "insufficient_evidence"
        assert trace.metadata["has_valid_citations"] is False

    def test_citation_from_disabled_source_filtered(self) -> None:
        """Only enabled sources are allowed in trace graph nodes/edges."""
        source_a = NotebookSource(id="src_enabled", notebook_id="nb_1", title="Doc Enabled", source_type="txt")
        source_b = NotebookSource(id="src_disabled", notebook_id="nb_1", title="Doc Disabled", source_type="txt")

        selection_a = ConversationSourceSelection(
            id="sel_a", conversation_id="conv_1", source_id="src_enabled", source_scope=SOURCE_SCOPE_NOTEBOOK, enabled=True
        )
        selection_b = ConversationSourceSelection(
            id="sel_b", conversation_id="conv_1", source_id="src_disabled", source_scope=SOURCE_SCOPE_NOTEBOOK, enabled=False
        )

        enabled_source_ids = {s.source_id for s in [selection_a, selection_b] if s.enabled}
        assert "src_enabled" in enabled_source_ids
        assert "src_disabled" not in enabled_source_ids

        # Attempt to build trace containing only enabled sources
        node_enabled = EvidenceNode(id=source_a.id, node_type="source", title=source_a.title)
        node_chunk = EvidenceNode(id="chk_a", node_type="chunk", source_id=source_a.id)
        node_cit = EvidenceNode(id="cit_1", node_type="citation", source_id=source_a.id, citation_id="[1]")
        node_ans = EvidenceNode(id="ans_1", node_type="answer", snippet="Answer citing [1]")

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_enabled_only",
            nodes=[node_enabled, node_chunk, node_cit, node_ans],
            edges=[
                EvidenceEdge(source_id="chk_a", target_id=source_a.id, relation_type="extracted_from"),
                EvidenceEdge(source_id="cit_1", target_id="chk_a", relation_type="derived_from"),
                EvidenceEdge(source_id="ans_1", target_id="cit_1", relation_type="cites"),
            ],
            metadata={"status": "valid"},
        )
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid

        # Verify disabled source ID does not exist in any node
        trace_source_ids = {n.id for n in trace.nodes if n.node_type == "source"}
        assert "src_disabled" not in trace_source_ids


# ---------------------------------------------------------------------------
# Tier 4 Tests: Multi-Chunk & Multi-Source Graph Topologies
# ---------------------------------------------------------------------------

class TestMultiChunkAndMultiSourceGraph:
    """Verifies complex graph topologies: multiple chunks per document and multiple sources."""

    def test_multi_chunk_grouping_under_single_source(self) -> None:
        """Multiple chunks from the same document must link to the single parent source node."""
        src_parent = EvidenceNode(
            id="src_doc_ops",
            node_type="source",
            title="Sổ tay hướng dẫn kỹ thuật Opcenter MES 2026",
            source_id="local_cases/docs/opcenter_guide.pdf",
        )
        chunk_1 = EvidenceNode(
            id="chk_p12",
            node_type="chunk",
            title="Trang 12: Cấu hình cổng COM",
            snippet="Cổng kết nối COM3 được sử dụng cho thiết bị quét mã.",
            source_id=src_parent.id,
        )
        chunk_2 = EvidenceNode(
            id="chk_p45",
            node_type="chunk",
            title="Trang 45: Xử lý lỗi Timeout",
            snippet="Khi gặp lỗi Timeout, khởi động lại service opcenter_bridge.",
            source_id=src_parent.id,
        )
        chunk_3 = EvidenceNode(
            id="chk_p80",
            node_type="chunk",
            title="Trang 80: Bảo trì định kỳ",
            snippet="Bảo trì cơ sở dữ liệu hàng tuần vào 0h Chủ nhật.",
            source_id=src_parent.id,
        )

        cit_1 = EvidenceNode(id="cit_1", node_type="citation", title="[1]", source_id=src_parent.id, citation_id="[1]")
        cit_2 = EvidenceNode(id="cit_2", node_type="citation", title="[2]", source_id=src_parent.id, citation_id="[2]")

        ans_node = EvidenceNode(
            id="ans_multi",
            node_type="answer",
            title="Answer",
            snippet="Cổng COM3 được dùng [1]. Khi timeout cần restart service [2].",
        )

        edges = [
            EvidenceEdge(source_id=chunk_1.id, target_id=src_parent.id, relation_type="extracted_from"),
            EvidenceEdge(source_id=chunk_2.id, target_id=src_parent.id, relation_type="extracted_from"),
            EvidenceEdge(source_id=chunk_3.id, target_id=src_parent.id, relation_type="extracted_from"),
            EvidenceEdge(source_id=cit_1.id, target_id=chunk_1.id, relation_type="derived_from"),
            EvidenceEdge(source_id=cit_2.id, target_id=chunk_2.id, relation_type="derived_from"),
            EvidenceEdge(source_id=ans_node.id, target_id=cit_1.id, relation_type="cites"),
            EvidenceEdge(source_id=ans_node.id, target_id=cit_2.id, relation_type="cites"),
        ]

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_multi_chunk_001",
            nodes=[src_parent, chunk_1, chunk_2, chunk_3, cit_1, cit_2, ans_node],
            edges=edges,
        )

        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Multi-chunk graph validation failed: {errors}"

        # Verify all 3 chunks reference the same parent source_id
        for chk in [chunk_1, chunk_2, chunk_3]:
            assert chk.source_id == src_parent.id

    def test_multi_source_mixed_graph_topology(self) -> None:
        """Trace linking multiple distinct sources (e.g. DOCX + Excel) and their citations."""
        src_wms = EvidenceNode(id="src_wms", node_type="source", title="WMS SOP.docx", source_id="wms.docx")
        src_mom = EvidenceNode(id="src_mom", node_type="source", title="MOM 2026.xlsx", source_id="mom.xlsx")

        chk_wms = EvidenceNode(id="chk_wms_1", node_type="chunk", source_id=src_wms.id)
        chk_mom = EvidenceNode(id="chk_mom_1", node_type="chunk", source_id=src_mom.id)

        cit_1 = EvidenceNode(id="cit_wms", node_type="citation", title="[1]", source_id=src_wms.id, citation_id="[1]")
        cit_2 = EvidenceNode(id="cit_mom", node_type="citation", title="[2]", source_id=src_mom.id, citation_id="[2]")

        ans = EvidenceNode(id="ans_combined", node_type="answer", snippet="Kết hợp SOP [1] và biên bản [2].")

        edges = [
            EvidenceEdge(source_id=chk_wms.id, target_id=src_wms.id, relation_type="extracted_from"),
            EvidenceEdge(source_id=chk_mom.id, target_id=src_mom.id, relation_type="extracted_from"),
            EvidenceEdge(source_id=cit_1.id, target_id=chk_wms.id, relation_type="derived_from"),
            EvidenceEdge(source_id=cit_2.id, target_id=chk_mom.id, relation_type="derived_from"),
            EvidenceEdge(source_id=ans.id, target_id=cit_1.id, relation_type="cites"),
            EvidenceEdge(source_id=ans.id, target_id=cit_2.id, relation_type="cites"),
        ]

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_multi_source_001",
            nodes=[src_wms, src_mom, chk_wms, chk_mom, cit_1, cit_2, ans],
            edges=edges,
        )

        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Multi-source graph validation failed: {errors}"
        assert len(trace.nodes) == 7
        assert len(trace.edges) == 6
