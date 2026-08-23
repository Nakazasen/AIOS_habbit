# -*- coding: utf-8 -*-
"""Empirical Challenger Final Verification & Stress Test Suite for Commit A.

Authored by challenger_final_1 to stress-test:
1. Multilingual Handoff Bundles & Verbatim Citation Preservation (R1):
   - Obscure/custom locales, case variants, multiple citations, complex file paths with spaces and symbols,
     multi-line error codes, long source snippets.
   - Prompt instructions strictly forbidding translating citations and identifiers across vi, ja, zh-CN.
2. Evidence Trace Schema Strict Type Validation (R3):
   - Fuzzing EvidenceTraceContract.validate_trace with 12 allowed node types, 12 allowed edge types,
     and adversarial non-allowlisted inputs (integers, booleans, None, whitespace, SQL injection, unicode chars).
3. Hygiene & Isolation Checks (R4 & R3).
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from aios_habit.case_models import EvidenceItem
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_1_0_0,
    SCHEMA_VERSION_V1,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_ai_language_instruction,
    normalize_locale,
    t,
)
from aios_habit.ide_handoff_bridge import (
    HANDOFF_ROOT,
    RESPONSE_SCHEMA_VERSION,
    build_full_bundle_request,
    build_ide_prompt_markdown,
    validate_handoff_bundle,
    verify_bundle_integrity,
    write_ide_handoff_bundle,
)


# ============================================================================
# R1: Multilingual Handoff Bundles & Verbatim Citation Preservation
# ============================================================================

class TestMultilingualHandoffAdversarial:
    """Stress test write_ide_handoff_bundle and build_ide_prompt_markdown."""

    @pytest.mark.parametrize(
        "locale_input,expected_norm,expected_keyword",
        [
            ("vi", "vi", "Tiếng Việt"),
            ("vi-VN", "vi", "Tiếng Việt"),
            ("VIETNAMESE", "vi", "Tiếng Việt"),
            ("ja", "ja", "日本語"),
            ("ja-JP", "ja", "日本語"),
            ("JAPANESE", "ja", "日本語"),
            ("zh", "zh-CN", "简体中文"),
            ("zh-CN", "zh-CN", "简体中文"),
            ("zh_cn", "zh-CN", "简体中文"),
            ("zh-Hans", "zh-CN", "简体中文"),
            ("zh-Hans-CN", "zh-CN", "简体中文"),
            ("zh-SG", "zh-CN", "简体中文"),
            ("chinese", "zh-CN", "简体中文"),
            # Obscure and fallback cases
            ("fr-FR", "vi", "Tiếng Việt"),
            ("de", "vi", "Tiếng Việt"),
            ("es-ES", "vi", "Tiếng Việt"),
            ("custom_locale_999", "vi", "Tiếng Việt"),
            ("", "vi", "Tiếng Việt"),
            ("   ", "vi", "Tiếng Việt"),
            (None, "vi", "Tiếng Việt"),
            (12345, "vi", "Tiếng Việt"),
        ],
    )
    def test_handoff_bundle_locale_propagation_and_fallback(
        self, tmp_path: Path, locale_input: Any, expected_norm: str, expected_keyword: str
    ) -> None:
        """Verify write_ide_handoff_bundle correctly normalizes locales in manifest and prompt."""
        item = EvidenceItem(
            evidence_id="EVD-001",
            case_id="CASE-LOCALE-01",
            source_type="plain_text",
            source_path="logs/audit.log",
            title="Audit Log",
            extracted_text="[1] System state: NORMAL. Error: NONE.",
            privacy_level="local_only",
        )
        bundle_req = write_ide_handoff_bundle(
            case_id="CASE-LOCALE-01",
            question="Trạng thái hệ thống thế nào?",
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            answer_language=str(locale_input) if locale_input is not None else "vi",
        )
        assert bundle_req.ok is True

        manifest = json.loads((bundle_req.bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["answer_language"] == expected_norm

        prompt_md = (bundle_req.bundle_dir / "prompt_for_antigravity.md").read_text(encoding="utf-8")
        assert expected_keyword in prompt_md

    def test_verbatim_citation_and_path_preservation_complex_payload(self, tmp_path: Path) -> None:
        """Stress test handoff bundle with spaces in paths, multi-line error traces, and multiple citations."""
        complex_snippet = (
            "Traceback (most recent call last):\n"
            "  File \"/opt/aios apps/server module.py\", line 102, in handle_request\n"
            "    raise ConnectionResetError(\"ERR_SOCKET_RESET_0x80070005: [E1] Connection lost\")\n"
            "Ref citations: [1], [E1], [E2], EVD-999, CITATION_ALPHA_01\n"
            "Path with spaces & unicode: C:\\Users\\Admin\\Documents\\Báo cáo kiểm toán 2026.xlsx\n"
            "Japanese note: サーバーエラー発生 (ERR_CODE: 0x99)\n"
            "Chinese note: 数据库连接超时 (ERR_DB_TIMEOUT)\n"
        )
        item1 = EvidenceItem(
            evidence_id="EVD-999",
            case_id="CASE-COMPLEX-01",
            source_type="log",
            source_path="D:/Sandbox/data files/audit trace 2026.log",
            title="Audit Trace Log 2026 (日越中監査ログ)",
            extracted_text=complex_snippet,
            privacy_level="local_only",
        )
        item2 = EvidenceItem(
            evidence_id="CITATION_ALPHA_01",
            case_id="CASE-COMPLEX-01",
            source_type="pdf",
            source_path="D:/Sandbox/docs/Q3 Operational Guide.pdf",
            title="Q3 Operational Guide PDF",
            extracted_text="[E2] Procedure for recovering from ERR_SOCKET_RESET_0x80070005.",
            privacy_level="cloud_allowed",
        )

        for lang in ("vi", "ja", "zh-CN"):
            bundle_req = write_ide_handoff_bundle(
                case_id="CASE-COMPLEX-01",
                question="Phân tích mã lỗi và phương án khắc phục?",
                bundle_scope="active_case_all",
                evidence_items=[item1, item2],
                root=tmp_path / f"bundle_{lang}",
                answer_language=lang,
            )
            assert bundle_req.ok is True

            # 1. Manifest verification
            manifest_file = bundle_req.bundle_dir / "manifest.json"
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            assert manifest["answer_language"] == lang
            assert "EVD-999" in manifest["allowed_source_ids"]
            assert "CITATION_ALPHA_01" in manifest["allowed_source_ids"]

            # 2. Evidence JSONL verbatim check
            jsonl_file = bundle_req.bundle_dir / "evidence_full.jsonl"
            jsonl_text = jsonl_file.read_text(encoding="utf-8")
            assert "ERR_SOCKET_RESET_0x80070005" in jsonl_text
            assert "Báo cáo kiểm toán 2026.xlsx" in jsonl_text
            assert "日越中監査ログ" in jsonl_text
            assert "\\u" not in jsonl_text  # Anti-mojibake

            # 3. Evidence Markdown verbatim check
            md_file = bundle_req.bundle_dir / "evidence_full.md"
            md_text = md_file.read_text(encoding="utf-8")
            assert "ERR_SOCKET_RESET_0x80070005" in md_text
            assert "[E1]" in md_text
            assert "[E2]" in md_text

            # 4. Prompt Markdown verbatim rule check
            prompt_file = bundle_req.bundle_dir / "prompt_for_antigravity.md"
            prompt_text = prompt_file.read_text(encoding="utf-8")
            assert "[1]" in prompt_text
            assert "[E1]" in prompt_text
            assert "document.pdf" in prompt_text
            if lang == "ja":
                assert "翻訳せず、原文のまま100%保持してください" in prompt_text
            elif lang == "zh-CN":
                assert "严禁翻译或篡改任何标识符和证据引用" in prompt_text
            elif lang == "vi":
                assert "Giữ nguyên vẹn 100% tất cả các mã trích dẫn" in prompt_text

            # 5. Integrity check
            int_ok, int_errors = verify_bundle_integrity(bundle_req.bundle_dir)
            assert int_ok is True
            assert len(int_errors) == 0


# ============================================================================
# R3: Evidence Trace Schema Strict Type Validation Enforcement
# ============================================================================

class TestEvidenceTraceSchemaAdversarialFuzzing:
    """Adversarial fuzzing and strict allow-list validation on EvidenceTraceContract."""

    def test_all_12_node_types_accepted(self) -> None:
        """Verify all 12 ALLOWED_NODE_TYPES are strictly accepted."""
        assert len(ALLOWED_NODE_TYPES) == 12
        for nt in sorted(ALLOWED_NODE_TYPES):
            node = EvidenceNode(id=f"node_{nt}", node_type=nt, title=f"Node {nt}")
            trace = EvidenceTrace(
                trace_id="tr_valid_nt",
                schema_version=SCHEMA_VERSION_1_0_0,
                nodes=[node],
                edges=[],
            )
            valid, errors = EvidenceTraceContract.validate(trace)
            assert valid is True, f"Failed on valid node_type '{nt}': {errors}"

    def test_all_12_edge_types_accepted(self) -> None:
        """Verify all 12 ALLOWED_EDGE_TYPES are strictly accepted."""
        assert len(ALLOWED_EDGE_TYPES) == 12
        n1 = EvidenceNode(id="n1", node_type="claim")
        n2 = EvidenceNode(id="n2", node_type="evidence")
        for et in sorted(ALLOWED_EDGE_TYPES):
            edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type=et)
            trace = EvidenceTrace(
                trace_id="tr_valid_et",
                schema_version=SCHEMA_VERSION_1_0_0,
                nodes=[n1, n2],
                edges=[edge],
            )
            valid, errors = EvidenceTraceContract.validate(trace)
            assert valid is True, f"Failed on valid relation_type '{et}': {errors}"

    @pytest.mark.parametrize(
        "invalid_node_type",
        [
            "unsupported_type",
            "custom_node",
            "entity",
            "fact",
            "hypothesis",
            "CLAIM",  # uppercase
            "Evidence",  # title case
            "source ",  # trailing space
            " source",  # leading space
            "source\u200b",  # zero width space
            "source\x00",  # null byte
            "' OR '1'='1",  # SQL injection
            "<script>alert(1)</script>",  # XSS
            "DROP TABLE nodes;--",
            12345,  # int
            True,  # bool
            False,
            3.14159,
        ],
    )
    def test_fuzz_invalid_node_types_rejected(self, invalid_node_type: Any) -> None:
        """Verify EvidenceTraceContract deterministically rejects non-allowlisted node types."""
        node = EvidenceNode(id="n_bad", node_type=invalid_node_type, title="Bad Node")  # type: ignore
        trace = EvidenceTrace(
            trace_id="tr_fuzz_node",
            schema_version=SCHEMA_VERSION_1_0_0,
            nodes=[node],
            edges=[],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False, f"Expected rejection for invalid node_type: {invalid_node_type!r}"
        assert any("node_type" in e.lower() for e in errors)

    @pytest.mark.parametrize(
        "invalid_edge_type",
        [
            "unsupported_relation",
            "related_to",
            "causes",
            "connects_to",
            "CITES",  # uppercase
            "Supports",  # title case
            "cites ",  # trailing space
            " cites",  # leading space
            "cites\u200b",  # zero width space
            "' OR 1=1",  # SQL injection
            "<img src=x onerror=alert(1)>",  # XSS
            "DROP TABLE edges;--",
            99999,  # int
            True,  # bool
            False,
            2.718,
        ],
    )
    def test_fuzz_invalid_edge_types_rejected(self, invalid_edge_type: Any) -> None:
        """Verify EvidenceTraceContract deterministically rejects non-allowlisted edge types."""
        n1 = EvidenceNode(id="n1", node_type="claim")
        n2 = EvidenceNode(id="n2", node_type="source")
        edge = EvidenceEdge(source_id="n1", target_id="n2", relation_type=invalid_edge_type)  # type: ignore
        trace = EvidenceTrace(
            trace_id="tr_fuzz_edge",
            schema_version=SCHEMA_VERSION_1_0_0,
            nodes=[n1, n2],
            edges=[edge],
        )
        valid, errors = EvidenceTraceContract.validate(trace)
        assert valid is False, f"Expected rejection for invalid relation_type: {invalid_edge_type!r}"
        assert any("relation_type" in e.lower() or "edge" in e.lower() for e in errors)

    def test_schema_isolation_no_exporter_code(self) -> None:
        """Verify evidence_trace_schema.py contains zero graph exporter or visualization libraries."""
        schema_file = Path("src/aios_habit/evidence_trace_schema.py")
        code = schema_file.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(schema_file))

        disallowed_names = {
            "networkx", "matplotlib", "pyvis", "graphviz", "cytoscape",
            "plotly", "seaborn", "streamlit_agraph", "pydot",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.lower())
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.lower())

        found_disallowed = imported & disallowed_names
        assert not found_disallowed, f"Disallowed graph rendering imports found: {found_disallowed}"
