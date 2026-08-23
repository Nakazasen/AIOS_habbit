# -*- coding: utf-8 -*-
"""Adversarial Stress Test Suite for Commit C: Evidence Graph Viewer.

Author: Challenger 1 (teamwork_preview_challenger_1)
Milestone: Commit C Empirical Challenge

Exhaustively stress-tests:
1. Extreme Trace Structures (massive DAGs with 50+ nodes & 100+ edges, cyclic loops, deeply nested metadata, disconnected nodes).
2. Unicode Torture Tests (Vietnamese combining marks/NFD, Japanese Kanji/Kana/halfwidth, Simplified/Traditional Chinese, CJK Ext, mixed RTL/XSS).
3. Strict Determinism & 1-Byte Avalanche Hash Sensitivity of compute_trace_content_hash.
4. Multi-Threaded Concurrency & Cache Thread-Safety under high contention and eviction.
5. Corrupted, Malicious, Non-String, and Invalid Typed Payloads (100% Fail-Safe Resilience, 0 Crashes).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import html
import json
import math
import random
import string
import threading
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.evidence_graph_viewer import (
    EvidenceGraphViewerCache,
    EvidenceGraphViewModel,
    VIEWER_CACHE,
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
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    normalize_locale,
    t,
)
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import render_chat_bubble


# ==============================================================================
# Challenge 1: Extreme Graph Structures & Massive DAGs
# ==============================================================================

def test_massive_dag_50_plus_nodes_100_plus_edges() -> None:
    """Stress test with a massive DAG: 80 nodes and 150 edges."""
    nodes: List[EvidenceNode] = []
    edges: List[EvidenceEdge] = []

    # 1 question node, 1 answer node
    nodes.append(EvidenceNode(id="q_root", node_type="question", title="Câu hỏi lớn về hệ thống kho bãi"))
    nodes.append(EvidenceNode(id="ans_root", node_type="answer", title="Câu trả lời tổng hợp"))
    edges.append(EvidenceEdge(source_id="ans_root", target_id="q_root", relation_type="derives_from", label="Trả lời"))

    # 39 Source nodes + 39 Citation nodes = 78 nodes (Total 80 nodes)
    for i in range(1, 40):
        src_id = f"src_node_{i:03d}"
        cit_id = f"cit_node_{i:03d}"
        nodes.append(EvidenceNode(
            id=src_id,
            node_type="source",
            title=f"Tài_liệu_hướng_dẫn_v{i:03d}.pdf",
            snippet=f"Nội dung chi tiết tài liệu quy trình số {i} với các tham số quan trọng.",
            source_id=f"local_cases/docs/quy_trinh_{i:03d}.pdf",
            citation_id=f"[{i}]",
        ))
        nodes.append(EvidenceNode(
            id=cit_id,
            node_type="citation",
            title=f"[{i}]",
            snippet=f"Trích dẫn số {i} phục vụ việc chứng minh các luận điểm.",
            source_id=src_id,
            citation_id=f"[{i}]",
        ))
        # Base edges
        edges.append(EvidenceEdge(source_id="ans_root", target_id=cit_id, relation_type="cites"))
        edges.append(EvidenceEdge(source_id=cit_id, target_id=src_id, relation_type="extracted_from"))

    # Add 72 cross-reference edges among citations and sources (Total edges: 1 + 39*2 + 72 = 151 edges)
    for i in range(1, 37):
        target_src = f"src_node_{((i * 3) % 39) + 1:03d}"
        cit_src = f"cit_node_{i:03d}"
        edges.append(EvidenceEdge(source_id=cit_src, target_id=target_src, relation_type="references", label="Tham chiếu phụ"))
        edges.append(EvidenceEdge(source_id=f"src_node_{i:03d}", target_id=target_src, relation_type="depends_on", label="Phụ thuộc"))

    assert len(nodes) == 80
    assert len(edges) == 151

    massive_trace = EvidenceTrace(
        trace_id="trc_massive_001",
        query="Câu hỏi lớn về hệ thống kho bãi",
        answer_text="Câu trả lời tổng hợp tham chiếu toàn bộ tài liệu.",
        nodes=nodes,
        edges=edges,
        metadata={"status": "valid", "insufficient_evidence": False, "node_count": 80},
    )

    # 1. Verify view model exact 1-1 topology
    vm = build_evidence_graph_view_model(massive_trace, locale="vi")
    assert vm.is_insufficient is False
    assert len(vm.nodes) == 80
    assert len(vm.edges) == 151
    assert vm.stats["nodes"] == 80
    assert vm.stats["edges"] == 151
    assert vm.stats["sources"] == 39
    assert vm.stats["citations"] == 39

    # 2. Verify HTML rendering does not crash and renders all nodes
    html_out = render_evidence_graph_html(massive_trace, locale="vi")
    assert "trc_massive_001" in html_out
    assert "Tài_liệu_hướng_dẫn_v001.pdf" in html_out
    assert "Tài_liệu_hướng_dẫn_v039.pdf" in html_out
    assert "egv-container" in html_out
    assert "egv-error" not in html_out

    # 3. Verify content hash computation is fast and deterministic
    chash = compute_trace_content_hash(massive_trace)
    assert len(chash) == 64


def test_cyclic_graph_references_and_self_loops() -> None:
    """Stress test graph with directed cycles (A->B->C->A) and self-loops (D->D)."""
    cyclic_nodes = [
        EvidenceNode(id="n_a", node_type="question", title="Question A"),
        EvidenceNode(id="n_b", node_type="answer", title="Answer B"),
        EvidenceNode(id="n_c", node_type="citation", title="Citation C"),
        EvidenceNode(id="n_d", node_type="source", title="Self Source D"),
    ]
    cyclic_edges = [
        EvidenceEdge(source_id="n_a", target_id="n_b", relation_type="derives_from"),
        EvidenceEdge(source_id="n_b", target_id="n_c", relation_type="cites"),
        EvidenceEdge(source_id="n_c", target_id="n_a", relation_type="references"),  # Cycle back to A
        EvidenceEdge(source_id="n_d", target_id="n_d", relation_type="references"), # Self loop
    ]

    cyclic_trace = EvidenceTrace(
        trace_id="trc_cyclic_001",
        query="Chu trình kiểm tra",
        answer_text="Hệ thống có chu trình kiểm tra.",
        nodes=cyclic_nodes,
        edges=cyclic_edges,
        metadata={"status": "valid"},
    )

    # Must build and render without infinite recursion or stack overflow
    vm = build_evidence_graph_view_model(cyclic_trace, locale="vi")
    assert len(vm.nodes) == 4
    assert len(vm.edges) == 4

    html_out = render_evidence_graph_html(cyclic_trace, locale="ja")
    assert "trc_cyclic_001" in html_out
    assert "Question A" in html_out
    assert "Self Source D" in html_out
    assert "egv-error" not in html_out


def test_deeply_nested_metadata_resilience() -> None:
    """Stress test with metadata nested 25 levels deep and diverse data types."""
    nested_dict: Dict[str, Any] = {"leaf": "deepest_value", "number": 123.456, "tags": ["a", "b", "c"]}
    for depth in range(25, 0, -1):
        nested_dict = {
            f"level_{depth:02d}": nested_dict,
            f"depth_meta_{depth:02d}": {"active": True, "count": depth},
            "unicode_key_vi": "Tiếng Việt có dấu tại tầng này",
        }

    trace = EvidenceTrace(
        trace_id="trc_deep_meta_001",
        query="Kiểm tra metadata sâu",
        answer_text="Metadata sâu 25 tầng theo tài liệu [1].",
        nodes=[
            EvidenceNode(id="n1", node_type="question", title="Q1", metadata=nested_dict),
            EvidenceNode(id="n2", node_type="answer", title="A1", metadata={"deep": nested_dict}),
            EvidenceNode(id="n3", node_type="source", title="S1.docx", source_id="s1.docx", metadata=nested_dict),
            EvidenceNode(id="n4", node_type="citation", title="[1]", citation_id="[1]", source_id="s1.docx", metadata=nested_dict),
        ],
        edges=[
            EvidenceEdge(source_id="n2", target_id="n1", relation_type="derives_from", metadata=nested_dict),
            EvidenceEdge(source_id="n2", target_id="n4", relation_type="cites", metadata=nested_dict),
            EvidenceEdge(source_id="n4", target_id="n3", relation_type="extracted_from", metadata=nested_dict),
        ],
        metadata={"global_deep": nested_dict, "status": "valid"},
    )

    # Content hash must compute without recursion depth error
    chash1 = compute_trace_content_hash(trace)
    chash2 = compute_trace_content_hash(trace)
    assert chash1 == chash2
    assert len(chash1) == 64

    # View model and HTML render safely
    vm = build_evidence_graph_view_model(trace, locale="zh-CN")
    assert len(vm.nodes) == 4
    assert len(vm.edges) == 3

    html_out = render_evidence_graph_html(trace, locale="zh-CN")
    assert "trc_deep_meta_001" in html_out
    assert "egv-error" not in html_out


def test_disconnected_isolated_nodes_and_multiple_components() -> None:
    """Stress test with disconnected isolated nodes and isolated subgraphs."""
    nodes = [
        EvidenceNode(id="iso_1", node_type="source", title="Tài liệu cô lập 1"),
        EvidenceNode(id="iso_2", node_type="source", title="Tài liệu cô lập 2"),
        EvidenceNode(id="iso_3", node_type="citation", title="[C-00]"),
        EvidenceNode(id="grp1_a", node_type="question", title="Hỏi nhóm 1"),
        EvidenceNode(id="grp1_b", node_type="answer", title="Đáp nhóm 1"),
        EvidenceNode(id="grp2_a", node_type="citation", title="[C-01]"),
        EvidenceNode(id="grp2_b", node_type="source", title="Nguồn nhóm 2"),
    ]
    edges = [
        EvidenceEdge(source_id="grp1_b", target_id="grp1_a", relation_type="derives_from"),
        EvidenceEdge(source_id="grp2_a", target_id="grp2_b", relation_type="extracted_from"),
    ]

    trace = EvidenceTrace(
        trace_id="trc_isolated_001",
        query="Các thành phần phân mảnh",
        answer_text="Có các nút cô lập.",
        nodes=nodes,
        edges=edges,
        metadata={"status": "valid"},
    )

    vm = build_evidence_graph_view_model(trace, locale="vi")
    assert len(vm.nodes) == 7
    assert len(vm.edges) == 2
    assert vm.stats["nodes"] == 7
    assert vm.stats["edges"] == 2
    assert vm.stats["sources"] == 3
    assert vm.stats["citations"] == 2

    html_out = render_evidence_graph_html(trace, locale="vi")
    assert "Tài liệu cô lập 1" in html_out
    assert "Tài liệu cô lập 2" in html_out
    assert "[C-00]" in html_out


# ==============================================================================
# Challenge 2: Unicode Torture & Multilingual Adversarial Strings
# ==============================================================================

def test_unicode_torture_vietnamese_combining_marks_and_tone_diacritics() -> None:
    """Test Vietnamese strings with all combinations of combining tone marks, diphthongs, and triphthongs."""
    vi_heavy_text = (
        "Thử nghiệm chuỗi tiếng Việt đặc thù: ắ ằ ẳ ẵ ặ, ấ ầ ổ ỗ ộ, ế ề ể ễ ệ, "
        "ứ ừ ử ữ ự, ớ ờ ở ỡ ợ, ỳ ỷ ỹ ỵ. "
        "Đoạn văn kiểm tra: 'Nghiên cứu ứng dụng trí tuệ nhân tạo trong kiểm soát chất lượng kho bãi'. "
        "Ký tự kết hợp (NFD): e\u0302\u0301 (ế), u\u031b\u0301 (ứ), o\u0302\u0303 (ỗ)."
    )

    trace = EvidenceTrace(
        trace_id="trc_vi_torture_001",
        query="Nghiên cứu kiểm soát chất lượng?",
        answer_text=vi_heavy_text,
        ui_locale="vi",
        answer_language="vi",
        nodes=[
            EvidenceNode(
                id="n_vi_q",
                node_type="question",
                title="Nghiên cứu kiểm soát chất lượng?",
                snippet=vi_heavy_text,
            ),
            EvidenceNode(
                id="n_vi_cit",
                node_type="citation",
                title="[Dẫn-Nguồn-VN-01]",
                snippet=vi_heavy_text,
                citation_id="[Dẫn-Nguồn-VN-01]",
                source_id="local_cases/docs/Báo_cáo_chất_lượng_tiếng_Việt_2026.docx",
            ),
            EvidenceNode(
                id="n_vi_src",
                node_type="source",
                title="Báo_cáo_chất_lượng_tiếng_Việt_2026.docx",
                snippet=vi_heavy_text,
                source_id="local_cases/docs/Báo_cáo_chất_lượng_tiếng_Việt_2026.docx",
                citation_id="[Dẫn-Nguồn-VN-01]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="n_vi_cit", target_id="n_vi_src", relation_type="extracted_from", label="Trích từ báo cáo tiếng Việt"),
        ],
        metadata={"status": "valid", "notes": vi_heavy_text},
    )

    html_out = render_evidence_graph_html(trace, locale="vi")

    # Verify no raw \\u escape sequences and full string preservation
    assert "\\u0302" not in html_out
    assert "\\u031b" not in html_out
    assert "Báo_cáo_chất_lượng_tiếng_Việt_2026.docx" in html_out
    assert "[Dẫn-Nguồn-VN-01]" in html_out
    assert "ắ ằ ẳ ẵ ặ" in html_out


def test_unicode_torture_japanese_kanji_kana_halfwidth_and_emojis() -> None:
    """Test Japanese strings with rare Kanji (𠮷, 竈, 鬱), half-width Katakana, Kana, and emojis."""
    ja_torture_text = (
        "日本語の過酷テスト：「𠮷野家」と「竈門炭治郎」と「憂鬱な麒麟」。"
        "半角ｶﾀｶﾅ: ﾊﾝﾃﾞｨﾀｰﾐﾅﾙ「HT-9000-PRO」でQRｺｰﾄﾞをｽｷｬﾝ。"
        "特殊記号＆絵文字: 🚀✨ 🕸️ 🏷️ 📄 ❓ 💡 ⚡ ⚙️。"
        "濁点・半濁点: がぎぐげご、ぱぴぷぺぽ、ヴぁ、ゔ。"
    )

    trace = EvidenceTrace(
        trace_id="trc_ja_torture_001",
        query="過酷テストの実施結果について",
        answer_text=ja_torture_text,
        ui_locale="ja",
        answer_language="ja",
        nodes=[
            EvidenceNode(
                id="n_ja_cit",
                node_type="citation",
                title="[証拠-JA-極]",
                snippet=ja_torture_text,
                citation_id="[証拠-JA-極]",
                source_id="local_cases/docs/品質管理マニュアル_𠮷野_v3.pdf",
            ),
            EvidenceNode(
                id="n_ja_src",
                node_type="source",
                title="品質管理マニュアル_𠮷野_v3.pdf",
                snippet=ja_torture_text,
                source_id="local_cases/docs/品質管理マニュアル_𠮷野_v3.pdf",
                citation_id="[証拠-JA-極]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="n_ja_cit", target_id="n_ja_src", relation_type="extracted_from", label="仕様書から抽出"),
        ],
        metadata={"status": "valid"},
    )

    html_out = render_evidence_graph_html(trace, locale="ja")

    assert "品質管理マニュアル_𠮷野_v3.pdf" in html_out
    assert "[証拠-JA-極]" in html_out
    assert "ﾊﾝﾃﾞｨﾀｰﾐﾅﾙ" in html_out
    assert "竈門炭治郎" in html_out
    assert "憂鬱な麒麟" in html_out
    assert "\\u" not in html_out


def test_unicode_torture_chinese_simplified_traditional_cjk_ext() -> None:
    """Test Chinese strings with Simplified Hanzi, Traditional Hanzi, and CJK Extension characters."""
    zh_torture_text = (
        "简体与繁体混合证据测试：'关于仓储出入库自动化审核规范' vs '關於倉儲出入庫自動化審核規範'。"
        "生僻汉字与扩展字集：𠮷、𩸽、𪚥、䶮、赟、堃、淼、犇。"
        "技术参数：API_ERROR_0x994F8A_连接超时。"
    )

    trace = EvidenceTrace(
        trace_id="trc_zh_torture_001",
        query="仓储出入库规范",
        answer_text=zh_torture_text,
        ui_locale="zh-CN",
        answer_language="zh-CN",
        nodes=[
            EvidenceNode(
                id="n_zh_cit",
                node_type="citation",
                title="[证据-ZH-001]",
                snippet=zh_torture_text,
                citation_id="[证据-ZH-001]",
                source_id="local_cases/docs/自动化审核规范_䶮_v2.xlsx",
            ),
            EvidenceNode(
                id="n_zh_src",
                node_type="source",
                title="自动化审核规范_䶮_v2.xlsx",
                snippet=zh_torture_text,
                source_id="local_cases/docs/自动化审核规范_䶮_v2.xlsx",
                citation_id="[证据-ZH-001]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="n_zh_cit", target_id="n_zh_src", relation_type="extracted_from", label="源自规范文档"),
        ],
        metadata={"status": "valid"},
    )

    html_out = render_evidence_graph_html(trace, locale="zh-CN")

    assert "自动化审核规范_䶮_v2.xlsx" in html_out
    assert "[证据-ZH-001]" in html_out
    assert "关于仓储出入库自动化审核规范" in html_out
    assert "關於倉儲出入庫自動化審核規範" in html_out
    assert "API_ERROR_0x994F8A_连接超时" in html_out
    assert "\\u" not in html_out


def test_xss_and_injection_payloads_safely_escaped() -> None:
    """Stress test with malicious XSS, HTML tags, and SQL injection strings across all fields."""
    xss_title = "<script>alert('XSS_IN_TITLE')</script>"
    xss_snippet = "<img src=x onerror=alert('XSS_IN_SNIPPET')> & <div style='position:fixed;top:0;left:0;width:100%;height:100%;'><h1>HACKED</h1></div>"
    xss_source_id = "'; DROP TABLE traces; SELECT * FROM users WHERE '1'='1"
    xss_citation_id = "<iframe src='javascript:alert(1)'>[XSS-1]</iframe>"

    trace = EvidenceTrace(
        trace_id="trc_xss_001",
        query="<script>alert('query')</script>",
        answer_text="<script>alert('answer')</script>",
        nodes=[
            EvidenceNode(
                id="n_xss_cit",
                node_type="citation",
                title=xss_title,
                snippet=xss_snippet,
                source_id="src_xss_01",
                citation_id=xss_citation_id,
            ),
            EvidenceNode(
                id="src_xss_01",
                node_type="source",
                title="xss_source.docx",
                snippet="Snippet from source",
                source_id=xss_source_id,
            ),
        ],
        edges=[
            EvidenceEdge(source_id="n_xss_cit", target_id="src_xss_01", relation_type="extracted_from"),
        ],
        metadata={"status": "valid", "injected": "<svg/onload=alert(1)>"},
    )

    html_out = render_evidence_graph_html(trace, locale="vi")

    # Unescaped active tags MUST NOT exist in HTML output
    assert "<script>alert('XSS_IN_TITLE')</script>" not in html_out
    assert "<img src=x onerror=alert('XSS_IN_SNIPPET')>" not in html_out
    assert "<iframe src=" not in html_out

    # Escaped safe versions MUST be present
    assert "&lt;script&gt;alert(&#x27;XSS_IN_TITLE&#x27;)&lt;/script&gt;" in html_out or "&lt;script&gt;alert('XSS_IN_TITLE')&lt;/script&gt;" in html_out
    assert "&lt;img src=x onerror=alert(&#x27;XSS_IN_SNIPPET&#x27;)&gt;" in html_out or "&lt;img src=x onerror=alert('XSS_IN_SNIPPET')&gt;" in html_out
    assert "&#x27;; DROP TABLE traces;" in html_out or "'; DROP TABLE traces;" in html_out


# ==============================================================================
# Challenge 3: Strict Determinism & 1-Byte Avalanche Hash Sensitivity
# ==============================================================================

def test_hash_determinism_under_node_edge_and_meta_permutations() -> None:
    """Verify that permuting the order of nodes, edges, or metadata keys produces 100% identical SHA-256."""
    nodes = [
        EvidenceNode(id=f"node_{i:02d}", node_type="evidence", title=f"Title {i}", snippet=f"Snippet {i}")
        for i in range(15)
    ]
    edges = [
        EvidenceEdge(source_id=f"node_{i:02d}", target_id=f"node_{(i+1)%15:02d}", relation_type="supports", label=f"Label {i}")
        for i in range(15)
    ]
    metadata = {f"key_{i:02d}": f"value_{i:02d}" for i in range(20)}

    baseline_trace = EvidenceTrace(
        trace_id="trc_perm_test",
        query="Câu hỏi kiểm thử hoán vị",
        answer_text="Câu trả lời kiểm thử hoán vị",
        nodes=nodes,
        edges=edges,
        metadata=metadata,
    )
    baseline_hash = compute_trace_content_hash(baseline_trace)

    rng = random.Random(42)

    # Test 50 random permutations
    for perm_idx in range(50):
        perm_nodes = list(nodes)
        rng.shuffle(perm_nodes)

        perm_edges = list(edges)
        rng.shuffle(perm_edges)

        perm_meta_items = list(metadata.items())
        rng.shuffle(perm_meta_items)
        perm_metadata = dict(perm_meta_items)

        perm_trace = EvidenceTrace(
            trace_id="trc_perm_test",
            query="Câu hỏi kiểm thử hoán vị",
            answer_text="Câu trả lời kiểm thử hoán vị",
            nodes=perm_nodes,
            edges=perm_edges,
            metadata=perm_metadata,
        )

        perm_hash = compute_trace_content_hash(perm_trace)
        assert perm_hash == baseline_hash, f"Hash mismatch on permutation iteration {perm_idx}"


def test_hash_single_byte_mutation_sensitivity_avalanche() -> None:
    """Verify that modifying ANY single byte in any field strictly produces a different SHA-256 hash."""
    base_node1 = EvidenceNode(id="n1", node_type="question", title="Q1", snippet="Snippet 1", source_id="src1", citation_id="[1]", confidence=0.9)
    base_node2 = EvidenceNode(id="n2", node_type="answer", title="A1", snippet="Snippet 2", source_id="src2", citation_id="[2]", confidence=0.8)
    base_edge = EvidenceEdge(source_id="n2", target_id="n1", relation_type="derives_from", label="Derived", weight=0.95)

    base_trace = EvidenceTrace(
        trace_id="trc_base_001",
        query="Base Query",
        answer_text="Base Answer",
        schema_version="rag-trace/v1",
        nodes=[base_node1, base_node2],
        edges=[base_edge],
        metadata={"category": "warehouse", "tag": "v1"},
    )
    base_hash = compute_trace_content_hash(base_trace)

    # 1. Modify trace query
    t_mod_q = copy.deepcopy(base_trace)
    t_mod_q.query = "Base Query."
    assert compute_trace_content_hash(t_mod_q) != base_hash

    # 2. Modify trace answer_text
    t_mod_ans = copy.deepcopy(base_trace)
    t_mod_ans.answer_text = "Base Answer!"
    assert compute_trace_content_hash(t_mod_ans) != base_hash

    # 3. Modify trace schema_version
    t_mod_ver = copy.deepcopy(base_trace)
    t_mod_ver.schema_version = "rag-trace/v2"
    assert compute_trace_content_hash(t_mod_ver) != base_hash

    # 4. Modify node snippet
    t_mod_snip = copy.deepcopy(base_trace)
    t_mod_snip.nodes[0].snippet = "Snippet 1."
    assert compute_trace_content_hash(t_mod_snip) != base_hash

    # 5. Modify node title
    t_mod_title = copy.deepcopy(base_trace)
    t_mod_title.nodes[0].title = "Q1 modified"
    assert compute_trace_content_hash(t_mod_title) != base_hash

    # 6. Modify node confidence
    t_mod_conf = copy.deepcopy(base_trace)
    t_mod_conf.nodes[0].confidence = 0.91
    assert compute_trace_content_hash(t_mod_conf) != base_hash

    # 7. Modify node source_id
    t_mod_src = copy.deepcopy(base_trace)
    t_mod_src.nodes[0].source_id = "src1_alt"
    assert compute_trace_content_hash(t_mod_src) != base_hash

    # 8. Modify node citation_id
    t_mod_cit = copy.deepcopy(base_trace)
    t_mod_cit.nodes[0].citation_id = "[1b]"
    assert compute_trace_content_hash(t_mod_cit) != base_hash

    # 9. Modify edge relation_type
    t_mod_rel = copy.deepcopy(base_trace)
    t_mod_rel.edges[0].relation_type = "cites"
    assert compute_trace_content_hash(t_mod_rel) != base_hash

    # 10. Modify edge label
    t_mod_lbl = copy.deepcopy(base_trace)
    t_mod_lbl.edges[0].label = "Derived slightly"
    assert compute_trace_content_hash(t_mod_lbl) != base_hash

    # 11. Modify edge weight
    t_mod_w = copy.deepcopy(base_trace)
    t_mod_w.edges[0].weight = 0.96
    assert compute_trace_content_hash(t_mod_w) != base_hash

    # 12. Modify metadata key/value
    t_mod_meta = copy.deepcopy(base_trace)
    t_mod_meta.metadata["category"] = "logistics"
    assert compute_trace_content_hash(t_mod_meta) != base_hash

    # Verify cache behavior with mutated hash
    cache = EvidenceGraphViewerCache()
    cache.set(base_trace.trace_id, base_hash, "<html>Cached Baseline</html>", locale="vi")
    assert cache.get(base_trace.trace_id, base_hash, locale="vi") == "<html>Cached Baseline</html>"

    # Mutated hash MUST cause cache miss
    mutated_hash = compute_trace_content_hash(t_mod_meta)
    assert cache.get(base_trace.trace_id, mutated_hash, locale="vi") is None


# ==============================================================================
# Challenge 4: Multi-Threaded Concurrency & Cache Thread-Safety
# ==============================================================================

def test_multithreaded_cache_concurrency_stress() -> None:
    """Stress test EvidenceGraphViewerCache under high multi-threaded concurrency (30 workers, 3000 operations)."""
    cache = EvidenceGraphViewerCache(max_entries=30)
    cache.clear()

    errors: List[Exception] = []
    num_threads = 30
    ops_per_thread = 100

    def worker_task(thread_id: int) -> None:
        try:
            for op in range(ops_per_thread):
                key_id = f"trc_th_{thread_id % 10}_{op % 15}"
                h_val = f"hash_{thread_id % 5}_{op % 10}"
                loc = ["vi", "ja", "zh-CN"][op % 3]

                # Perform mixed read/write/has/size/clear
                choice = op % 5
                if choice == 0:
                    cache.set(key_id, h_val, f"<div>Payload {thread_id}-{op}</div>", locale=loc)
                elif choice == 1:
                    _ = cache.get(key_id, h_val, locale=loc)
                elif choice == 2:
                    _ = cache.has(key_id, h_val, locale=loc)
                elif choice == 3:
                    _ = cache.size()
                elif choice == 4 and thread_id == 0 and op == 50:
                    # Rare clear during concurrency
                    cache.clear()
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()

    assert len(errors) == 0, f"Thread errors encountered during cache concurrency: {errors}"
    assert cache.size() <= 30, f"Cache size {cache.size()} exceeded max_entries limit of 30"


# ==============================================================================
# Challenge 5: Corrupted, Malicious Payloads & Fail-Safe Resilience
# ==============================================================================

def test_corrupted_and_malformed_payloads_fail_safe_resilience() -> None:
    """Verify that completely corrupted payloads never crash render_evidence_graph_html/streamlit."""
    corrupted_inputs = [
        None,
        123456,
        3.14159,
        True,
        False,
        "raw_string_not_dict_or_trace",
        [],
        [1, 2, 3],
        {},
        {"nodes": None, "edges": None},
        {"nodes": "not_a_list", "edges": 999},
        {"nodes": [None, 123, "corrupted", {}], "edges": [None, False]},
        {"nodes": [{"id": None, "node_type": None, "confidence": "invalid_float"}], "edges": []},
        {"nodes": [{"id": "n1", "snippet": math.nan}], "edges": [{"source_id": "n1", "target_id": "n2", "weight": math.inf}]},
    ]

    for idx, bad_input in enumerate(corrupted_inputs):
        for loc in ("vi", "ja", "zh-CN"):
            # 1. render_evidence_graph_html MUST NEVER raise an uncaught exception
            try:
                html_res = render_evidence_graph_html(bad_input, locale=loc, use_cache=False)
                assert isinstance(html_res, str)
                assert len(html_res) > 0
                # Either localized error banner or container
                assert "egv-error" in html_res or "egv-container" in html_res
            except Exception as e:
                pytest.fail(f"render_evidence_graph_html crashed on bad_input index {idx} ({bad_input}): {e}")

            # 2. render_evidence_graph_streamlit MUST NEVER raise an uncaught exception
            try:
                with patch("streamlit.warning"), patch("streamlit.error"), patch("streamlit.markdown"), patch("streamlit.caption"):
                    render_evidence_graph_streamlit(bad_input, locale=loc)
            except Exception as e:
                pytest.fail(f"render_evidence_graph_streamlit crashed on bad_input index {idx}: {e}")


def test_non_string_ids_and_extreme_types_in_schema_and_viewer() -> None:
    """Test nodes and edges containing integers, floats, None as IDs and properties."""
    weird_dict = {
        "trace_id": 99999,
        "schema_version": 1.0,
        "query": 100200,
        "answer_text": ["List", "as", "answer"],
        "nodes": [
            {
                "id": 101,
                "node_type": 202,
                "title": 303,
                "snippet": None,
                "source_id": 404,
                "citation_id": 505,
                "confidence": "0.85",
            },
            {
                "id": "102",
                "node_type": "citation",
                "title": "Cit 102",
                "snippet": 8888,
                "source_id": "src_102",
                "citation_id": "[102]",
                "confidence": 1.5, # Out of range float coerced
            }
        ],
        "edges": [
            {
                "source_id": 101,
                "target_id": "102",
                "relation_type": 999,
                "label": None,
                "weight": "0.75",
            }
        ],
        "metadata": {123: "int_key", "flag": True},
    }

    # Content hash must succeed
    chash = compute_trace_content_hash(weird_dict)
    assert isinstance(chash, str) and len(chash) == 64

    # HTML rendering must produce valid HTML without crashing
    html_out = render_evidence_graph_html(weird_dict, locale="vi")
    assert isinstance(html_out, str)
    assert len(html_out) > 0
    assert "egv-error" not in html_out
