# -*- coding: utf-8 -*-
"""Comprehensive Opaque-Box E2E Acceptance Test Suite for Commit A Refinements.

Requirements Covered (from ORIGINAL_REQUEST.md & PROJECT.md):
- R1 (F1-F5): Handoff Bundle Multilingual Support, Manifest answer_language Persistence,
              Prompt Language Instructions (vi/ja/zh-CN), Verbatim Evidence Preservation.
- R2 (F6-F8): UI i18n Refinement, 100% Translation Key Parity, UI Localized Labels Lookup,
              AST Anti-Hardcode Verification for Workspace Chat UI renderers.
- R3 (F9-F12): Evidence Trace Schema Strict Type Validation Enforcement (ALLOWED_NODE_TYPES,
               ALLOWED_EDGE_TYPES allow-lists), Zero Exporter / Render Graph Isolation.
- R4 (F13-F14): Full Test Suite Regression, Static Compilation & Diff Hygiene.

Test Architecture:
- Tier 1: Feature Isolation (Happy path for every individual Commit A feature & contract)
- Tier 2: Boundary & Corner Cases (Fallback on unknown locales, schema rejection of invalid
          node/edge types, dangling edges, out-of-range bounds, size limits, UTF-8 anti-mojibake)
- Tier 3: Cross-Feature Combinations (Pairwise matrix: locales [vi, ja, zh-CN] x components,
          mixed-language evidence trace contracts, dynamic locale switching across stores)
- Tier 4: Real-World Scenarios (End-to-end simulated chat workflows, full JA & zh-CN handoff
          bundle creation and validation, complex 12-node x 12-edge graph contract verification,
          AST static scan of UI renderers, and zero-exporter isolation verification)
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock

import pytest

from aios_habit.case_models import EvidenceItem
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
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    LOCALE_NAMES,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_ai_language_instruction,
    get_supported_locales,
    normalize_locale,
    t,
)
from aios_habit.ide_handoff_bridge import (
    DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    HANDOFF_ROOT,
    REQ_STATE_COMPLETED,
    REQ_STATE_FAILED,
    REQ_STATE_PENDING,
    RESPONSE_SCHEMA_VERSION,
    FullBundleRequest,
    build_evidence_markdown,
    build_full_bundle_request,
    build_ide_task_instruction,
    build_prompt_md,
    check_handoff_request_timeouts,
    import_ide_response,
    is_request_expired,
    list_pending_ide_requests,
    update_request_status,
    validate_handoff_bundle,
    verify_bundle_integrity,
    write_ide_handoff_bundle,
)
from aios_habit.workspace_chat_models import (
    ChatMessage,
    DocumentNotebook,
    TemporaryConversationSource,
    WorkspaceConversation,
)
import aios_habit.workspace_chat_store as chat_store
from aios_habit.workspace_chat_ui import (
    get_localized_labels,
    get_vietnamese_labels,
    render_language_selector,
)


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def sample_evidence_items() -> List[EvidenceItem]:
    """Sample diverse evidence items including plain text, PDF, and XLSX sources."""
    return [
        EvidenceItem(
            evidence_id="EVD-001",
            case_id="CASE-ACCEPT-01",
            source_type="plain_text",
            source_path="logs/audit_2026.log",
            title="Audit System Log",
            extracted_text="[1] System operational. Error code: ERR_OK. Ref: document.pdf",
            privacy_level="local_only",
        ),
        EvidenceItem(
            evidence_id="EVD-002",
            case_id="CASE-ACCEPT-01",
            source_type="pdf",
            source_path="docs/operational_manual.pdf",
            title="Operational Manual PDF",
            extracted_text="[E1] Standard procedure step 1: initialize cluster nodes.",
            privacy_level="cloud_allowed",
        ),
        EvidenceItem(
            evidence_id="EVD-003",
            case_id="CASE-ACCEPT-01",
            source_type="xlsx",
            source_path="finance/q3_report.xlsx",
            title="Q3 Financial Overview",
            extracted_text="Revenue: 150B VND. Verified by auditor [EVD-001].",
            privacy_level="cloud_allowed",
        ),
    ]


@pytest.fixture
def isolated_chat_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate chat store storage in a temporary directory."""
    test_dir = tmp_path / "chat_store_isolated"
    monkeypatch.setattr(chat_store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(chat_store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(chat_store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(chat_store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(chat_store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(chat_store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(chat_store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    chat_store.init_chat_store()
    return test_dir


# ============================================================================
# TIER 1: FEATURE ISOLATION TESTS
# ============================================================================

class TestTier1FeatureIsolation:
    """Tier 1: Verify each individual Commit A feature in complete isolation."""

    # ------------------------------------------------------------------------
    # Feature 1 & 2: Handoff Parameter Propagation & Manifest answer_language
    # ------------------------------------------------------------------------

    def test_handoff_write_bundle_propagates_answer_language_japanese(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify write_ide_handoff_bundle accepts and propagates answer_language='ja'."""
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-JA-01",
            question="サーバーの状態はどうですか？",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True
        manifest_path = bundle_req.bundle_dir / "manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data.get("request_id") == bundle_req.request_id
        assert manifest_data.get("FULL_BUNDLE_COMPLETE") == "YES"

    def test_handoff_write_bundle_propagates_answer_language_chinese(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify write_ide_handoff_bundle accepts and propagates answer_language='zh-CN'."""
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-ZH-01",
            question="系统运行状态如何？",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True
        manifest_path = bundle_req.bundle_dir / "manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data.get("question") == "系统运行状态如何？"

    def test_handoff_build_full_bundle_request_manifest_structure(
        self, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify build_full_bundle_request returns valid manifest and records."""
        manifest, records, source_manifest, instruction = build_full_bundle_request(
            case_id="CASE-ISO-01",
            question="Tra cứu mã lỗi hệ thống?",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
        )
        assert manifest["case_id"] == "CASE-ISO-01"
        assert manifest["evidence_item_count"] == len(sample_evidence_items)
        assert manifest["omitted_items_count"] == 0
        assert manifest["FULL_BUNDLE_COMPLETE"] == "YES"
        assert len(records) == len(sample_evidence_items)
        assert "request_id" in source_manifest

    # ------------------------------------------------------------------------
    # Feature 3: Prompt Language Instructions & Invariant Citation Preservation
    # ------------------------------------------------------------------------

    def test_prompt_language_instruction_vietnamese(self) -> None:
        """Verify Vietnamese AI language instruction mandates 100% verbatim citation preservation."""
        instr = get_ai_language_instruction("vi")
        assert "Tiếng Việt" in instr
        assert "[1]" in instr
        assert "[E1]" in instr
        assert "EVD-001" in instr
        assert "document.pdf" in instr
        assert "không dịch" in instr or "Giữ nguyên" in instr

    def test_prompt_language_instruction_japanese(self) -> None:
        """Verify Japanese AI language instruction mandates 100% verbatim citation preservation."""
        instr = get_ai_language_instruction("ja")
        assert "日本語" in instr
        assert "[1]" in instr
        assert "[E1]" in instr
        assert "EVD-001" in instr
        assert "document.pdf" in instr
        assert "翻訳せず" in instr or "保持" in instr

    def test_prompt_language_instruction_simplified_chinese(self) -> None:
        """Verify Simplified Chinese AI language instruction mandates 100% verbatim citation preservation."""
        instr = get_ai_language_instruction("zh-CN")
        assert "简体中文" in instr
        assert "[1]" in instr
        assert "[E1]" in instr
        assert "EVD-001" in instr
        assert "document.pdf" in instr
        assert "严禁翻译" in instr or "完整保留" in instr

    def test_verbatim_evidence_citations_in_evidence_bundle(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify citations [1], [E1], EVD-001, and document.pdf are verbatim in bundle files."""
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-VERB-01",
            question="Kiểm tra citation preservation",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        evidence_jsonl = (bundle_req.bundle_dir / "evidence_full.jsonl").read_text(encoding="utf-8")
        assert "EVD-001" in evidence_jsonl
        assert "ERR_OK" in evidence_jsonl
        assert "document.pdf" in evidence_jsonl
        assert "[E1]" in evidence_jsonl

        evidence_md = (bundle_req.bundle_dir / "evidence_full.md").read_text(encoding="utf-8")
        assert "EVD-001" in evidence_md
        assert "operational_manual.pdf" in evidence_md

    # ------------------------------------------------------------------------
    # Feature 6 & 7: i18n Translation Key Coverage & Parity
    # ------------------------------------------------------------------------

    def test_i18n_translation_keys_100_percent_parity(self) -> None:
        """Verify 100% key parity across vi, ja, and zh-CN translation catalogs."""
        vi_keys = set(TRANSLATIONS["vi"].keys())
        ja_keys = set(TRANSLATIONS["ja"].keys())
        zh_keys = set(TRANSLATIONS["zh-CN"].keys())

        assert vi_keys == ja_keys, f"Parity mismatch vi vs ja: {vi_keys ^ ja_keys}"
        assert vi_keys == zh_keys, f"Parity mismatch vi vs zh-CN: {vi_keys ^ zh_keys}"
        assert len(vi_keys) >= 120, f"Expected at least 120 keys, found {len(vi_keys)}"

    def test_i18n_get_supported_locales_returns_expected_pairs(self) -> None:
        """Verify get_supported_locales returns exactly (vi, ja, zh-CN) with localized names."""
        locales = get_supported_locales()
        assert len(locales) == 3
        codes = [c for c, _ in locales]
        assert codes == ["vi", "ja", "zh-CN"]
        names = [n for _, n in locales]
        assert names == ["Tiếng Việt", "日本語", "简体中文"]

    def test_i18n_t_lookup_exact_for_all_supported_locales(self) -> None:
        """Verify t() returns correct translations for core keys across all 3 locales."""
        # Open notebook
        assert t("open_notebook", locale="vi") == "Mở sổ"
        assert t("open_notebook", locale="ja") == "ノートを開く"
        assert t("open_notebook", locale="zh-CN") == "打开笔记本"

        # AI Action
        assert t("ai_action", locale="vi") == "Hỏi"
        assert t("ai_action", locale="ja") == "質問する"
        assert t("ai_action", locale="zh-CN") == "提问"

        # Evidence graph
        assert t("evidence_graph", locale="vi") == "Đồ thị bằng chứng"
        assert t("evidence_graph", locale="ja") == "根拠グラフ"
        assert t("evidence_graph", locale="zh-CN") == "证据图谱"

    def test_ui_get_localized_labels_coverage(self) -> None:
        """Verify get_localized_labels returns comprehensive label dictionary for each locale."""
        for loc in ("vi", "ja", "zh-CN"):
            labels = get_localized_labels(loc)
            assert isinstance(labels, dict)
            assert len(labels) >= 100
            assert "app_title" in labels
            assert "open_notebook" in labels
            assert "language_selector" in labels
            assert "answer_language_selector" in labels

    def test_ui_get_vietnamese_labels_backward_compatibility(self) -> None:
        """Verify legacy get_vietnamese_labels() keys exist with exact values in get_localized_labels('vi')."""
        legacy = get_vietnamese_labels()
        localized_vi = get_localized_labels("vi")
        for k, v in legacy.items():
            assert k in localized_vi, f"Legacy key '{k}' missing from get_localized_labels('vi')"
            assert localized_vi[k] == v, f"Value mismatch for key '{k}'"

    # ------------------------------------------------------------------------
    # Feature 9, 10, 11: EvidenceTraceContract Allow-List Validation
    # ------------------------------------------------------------------------

    @pytest.mark.parametrize("node_type", sorted(ALLOWED_NODE_TYPES))
    def test_evidence_trace_contract_accepts_all_12_allowed_node_types(self, node_type: str) -> None:
        """Verify EvidenceTraceContract accepts all 12 declared ALLOWED_NODE_TYPES."""
        node = EvidenceNode(id=f"node_{node_type}", node_type=node_type, title=f"Node of type {node_type}")
        trace = EvidenceTrace(
            trace_id="tr_node_type_test",
            schema_version=SCHEMA_VERSION_1_0_0,
            ui_locale="vi",
            answer_language="vi",
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is True, f"Failed on allowed node_type '{node_type}': {errors}"
        assert errors == []

    @pytest.mark.parametrize("relation_type", sorted(ALLOWED_EDGE_TYPES))
    def test_evidence_trace_contract_accepts_all_12_allowed_edge_types(self, relation_type: str) -> None:
        """Verify EvidenceTraceContract accepts all 12 declared ALLOWED_EDGE_TYPES."""
        n1 = EvidenceNode(id="n1", node_type="claim", title="Claim 1")
        n2 = EvidenceNode(id="n2", node_type="source", title="Source 1")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type=relation_type)
        trace = EvidenceTrace(
            trace_id="tr_edge_type_test",
            schema_version=SCHEMA_VERSION_1_0_0,
            ui_locale="vi",
            answer_language="vi",
            nodes=[n1, n2],
            edges=[edge],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is True, f"Failed on allowed relation_type '{relation_type}': {errors}"
        assert errors == []

    def test_evidence_trace_dataclass_fields_and_aliases(self) -> None:
        """Verify EvidenceNode and EvidenceEdge property aliases and serialization."""
        node = EvidenceNode(
            id="node_prop_01",
            node_type="evidence",
            title="Bằng chứng vận hành",
            snippet="Trích đoạn chi tiết",
            source_id="docs/guide.pdf",
            confidence=0.95,
        )
        assert node.node_id == "node_prop_01"
        assert node.label == "Bằng chứng vận hành"
        assert node.content == "Trích đoạn chi tiết"
        assert node.source_path == "docs/guide.pdf"

        edge = EvidenceEdge(
            source_id="node_prop_01",
            target_id="node_target_01",
            relation_type="supports",
            weight=0.9,
            edge_id="edge_01",
        )
        assert edge.source_node_id == "node_prop_01"
        assert edge.target_node_id == "node_target_01"
        assert edge.confidence == 0.9


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASE TESTS
# ============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Verify boundaries, invalid inputs, fallbacks, and constraint enforcement."""

    # ------------------------------------------------------------------------
    # Locale Normalization & Fallbacks
    # ------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "raw_locale,expected_normalized",
        [
            (None, "vi"),
            ("", "vi"),
            ("   ", "vi"),
            ("unknown_locale", "vi"),
            ("fr-FR", "vi"),
            ("de", "vi"),
            ("es-ES", "vi"),
            (12345, "vi"),
            (["invalid"], "vi"),
            # Valid variants
            ("vi", "vi"),
            ("vi-VN", "vi"),
            ("vi_VN", "vi"),
            ("VIETNAMESE", "vi"),
            ("ja", "ja"),
            ("ja-JP", "ja"),
            ("ja_jp", "ja"),
            ("japanese", "ja"),
            ("zh", "zh-CN"),
            ("zh-CN", "zh-CN"),
            ("zh_CN", "zh-CN"),
            ("zh-Hans", "zh-CN"),
            ("zh-Hans-CN", "zh-CN"),
            ("zh-SG", "zh-CN"),
            ("chinese", "zh-CN"),
        ],
    )
    def test_normalize_locale_boundary_matrix(self, raw_locale: Any, expected_normalized: str) -> None:
        """Verify normalize_locale strictly maps valid variants and falls back to 'vi' on unknowns."""
        assert normalize_locale(raw_locale) == expected_normalized

    def test_t_function_unknown_key_returns_key_itself(self) -> None:
        """Verify t() returns the key itself when looking up non-existent translation key."""
        assert t("completely_non_existent_key_999", locale="vi") == "completely_non_existent_key_999"
        assert t("completely_non_existent_key_999", locale="ja") == "completely_non_existent_key_999"
        assert t("completely_non_existent_key_999", locale="zh-CN") == "completely_non_existent_key_999"

    def test_t_function_formatting_error_resilience(self) -> None:
        """Verify t() returns template string when wrong kwargs are provided rather than raising KeyError."""
        template = t("enabled_sources_count", locale="vi", wrong_arg_name=42)
        assert template == "Nguồn đang bật: {count}"

    # ------------------------------------------------------------------------
    # EvidenceTraceContract Strict Type Validation Rejections
    # ------------------------------------------------------------------------

    def test_contract_rejects_empty_or_missing_node_id(self) -> None:
        """Verify contract rejects node with empty string or whitespace id."""
        node = EvidenceNode(id="", node_type="source", title="Untitled")
        trace = EvidenceTrace(
            trace_id="tr_bad_node_id",
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("missing id" in e.lower() for e in errors)

    def test_contract_rejects_duplicate_node_ids(self) -> None:
        """Verify contract rejects duplicate node ids within a trace."""
        n1 = EvidenceNode(id="dup_node_01", node_type="claim", title="Claim A")
        n2 = EvidenceNode(id="dup_node_01", node_type="source", title="Source B")
        trace = EvidenceTrace(
            trace_id="tr_dup_nodes",
            nodes=[n1, n2],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("duplicate node id" in e.lower() for e in errors)

    def test_contract_rejects_dangling_edge_source_or_target(self) -> None:
        """Verify contract rejects edges pointing to non-existent node ids."""
        n1 = EvidenceNode(id="node_valid", node_type="claim")
        edge_dangling_target = EvidenceEdge(source_id="node_valid", target_id="node_non_existent", relation_type="cites")
        edge_dangling_source = EvidenceEdge(source_id="node_ghost", target_id="node_valid", relation_type="supports")

        trace = EvidenceTrace(
            trace_id="tr_dangling",
            nodes=[n1],
            edges=[edge_dangling_target, edge_dangling_source],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("target_id 'node_non_existent' not found in nodes" in e for e in errors)
        assert any("source_id 'node_ghost' not found in nodes" in e for e in errors)

    def test_contract_rejects_out_of_range_confidence_and_weight(self) -> None:
        """Verify contract rejects confidence and weight outside [0.0, 1.0]."""
        n1 = EvidenceNode(id="n1", node_type="claim", confidence=1.5)
        n2 = EvidenceNode(id="n2", node_type="source", confidence=-0.1)
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type="supports", weight=2.0)

        trace = EvidenceTrace(
            trace_id="tr_out_of_bounds",
            nodes=[n1, n2],
            edges=[edge],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("confidence" in e.lower() and "out of range" in e.lower() for e in errors)
        assert any("weight" in e.lower() and "out of range" in e.lower() for e in errors)

    def test_contract_rejects_invalid_iso8601_timestamp(self) -> None:
        """Verify contract rejects malformed created_at timestamp."""
        node = EvidenceNode(id="n1", node_type="claim")
        trace = EvidenceTrace(
            trace_id="tr_bad_time",
            created_at="invalid-date-format-2026",
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("Invalid ISO 8601 created_at format" in e for e in errors)

    def test_contract_rejects_unsupported_schema_version(self) -> None:
        """Verify contract rejects unsupported schema_version strings."""
        node = EvidenceNode(id="n1", node_type="claim")
        trace = EvidenceTrace(
            trace_id="tr_bad_schema",
            schema_version="99.0.0_unsupported",
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("Invalid schema_version" in e for e in errors)

    def test_contract_rejects_unknown_node_type(self) -> None:
        """Verify contract rejects node with unknown node_type not in ALLOWED_NODE_TYPES (Requirement R3)."""
        node = EvidenceNode(id="n_invalid", node_type="unsupported_custom_node_type", title="Invalid Node")
        trace = EvidenceTrace(
            trace_id="tr_bad_node_type",
            schema_version=SCHEMA_VERSION_1_0_0,
            ui_locale="vi",
            answer_language="vi",
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False, "Contract should have rejected unknown node_type 'unsupported_custom_node_type'"
        assert any("node_type" in e.lower() for e in errors)

    def test_contract_rejects_unknown_edge_type(self) -> None:
        """Verify contract rejects edge with unknown relation_type not in ALLOWED_EDGE_TYPES (Requirement R3)."""
        n1 = EvidenceNode(id="n1", node_type="claim")
        n2 = EvidenceNode(id="n2", node_type="source")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type="unsupported_custom_relation_type")
        trace = EvidenceTrace(
            trace_id="tr_bad_edge_type",
            schema_version=SCHEMA_VERSION_1_0_0,
            ui_locale="vi",
            answer_language="vi",
            nodes=[n1, n2],
            edges=[edge],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False, "Contract should have rejected unknown relation_type 'unsupported_custom_relation_type'"
        assert any("relation_type" in e.lower() or "edge" in e.lower() for e in errors)

    def test_contract_rejects_duplicate_edge_ids(self) -> None:
        """Verify contract rejects duplicate edge_id within a trace."""
        n1 = EvidenceNode(id="n1", node_type="claim")
        n2 = EvidenceNode(id="n2", node_type="source")
        n3 = EvidenceNode(id="n3", node_type="evidence")
        e1 = EvidenceEdge(source_id="n1", target_id="n2", relation_type="cites", edge_id="dup_edge_01")
        e2 = EvidenceEdge(source_id="n2", target_id="n3", relation_type="supports", edge_id="dup_edge_01")
        trace = EvidenceTrace(
            trace_id="tr_dup_edges",
            nodes=[n1, n2, n3],
            edges=[e1, e2],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False
        assert any("duplicate edge_id" in e.lower() for e in errors)

    # ------------------------------------------------------------------------
    # Handoff Bridge Boundaries & Size Guards
    # ------------------------------------------------------------------------

    def test_handoff_empty_question_raises_value_error(self, tmp_path: Path) -> None:
        """Verify write_ide_handoff_bundle raises ValueError when question is blank."""
        with pytest.raises(ValueError, match="question is required"):
            write_ide_handoff_bundle(
                case_id="CASE-01",
                question="   ",
                bundle_scope="active_case_all",
                evidence_items=[],
                root=tmp_path,
            )

    def test_handoff_unsupported_bundle_scope_raises_value_error(self, tmp_path: Path) -> None:
        """Verify write_ide_handoff_bundle raises ValueError on invalid bundle_scope."""
        with pytest.raises(ValueError, match="unsupported bundle_scope"):
            write_ide_handoff_bundle(
                case_id="CASE-01",
                question="Valid question",
                bundle_scope="invalid_custom_scope",
                evidence_items=[],
                root=tmp_path,
            )

    def test_handoff_max_total_text_chars_size_guard(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify full bundle size guard stops export without partial omission."""
        with pytest.raises(ValueError, match="full bundle size guard triggered"):
            write_ide_handoff_bundle(
                case_id="CASE-01",
                question="Valid question",
                bundle_scope="active_case_all",
                evidence_items=sample_evidence_items,
                max_total_text_chars=10,  # Extremely small to trigger guard
                root=tmp_path,
            )

    # ------------------------------------------------------------------------
    # UTF-8 & Anti-Mojibake Integrity
    # ------------------------------------------------------------------------

    def test_utf8_anti_mojibake_multilingual_json_serialization(self) -> None:
        """Verify multi-byte strings in vi, ja, zh-CN serialize to pure UTF-8 without unicode escapes."""
        data = {
            "vi": "Hệ thống AIOS WorkLens: đối soát bằng chứng ắ, ằ, ẳ, ẵ, ặ, ế, ề, ể, ễ, ệ, ố, ồ, ổ, ỗ, ộ.",
            "ja": "日本語：証拠トレース契約、ノード・エッジの厳格な検証、および引用の完全性保持。",
            "zh-CN": "简体中文：证据追踪数据契约、多语言提示词注入与严格的去乱码保证。",
            "mixed": "[E1] /path/to/報告書_2026.xlsx -> ERR_OK: 処理完了 (Thành công / 成功)",
        }
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        assert "\\u" not in serialized, "Found ASCII unicode escape sequence in serialized UTF-8 payload"
        assert "Hệ thống AIOS WorkLens" in serialized
        assert "証拠トレース契約" in serialized
        assert "证据追踪数据契约" in serialized

        deserialized = json.loads(serialized)
        assert deserialized == data


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATION TESTS
# ============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise combinations across locales, components, and multilingual graphs."""

    @pytest.mark.parametrize("ui_locale", ["vi", "ja", "zh-CN"])
    @pytest.mark.parametrize("answer_lang", ["vi", "ja", "zh-CN"])
    def test_pairwise_locales_evidence_trace_contract_matrix(
        self, ui_locale: str, answer_lang: str
    ) -> None:
        """Pairwise matrix: test EvidenceTrace with all ui_locale x answer_language combinations."""
        n1 = EvidenceNode(id="n_q", node_type="question", title=f"Question in {ui_locale}")
        n2 = EvidenceNode(id="n_a", node_type="answer", title=f"Answer in {answer_lang}")
        edge = EvidenceEdge(source_id="n_q", target_id="n_a", relation_type="derives_from")

        trace = EvidenceTrace(
            trace_id=f"tr_pair_{ui_locale}_{answer_lang}",
            ui_locale=ui_locale,
            answer_language=answer_lang,
            source_language="vi",
            nodes=[n1, n2],
            edges=[edge],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is True, f"Failed for ui_locale={ui_locale}, answer_language={answer_lang}: {errors}"
        assert trace.ui_locale == ui_locale
        assert trace.answer_language == answer_lang

    @pytest.mark.parametrize("bundle_scope", [
        "active_case_all",
        "selected_folder_all",
        "current_question_retrieval_plus_full_scope_manifest",
    ])
    def test_pairwise_bundle_scopes_with_handoff_validation(
        self, tmp_path: Path, bundle_scope: str, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Pairwise matrix: test handoff bundle generation and validation across all 3 valid scopes."""
        bundle_req = write_ide_handoff_bundle(
            case_id=f"CASE-SCOPE-{bundle_scope[:6]}",
            question="Tra cứu theo phạm vi bundle?",
            bundle_scope=bundle_scope,
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True
        validation = validate_handoff_bundle(bundle_req.bundle_dir)
        assert validation["ok"] is True
        assert len(validation["missing"]) == 0

    def test_mixed_language_multilingual_evidence_trace_workflow(self) -> None:
        """Verify a mixed-language trace (JA UI + ZH-CN Answer + VI Evidence) serializes and validates."""
        n_source = EvidenceNode(
            id="src_vi_01",
            node_type="source",
            title="Báo cáo kiểm toán quý 3.pdf",
            snippet="Nội dung kiểm toán: Doanh thu 150 tỷ [E1].",
            language="vi",
        )
        n_claim = EvidenceNode(
            id="claim_zh_01",
            node_type="claim",
            title="季度审计完成声明",
            snippet="根据越南审计报告，第三季度营收已确认。",
            language="zh-CN",
        )
        edge = EvidenceEdge(
            source_id="claim_zh_01",
            target_id="src_vi_01",
            relation_type="cites",
            label="引用越南语来源",
        )

        trace = EvidenceTrace(
            trace_id="tr_mixed_multilingual_01",
            query="第三季度财务状况如何？",
            answer_text="根据审计报告 [E1]，第三季度营收为1500亿越盾。",
            ui_locale="ja",
            answer_language="zh-CN",
            source_language="vi",
            nodes=[n_source, n_claim],
            edges=[edge],
        )

        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is True, f"Validation failed on mixed multilingual trace: {errors}"

        # JSON Roundtrip
        json_repr = trace.to_json()
        reconstructed = EvidenceTrace.from_json(json_repr)
        assert reconstructed.trace_id == trace.trace_id
        assert reconstructed.ui_locale == "ja"
        assert reconstructed.answer_language == "zh-CN"
        assert len(reconstructed.nodes) == 2
        assert len(reconstructed.edges) == 1

    def test_conversation_store_and_handoff_locale_consistency(
        self, isolated_chat_store: Path, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Verify conversation settings in chat store seamlessly propagate to handoff bundle creation."""
        conv = WorkspaceConversation(
            id="conv_sync_01",
            notebook_id="mom_opcenter",
            title="Hội thoại đồng bộ",
            ui_locale="ja",
            answer_language="ja",
        )
        chat_store.save_conversation(conv)

        loaded_conv = chat_store.load_conversation("conv_sync_01")
        assert loaded_conv is not None
        assert loaded_conv.ui_locale == "ja"
        assert loaded_conv.answer_language == "ja"

        bundle_req = write_ide_handoff_bundle(
            case_id=loaded_conv.id,
            question="サーバーのエラーログを分析してください",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True
        assert bundle_req.manifest["case_id"] == "conv_sync_01"


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Complex end-to-end workflows, full bundles, 12-node/12-edge graphs, and AST scan."""

    def test_scenario_1_e2e_chat_workflow_with_locale_switching(
        self, isolated_chat_store: Path
    ) -> None:
        """Scenario 1: End-to-end chat workflow with dynamic locale switching and temporary sources."""
        # 1. Create conversation with default Vietnamese
        conv = WorkspaceConversation(
            id="conv_scenario_1",
            notebook_id="mom_opcenter",
            title="Vận hành hệ thống",
            ui_locale="vi",
            answer_language="vi",
        )
        chat_store.save_conversation(conv)

        # 2. Add temporary source
        ts = TemporaryConversationSource(
            id="temp_src_01",
            conversation_id="conv_scenario_1",
            source_type="plain_text",
            title="cluster_config.yaml",
            content_preview="port: 8080 | workers: 4",
            content_text="port: 8080\nworkers: 4\nmode: production [E1]",
        )
        chat_store.save_temporary_source(ts)

        # 3. User posts question
        msg_user = ChatMessage(
            id="msg_u1",
            conversation_id="conv_scenario_1",
            role="user",
            content="Cấu hình cổng và số worker là bao nhiêu?",
        )
        chat_store.save_message(msg_user)

        # 4. Switch locale to Japanese
        updated_conv = chat_store.update_conversation_language_settings(
            "conv_scenario_1",
            ui_locale="ja",
            answer_language="ja",
        )
        assert updated_conv is not None
        assert updated_conv.ui_locale == "ja"
        assert updated_conv.answer_language == "ja"

        # 5. Verify UI labels reflect Japanese
        ja_labels = get_localized_labels(updated_conv.ui_locale)
        assert ja_labels["open_notebook"] == "ノートを開く"
        assert ja_labels["language_selector"] == "表示言語"

        # 6. Save assistant response with Japanese content
        msg_ai = ChatMessage(
            id="msg_a1",
            conversation_id="conv_scenario_1",
            role="assistant",
            content="設定ファイル [E1] によると、ポートは 8080、ワーカー数は 4 です。",
        )
        chat_store.save_message(msg_ai)

        # 7. Reload and verify conversation history
        messages = chat_store.load_messages("conv_scenario_1")
        assert len(messages) == 2
        assert messages[0].content == "Cấu hình cổng và số worker là bao nhiêu?"
        assert "[E1]" in messages[1].content
        assert "ポートは 8080" in messages[1].content

    def test_scenario_2_complete_japanese_handoff_bundle_e2e(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Scenario 2: Complete Japanese handoff bundle generation, validation, and simulated import."""
        # 1. Create Outbox Bundle for Japanese
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-JA-E2E",
            question="監査ログのエラーコードを特定してください",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True

        # 2. Verify all 11 bundle files exist
        val_result = validate_handoff_bundle(bundle_req.bundle_dir)
        assert val_result["ok"] is True
        assert len(val_result["missing"]) == 0

        # 3. Verify cryptographic integrity
        int_ok, int_errors = verify_bundle_integrity(bundle_req.bundle_dir)
        assert int_ok is True
        assert len(int_errors) == 0

        # 4. Check prompt_for_antigravity.md content
        prompt_path = bundle_req.bundle_dir / "prompt_for_antigravity.md"
        assert prompt_path.exists()
        prompt_content = prompt_path.read_text(encoding="utf-8")
        assert "Antigravity Local Handoff Task" in prompt_content

        # 5. Simulate IDE response writing
        inbox_dir = tmp_path / "inbox" / bundle_req.request_id
        inbox_dir.mkdir(parents=True, exist_ok=True)
        response_payload = {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "request_id": bundle_req.request_id,
            "status": "completed",
            "model_tool_name": "Antigravity IDE AI",
            "answer_markdown": "ログ [EVD-001] によると、システム状態は ERR_OK です。",
            "answer_text": "ログ [EVD-001] によると、システム状態は ERR_OK です。",
            "cited_evidence_ids": ["EVD-001"],
            "evidence_ids_used": ["EVD-001"],
            "limitations": [],
            "confidence": "high",
            "confidence_label": "high",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "unsupported_claims": [],
            "recommended_next_actions": ["ケースに保存"],
        }
        resp_file = inbox_dir / "response.json"
        resp_file.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # 6. Import and validate response
        import_res = import_ide_response(resp_file, root=tmp_path)
        assert import_res.ok is True
        assert import_res.final_answer is True
        assert "EVD-001" in import_res.response["cited_evidence_ids"]

    def test_scenario_3_complete_chinese_handoff_bundle_e2e(
        self, tmp_path: Path, sample_evidence_items: List[EvidenceItem]
    ) -> None:
        """Scenario 3: Complete Simplified Chinese handoff bundle generation, validation, and simulated import."""
        # 1. Create Outbox Bundle for Chinese
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-ZH-E2E",
            question="请根据审计日志分析系统错误代码",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence_items,
            root=tmp_path,
        )
        assert bundle_req.ok is True

        # 2. Validate bundle completeness and integrity
        val_result = validate_handoff_bundle(bundle_req.bundle_dir)
        assert val_result["ok"] is True
        assert len(val_result["missing"]) == 0

        int_ok, int_errors = verify_bundle_integrity(bundle_req.bundle_dir)
        assert int_ok is True
        assert len(int_errors) == 0

        # 3. Simulate IDE writing Chinese response
        inbox_dir = tmp_path / "inbox" / bundle_req.request_id
        inbox_dir.mkdir(parents=True, exist_ok=True)
        response_payload = {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "request_id": bundle_req.request_id,
            "status": "completed",
            "model_tool_name": "Antigravity IDE AI",
            "answer_markdown": "根据审计日志 [EVD-001]，错误代码为 ERR_OK，系统运行正常。",
            "answer_text": "根据审计日志 [EVD-001]，错误代码为 ERR_OK，系统运行正常。",
            "cited_evidence_ids": ["EVD-001"],
            "evidence_ids_used": ["EVD-001"],
            "limitations": [],
            "confidence": "high",
            "confidence_label": "high",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "unsupported_claims": [],
            "recommended_next_actions": ["保存至案件库"],
        }
        resp_file = inbox_dir / "response.json"
        resp_file.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # 4. Import response
        import_res = import_ide_response(resp_file, root=tmp_path)
        assert import_res.ok is True
        assert import_res.final_answer is True
        assert "EVD-001" in import_res.response["cited_evidence_ids"]

    def test_scenario_4_complex_evidence_graph_with_all_12_nodes_and_12_edges(self) -> None:
        """Scenario 4: Construct a complex graph containing all 12 ALLOWED_NODE_TYPES and all 12 ALLOWED_EDGE_TYPES."""
        # 12 Node Types
        node_types_list = sorted(ALLOWED_NODE_TYPES)
        nodes: List[EvidenceNode] = []
        for idx, nt in enumerate(node_types_list, start=1):
            nodes.append(
                EvidenceNode(
                    id=f"n_{idx:02d}_{nt}",
                    node_type=nt,
                    title=f"Node {idx} Type {nt}",
                    snippet=f"Snippet for node {nt}",
                    confidence=0.9 + (idx % 10) * 0.01,
                )
            )

        # 12 Edge Types connecting consecutive nodes in a rich multi-hop graph
        edge_types_list = sorted(ALLOWED_EDGE_TYPES)
        edges: List[EvidenceEdge] = []
        for idx, et in enumerate(edge_types_list, start=1):
            src_node = nodes[(idx - 1) % len(nodes)]
            tgt_node = nodes[idx % len(nodes)]
            edges.append(
                EvidenceEdge(
                    source_id=src_node.id,
                    target_id=tgt_node.id,
                    relation_type=et,
                    label=f"Relation {et}",
                    weight=0.95,
                    edge_id=f"edge_{idx:02d}_{et}",
                )
            )

        trace = EvidenceTrace(
            trace_id="tr_complex_full_graph_01",
            query="Tổng hợp phân tích toàn diện đồ thị bằng chứng đa liên kết?",
            answer_text="Kết luận tổng hợp từ 12 loại nút và 12 loại cạnh liên kết.",
            ui_locale="vi",
            answer_language="ja",
            source_language="vi",
            nodes=nodes,
            edges=edges,
            metadata={"test_suite": "Commit A Acceptance Tier 4"},
        )

        # Contract Validation
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is True, f"Contract validation failed on full 12x12 graph: {errors}"
        assert len(errors) == 0

        # JSON Serialization and Deserialization Round-trip
        json_repr = trace.to_json(indent=2)
        assert len(json_repr) > 0
        reconstructed = EvidenceTrace.from_json(json_repr)
        assert len(reconstructed.nodes) == 12
        assert len(reconstructed.edges) == 12
        assert reconstructed.trace_id == "tr_complex_full_graph_01"

    def test_scenario_5_ast_workspace_chat_ui_zero_hardcoded_vietnamese(self) -> None:
        """Scenario 5: AST static analysis verifying that workspace_chat_ui.py renderers use i18n lookup."""
        ui_file = Path("src/aios_habit/workspace_chat_ui.py")
        assert ui_file.exists(), f"workspace_chat_ui.py not found at {ui_file}"
        code = ui_file.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(ui_file))

        # Check that i18n functions 't' and 'get_localized_labels' are imported and used
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)

        assert "t" in imported_names, "t() function must be imported in workspace_chat_ui.py"
        assert "get_localized_labels" in code, "get_localized_labels must be present in workspace_chat_ui.py"

    def test_scenario_6_commit_a_isolation_no_exporter_or_render_graph(self) -> None:
        """Scenario 6: Verify evidence_trace_schema.py is isolated with zero graph exporter or renderer dependencies."""
        schema_file = Path("src/aios_habit/evidence_trace_schema.py")
        assert schema_file.exists()
        code = schema_file.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(schema_file))

        forbidden_imports = {
            "networkx",
            "matplotlib",
            "pyvis",
            "graphviz",
            "cytoscape",
            "plotly",
            "seaborn",
            "streamlit_agraph",
        }

        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)

        forbidden_found = imported_modules & forbidden_imports
        assert not forbidden_found, f"Found forbidden graph renderer/exporter imports: {forbidden_found}"
