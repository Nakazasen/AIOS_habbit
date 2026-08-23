# -*- coding: utf-8 -*-
"""Comprehensive Automated Test Suite for Commit C: Evidence Graph Viewer Integration.

Validates all Commit C requirements:
1. Multilingual Translation Key Parity (100% parity across vi, ja, zh-CN).
2. Deterministic SHA-256 Content Hashing & Local Caching.
3. Exact 1-to-1 Topology Mapping (zero hallucinated nodes/edges).
4. Insufficient Evidence Guard (no fake graphs rendered).
5. Verbatim Text Preservation & Anti-Mojibake (filenames, snippets, citations, CJK/Vietnamese).
6. Fail-Safe Offline Local Rendering (zero cloud egress, never crash).
7. UI Action Button Visibility in Chat Bubble (visible iff assistant + trace exists).
"""
from __future__ import annotations

import hashlib
import html
import json
import socket
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
    TRANSLATIONS,
    normalize_locale,
    t,
)
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import render_chat_bubble


# ==============================================================================
# Tier 1: i18n Translation Completeness & Key Parity
# ==============================================================================

def test_commit_c_translation_keys_parity_100_percent() -> None:
    """Verify 100% key parity across vi, ja, and zh-CN for all Commit C keys."""
    required_commit_c_keys = [
        "btn_view_evidence_graph",
        "btn_hide_evidence_graph",
        "evidence_graph_insufficient",
        "evidence_graph_insufficient_desc",
        "evidence_graph_render_error",
        "evidence_trace_not_found",
        "evidence_graph_cached_badge",
        "evidence_graph_stats_label",
        "evidence_graph_generating_spinner",
        "evidence_graph_legend",
        "evidence_graph_source_nodes",
        "evidence_graph_citation_nodes",
        "node_type_citation",
        "edge_extracted_from",
    ]

    for loc in ("vi", "ja", "zh-CN"):
        for key in required_commit_c_keys:
            assert key in TRANSLATIONS[loc], f"Missing key '{key}' in locale '{loc}'"
            val = TRANSLATIONS[loc][key]
            assert isinstance(val, str) and len(val.strip()) > 0, f"Empty value for key '{key}' in '{loc}'"

    # Verify global key parity across all dictionaries
    vi_keys = set(TRANSLATIONS["vi"].keys())
    ja_keys = set(TRANSLATIONS["ja"].keys())
    zh_keys = set(TRANSLATIONS["zh-CN"].keys())
    assert vi_keys == ja_keys == zh_keys


def test_commit_c_button_and_notice_exact_translations() -> None:
    """Verify exact localized strings as specified in Commit C requirements."""
    # Button label
    assert t("btn_view_evidence_graph", locale="vi") == "🕸️ Xem đồ thị bằng chứng"
    assert t("btn_view_evidence_graph", locale="ja") == "🕸️ 根拠グラフを見る"
    assert t("btn_view_evidence_graph", locale="zh-CN") == "🕸️ 查看证据图谱"

    # Insufficient evidence warning
    assert t("evidence_graph_insufficient", locale="vi") == "Chưa đủ bằng chứng để vẽ đồ thị"
    assert t("evidence_graph_insufficient", locale="ja") == "根拠が不足しているためグラフを描画できません"
    assert t("evidence_graph_insufficient", locale="zh-CN") == "证据不足，无法生成图谱"

    # Cached badge
    assert t("evidence_graph_cached_badge", locale="vi") == "(Đã tải từ bộ nhớ đệm)"
    assert t("evidence_graph_cached_badge", locale="ja") == "(キャッシュから読み込み済み)"
    assert t("evidence_graph_cached_badge", locale="zh-CN") == "(已从缓存加载)"

    # Render error
    assert t("evidence_graph_render_error", locale="vi") == "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra."
    assert t("evidence_graph_render_error", locale="ja") == "根拠グラフを表示できません。エラーが発生しました。"
    assert t("evidence_graph_render_error", locale="zh-CN") == "无法显示证据图谱。发生错误。"


# ==============================================================================
# Tier 2: Deterministic Content Hashing & Local Caching
# ==============================================================================

def test_compute_trace_content_hash_deterministic() -> None:
    """Verify SHA-256 content hashing is deterministic and order-independent."""
    node1 = EvidenceNode(id="n1", node_type="question", title="Q1", snippet="Query 1")
    node2 = EvidenceNode(id="n2", node_type="answer", title="A1", snippet="Answer 1")
    edge1 = EvidenceEdge(source_id="n2", target_id="n1", relation_type="derives_from")

    trace_a = EvidenceTrace(
        trace_id="trc_test_001",
        query="Query 1",
        answer_text="Answer 1",
        nodes=[node1, node2],
        edges=[edge1],
        metadata={"status": "valid"},
    )

    # Same nodes in reversed order
    trace_b = EvidenceTrace(
        trace_id="trc_test_001",
        query="Query 1",
        answer_text="Answer 1",
        nodes=[node2, node1],
        edges=[edge1],
        metadata={"status": "valid"},
    )

    hash_a = compute_trace_content_hash(trace_a)
    hash_b = compute_trace_content_hash(trace_b)

    assert isinstance(hash_a, str) and len(hash_a) == 64
    assert hash_a == hash_b, "Content hash must be order-independent for nodes"

    # Modifying a node snippet must alter the content hash
    node2_mod = EvidenceNode(id="n2", node_type="answer", title="A1", snippet="Modified Answer")
    trace_c = EvidenceTrace(
        trace_id="trc_test_001",
        query="Query 1",
        answer_text="Answer 1",
        nodes=[node1, node2_mod],
        edges=[edge1],
        metadata={"status": "valid"},
    )
    hash_c = compute_trace_content_hash(trace_c)
    assert hash_a != hash_c, "Content hash must change when node content changes"


def test_evidence_graph_viewer_cache_operations() -> None:
    """Verify thread-safe caching operations keyed by (trace_id, content_hash)."""
    cache = EvidenceGraphViewerCache(max_entries=10)
    cache.clear()

    trace_id = "trc_cache_001"
    content_hash = "a" * 64
    sample_html = "<div>Sample Graph Artifact</div>"

    assert cache.has(trace_id, content_hash, locale="vi") is False
    assert cache.get(trace_id, content_hash, locale="vi") is None

    cache.set(trace_id, content_hash, sample_html, locale="vi")
    assert cache.has(trace_id, content_hash, locale="vi") is True
    assert cache.get(trace_id, content_hash, locale="vi") == sample_html

    # Miss on different locale or different hash
    assert cache.get(trace_id, content_hash, locale="ja") is None
    assert cache.get(trace_id, "b" * 64, locale="vi") is None

    # Clear cache
    cache.clear()
    assert cache.size() == 0
    assert cache.has(trace_id, content_hash, locale="vi") is False


# ==============================================================================
# Tier 3: Exact 1-1 Topology & Insufficient Evidence Guard
# ==============================================================================

@pytest.fixture
def sample_valid_trace() -> EvidenceTrace:
    """Fixture providing a standard valid EvidenceTrace with exact topology."""
    return EvidenceTrace(
        trace_id="trc_valid_001",
        query="Quy trình xuất nhập kho thế nào?",
        answer_text="Theo tài liệu [1], quy trình yêu cầu kiểm đếm PDA.",
        ui_locale="vi",
        answer_language="vi",
        nodes=[
            EvidenceNode(
                id="q_valid_001",
                node_type="question",
                title="Quy trình xuất nhập kho thế nào?",
                snippet="Quy trình xuất nhập kho thế nào?",
            ),
            EvidenceNode(
                id="ans_valid_001",
                node_type="answer",
                title="Câu trả lời (vi)",
                snippet="Theo tài liệu [1], quy trình yêu cầu kiểm đếm PDA.",
            ),
            EvidenceNode(
                id="cit_valid_001_1",
                node_type="citation",
                title="[1]",
                snippet="Nhân viên sử dụng thiết bị PDA để quét mã vạch.",
                source_id="src_valid_001_1",
                citation_id="[1]",
            ),
            EvidenceNode(
                id="src_valid_001_1",
                node_type="source",
                title="Quy trình kiểm kho 2026.docx",
                snippet="Nhân viên sử dụng thiết bị PDA để quét mã vạch.",
                source_id="local_cases/docs/kiem_kho_2026.docx",
                citation_id="[1]",
            ),
        ],
        edges=[
            EvidenceEdge(
                source_id="ans_valid_001",
                target_id="q_valid_001",
                relation_type="derives_from",
                label="Trả lời cho câu hỏi",
            ),
            EvidenceEdge(
                source_id="ans_valid_001",
                target_id="cit_valid_001_1",
                relation_type="cites",
                label="Dẫn nguồn trích dẫn",
            ),
            EvidenceEdge(
                source_id="cit_valid_001_1",
                target_id="src_valid_001_1",
                relation_type="extracted_from",
                label="Trích từ nguồn tài liệu",
            ),
        ],
        metadata={"status": "valid", "insufficient_evidence": False, "cited_count": 1},
    )


def test_build_view_model_exact_topology(sample_valid_trace: EvidenceTrace) -> None:
    """Verify build_evidence_graph_view_model reflects exact 1-1 topology with zero fake nodes/edges."""
    vm = build_evidence_graph_view_model(sample_valid_trace, locale="vi")

    assert vm.is_insufficient is False
    assert vm.notice is None
    assert vm.trace_id == "trc_valid_001"
    assert vm.stats["nodes"] == 4
    assert vm.stats["edges"] == 3
    assert vm.stats["sources"] == 1
    assert vm.stats["citations"] == 1

    # Verify exact 1-to-1 node mappings
    node_ids = {n["id"] for n in vm.nodes}
    assert node_ids == {"q_valid_001", "ans_valid_001", "cit_valid_001_1", "src_valid_001_1"}

    # Verify exact 1-to-1 edge mappings
    edge_pairs = {(e["source_id"], e["target_id"], e["relation_type"]) for e in vm.edges}
    assert edge_pairs == {
        ("ans_valid_001", "q_valid_001", "derives_from"),
        ("ans_valid_001", "cit_valid_001_1", "cites"),
        ("cit_valid_001_1", "src_valid_001_1", "extracted_from"),
    }


def test_insufficient_evidence_guard_refuses_fake_graph() -> None:
    """Verify that a trace with insufficient_evidence returns a refused graph without fake nodes/edges."""
    insufficient_trace = EvidenceTrace(
        trace_id="trc_insufficient_001",
        query="Hỏi câu không có trong tài liệu",
        answer_text="Không tìm thấy thông tin phù hợp.",
        ui_locale="ja",
        answer_language="ja",
        nodes=[
            EvidenceNode(id="q_insuf", node_type="question", title="Hỏi"),
            EvidenceNode(id="ans_insuf", node_type="answer", title="Trả lời"),
        ],
        edges=[
            EvidenceEdge(source_id="ans_insuf", target_id="q_insuf", relation_type="derives_from"),
        ],
        metadata={"status": "insufficient_evidence", "insufficient_evidence": True, "cited_count": 0},
    )

    assert is_insufficient_evidence(insufficient_trace) is True

    vm = build_evidence_graph_view_model(insufficient_trace, locale="ja")
    assert vm.is_insufficient is True
    assert vm.notice == "根拠が不足しているためグラフを描画できません"
    assert vm.stats["nodes"] == 0
    assert vm.stats["edges"] == 0
    assert len(vm.nodes) == 0
    assert len(vm.edges) == 0

    # HTML rendering should contain the localized warning and no graph nodes
    html_out = render_evidence_graph_html(insufficient_trace, locale="ja")
    assert "根拠が不足しているためグラフを描画できません" in html_out
    assert "egv-insufficient" in html_out
    assert "egv-node-card" not in html_out


def test_insufficient_when_only_source_without_citation_multilingual() -> None:
    """Regression test: Trace with question + answer + source (NO citation) must be marked insufficient across VI, JA, ZH-CN."""
    source_only_trace = EvidenceTrace(
        trace_id="trc_source_only_001",
        query="Quy trình kho",
        answer_text="Thông tin kho bãi",
        nodes=[
            EvidenceNode(id="q1", node_type="question", title="Q"),
            EvidenceNode(id="a1", node_type="answer", title="A"),
            EvidenceNode(id="s1", node_type="source", title="kho.docx", source_id="kho.docx"),
        ],
        edges=[
            EvidenceEdge(source_id="a1", target_id="q1", relation_type="derives_from"),
            EvidenceEdge(source_id="a1", target_id="s1", relation_type="references"),
        ],
        metadata={"status": "valid"},
    )

    expected_notices = {
        "vi": "Chưa đủ bằng chứng để vẽ đồ thị",
        "ja": "根拠が不足しているためグラフを描画できません",
        "zh-CN": "证据不足，无法生成图谱",
    }

    for loc, expected_notice in expected_notices.items():
        vm = build_evidence_graph_view_model(source_only_trace, locale=loc)
        assert vm.is_insufficient is True
        assert vm.notice == expected_notice
        assert vm.stats["nodes"] == 0
        assert vm.stats["edges"] == 0
        assert len(vm.nodes) == 0
        assert len(vm.edges) == 0

        html_out = render_evidence_graph_html(source_only_trace, locale=loc, use_cache=False)
        assert expected_notice in html_out
        assert "egv-insufficient" in html_out
        assert "egv-node-card" not in html_out


def test_insufficient_when_only_citation_without_source() -> None:
    """Regression test: Trace with question + answer + citation (NO source) must be marked insufficient."""
    citation_only_trace = EvidenceTrace(
        trace_id="trc_citation_only_001",
        query="Quy trình kho",
        answer_text="Theo trích dẫn [1]",
        nodes=[
            EvidenceNode(id="q1", node_type="question", title="Q"),
            EvidenceNode(id="a1", node_type="answer", title="A"),
            EvidenceNode(id="c1", node_type="citation", title="[1]", citation_id="[1]"),
        ],
        edges=[
            EvidenceEdge(source_id="a1", target_id="q1", relation_type="derives_from"),
            EvidenceEdge(source_id="a1", target_id="c1", relation_type="cites"),
        ],
        metadata={"status": "valid"},
    )

    vm = build_evidence_graph_view_model(citation_only_trace, locale="vi")
    assert vm.is_insufficient is True
    assert vm.notice == "Chưa đủ bằng chứng để vẽ đồ thị"
    assert vm.stats["nodes"] == 0
    assert vm.stats["edges"] == 0
    assert len(vm.nodes) == 0
    assert len(vm.edges) == 0

    html_out = render_evidence_graph_html(citation_only_trace, locale="vi", use_cache=False)
    assert "Chưa đủ bằng chứng để vẽ đồ thị" in html_out
    assert "egv-insufficient" in html_out
    assert "egv-node-card" not in html_out


def test_renders_normally_when_both_source_and_citation_present(sample_valid_trace: EvidenceTrace) -> None:
    """Regression test: Trace with valid source + citation renders normally with egv-node-card."""
    vm = build_evidence_graph_view_model(sample_valid_trace, locale="vi")
    assert vm.is_insufficient is False
    assert vm.notice is None
    assert vm.stats["nodes"] == 4
    assert vm.stats["edges"] == 3
    assert vm.stats["sources"] == 1
    assert vm.stats["citations"] == 1
    assert len(vm.nodes) == 4
    assert len(vm.edges) == 3

    html_out = render_evidence_graph_html(sample_valid_trace, locale="vi", use_cache=False)
    assert "egv-node-card" in html_out
    assert "egv-insufficient" not in html_out


def test_streamlit_graph_uses_isolated_responsive_component(sample_valid_trace: EvidenceTrace) -> None:
    """Complex graph HTML must never be fed through Streamlit Markdown.

    The component iframe prevents literal HTML being shown in the chat and
    isolates its styles from the surrounding answer.
    """
    with patch("streamlit.components.v1.html") as mock_component, patch("streamlit.markdown") as mock_markdown:
        render_evidence_graph_streamlit(sample_valid_trace, locale="vi")

    mock_component.assert_called_once()
    component_html = mock_component.call_args.args[0]
    assert component_html.startswith("<!doctype html>")
    assert '<meta name="viewport"' in component_html
    assert "egv-container" in component_html
    assert mock_component.call_args.kwargs["height"] >= 520
    assert mock_component.call_args.kwargs["scrolling"] is True
    mock_markdown.assert_not_called()


# ==============================================================================
# Tier 4: UTF-8 Anti-Mojibake & Verbatim Text Preservation
# ==============================================================================

def test_verbatim_preservation_and_anti_mojibake_multilingual() -> None:
    """Verify verbatim preservation of filenames, error codes, citation IDs across VI, JA, ZH."""
    cjk_trace = EvidenceTrace(
        trace_id="trc_cjk_001",
        query="品質基準と生产规范について",
        answer_text="Báo cáo [1] và tài liệu [証拠-JA-02] ghi nhận mã lỗi ERR_KHO_SYNC_0x80040111.",
        ui_locale="zh-CN",
        answer_language="zh-CN",
        nodes=[
            EvidenceNode(
                id="q_cjk",
                node_type="question",
                title="品質基準と生产规范について",
                snippet="品質基準と生产规范について",
            ),
            EvidenceNode(
                id="ans_cjk",
                node_type="answer",
                title="回答 (zh-CN)",
                snippet="Báo cáo [1] và tài liệu [証拠-JA-02] ghi nhận mã lỗi ERR_KHO_SYNC_0x80040111.",
            ),
            EvidenceNode(
                id="cit_cjk_1",
                node_type="citation",
                title="[1]",
                snippet="Đoạn trích tiếng Việt: nhân viên thực hiện kiểm tra định kỳ ắ ằ ẳ ẵ ặ.",
                source_id="src_cjk_1",
                citation_id="[1]",
            ),
            EvidenceNode(
                id="cit_cjk_2",
                node_type="citation",
                title="[証拠-JA-02]",
                snippet="日本語スニペット：ハンディターミナル「HT-5000」でバーコードをスキャンする。",
                source_id="src_cjk_2",
                citation_id="[証拠-JA-02]",
            ),
            EvidenceNode(
                id="src_cjk_1",
                node_type="source",
                title="Báo_cáo_tài_chính_Q3_2026.xlsx",
                snippet="Đoạn trích tiếng Việt: nhân viên thực hiện kiểm tra định kỳ ắ ằ ẳ ẵ ặ.",
                source_id="local_cases/docs/Báo_cáo_tài_chính_Q3_2026.xlsx",
                citation_id="[1]",
            ),
            EvidenceNode(
                id="src_cjk_2",
                node_type="source",
                title="品質管理規定_v2.pdf",
                snippet="日本語スニペット：ハンディターミナル「HT-5000」でバーコードをスキャンする。",
                source_id="local_cases/docs/品質管理規定_v2.pdf",
                citation_id="[証拠-JA-02]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="ans_cjk", target_id="q_cjk", relation_type="derives_from"),
            EvidenceEdge(source_id="ans_cjk", target_id="cit_cjk_1", relation_type="cites"),
            EvidenceEdge(source_id="ans_cjk", target_id="cit_cjk_2", relation_type="cites"),
            EvidenceEdge(source_id="cit_cjk_1", target_id="src_cjk_1", relation_type="extracted_from"),
            EvidenceEdge(source_id="cit_cjk_2", target_id="src_cjk_2", relation_type="extracted_from"),
        ],
        metadata={"status": "valid", "insufficient_evidence": False, "cited_count": 2},
    )

    html_out = render_evidence_graph_html(cjk_trace, locale="zh-CN")

    # Verbatim checks
    assert "Báo_cáo_tài_chính_Q3_2026.xlsx" in html_out
    assert "品質管理規定_v2.pdf" in html_out
    assert "ERR_KHO_SYNC_0x80040111" in html_out
    assert "[証拠-JA-02]" in html_out
    assert "ハンディターミナル" in html_out
    assert "ắ ằ ẳ ẵ ặ" in html_out
    assert "证据图谱" in html_out

    # Anti-mojibake check: no raw unicode escape sequences in output
    assert "\\u" not in html_out


# ==============================================================================
# Tier 5: Fail-Safe Error Handling & Offline Isolation
# ==============================================================================

def test_render_evidence_graph_html_fail_safe_isolation() -> None:
    """Verify that renderer errors are safely caught and return localized error banners."""
    corrupted_dict = {"nodes": "not-a-list", "edges": 12345}

    html_err_vi = render_evidence_graph_html(corrupted_dict, locale="vi")
    assert "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra." in html_err_vi
    assert "egv-error" in html_err_vi

    html_err_ja = render_evidence_graph_html(corrupted_dict, locale="ja")
    assert "根拠グラフを表示できません。エラーが発生しました。" in html_err_ja

    html_err_zh = render_evidence_graph_html(corrupted_dict, locale="zh-CN")
    assert "无法显示证据图谱。发生错误。" in html_err_zh


def test_zero_cloud_egress_and_offline_safety(sample_valid_trace: EvidenceTrace) -> None:
    """Verify that graph generation is 100% offline with zero network requests or CDN dependencies."""
    html_out = render_evidence_graph_html(sample_valid_trace, locale="vi")

    # No external CDN or HTTP resources
    assert "http://" not in html_out
    assert "https://" not in html_out
    assert "cdn." not in html_out
    assert "googleapis.com" not in html_out
    assert "<script src=" not in html_out


# ==============================================================================
# Tier 6: UI Chat Bubble Button Visibility & On-Demand Trigger
# ==============================================================================
# Tier 6: UI Chat Bubble Button Visibility & On-Demand Trigger
# ==============================================================================

def test_chat_bubble_button_visibility_before_and_after_click(sample_valid_trace: EvidenceTrace) -> None:
    """Verify true on-demand behavior: st.button is shown, renderer is NOT called before click, only called after click."""
    msg = ChatMessage(
        id="msg_assistant_001",
        conversation_id="conv_001",
        role="assistant",
        content="Câu trả lời có bằng chứng.",
        trace_id=sample_valid_trace.trace_id,
    )

    mock_loader = MagicMock(return_value=sample_valid_trace)

    # 1. Before Click (is_open = False, button returns False):
    # Renderer and trace_loader MUST NOT be called!
    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button", return_value=False) as mock_button, \
         patch("streamlit.markdown") as mock_markdown, \
         patch("aios_habit.workspace_chat_ui.render_evidence_graph_streamlit") as mock_render:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        # Session state empty
        mock_session_state: Dict[str, Any] = {}
        with patch("streamlit.session_state", mock_session_state):
            render_chat_bubble(msg, is_latest=False, locale="vi", trace_loader=mock_loader)

            # Button rendered with correct i18n label
            mock_button.assert_called_once_with("🕸️ Xem đồ thị bằng chứng", key="btn_view_graph_msg_assistant_001")
            # Loader and Renderer NOT called before click!
            mock_loader.assert_not_called()
            mock_render.assert_not_called()

    # 2. After Click (st.button returns True):
    # Loader and Renderer ARE called exactly once!
    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button", return_value=True) as mock_button, \
         patch("streamlit.markdown") as mock_markdown, \
         patch("aios_habit.workspace_chat_ui.render_evidence_graph_streamlit") as mock_render:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        mock_session_state = {}
        with patch("streamlit.session_state", mock_session_state):
            render_chat_bubble(msg, is_latest=False, locale="vi", trace_loader=mock_loader)

            mock_button.assert_called_once_with("🕸️ Xem đồ thị bằng chứng", key="btn_view_graph_msg_assistant_001")
            mock_loader.assert_called_once_with(sample_valid_trace.trace_id)
            mock_render.assert_called_once_with(sample_valid_trace, locale="vi")
            assert mock_session_state.get("wsc_show_graph_msg_assistant_001") is True

    # 3. Already Open state (is_open = True in session_state):
    # Shows hide button and renders graph
    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button", return_value=False) as mock_button, \
         patch("streamlit.markdown") as mock_markdown, \
         patch("aios_habit.workspace_chat_ui.render_evidence_graph_streamlit") as mock_render:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        mock_session_state = {"wsc_show_graph_msg_assistant_001": True}
        with patch("streamlit.session_state", mock_session_state):
            render_chat_bubble(msg, is_latest=False, locale="vi", trace_loader=mock_loader)

            mock_button.assert_called_once_with("Đóng đồ thị bằng chứng", key="btn_hide_graph_msg_assistant_001")
            mock_render.assert_called_once_with(sample_valid_trace, locale="vi")


def test_chat_bubble_button_hidden_when_trace_missing() -> None:
    """Verify that button is completely hidden if trace_id is None or empty."""
    # Case A: trace_id is None
    msg_no_trace = ChatMessage(
        id="msg_001",
        conversation_id="conv_001",
        role="assistant",
        content="Câu trả lời không có trace_id.",
        trace_id=None,
    )
    mock_loader_a = MagicMock()

    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.markdown") as mock_markdown:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        render_chat_bubble(msg_no_trace, is_latest=False, locale="vi", trace_loader=mock_loader_a)
        mock_loader_a.assert_not_called()
        mock_button.assert_not_called()

    # Case B: trace_id is empty string
    msg_empty_trace = ChatMessage(
        id="msg_002",
        conversation_id="conv_001",
        role="assistant",
        content="Câu trả lời trace_id rỗng.",
        trace_id="   ",
    )
    mock_loader_b = MagicMock()

    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.markdown") as mock_markdown:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        render_chat_bubble(msg_empty_trace, is_latest=False, locale="vi", trace_loader=mock_loader_b)
        mock_loader_b.assert_not_called()
        mock_button.assert_not_called()


def test_chat_bubble_user_message_never_shows_graph() -> None:
    """Verify that user messages never attempt to load or render evidence graph."""
    user_msg = ChatMessage(
        id="msg_user_001",
        conversation_id="conv_001",
        role="user",
        content="User asks question.",
        trace_id="trc_should_be_ignored",
    )
    mock_loader = MagicMock()

    with patch("streamlit.chat_message") as mock_chat_message, \
         patch("streamlit.button") as mock_button, \
         patch("streamlit.markdown") as mock_markdown:

        mock_chat_message.return_value.__enter__ = MagicMock()
        mock_chat_message.return_value.__exit__ = MagicMock()

        render_chat_bubble(user_msg, is_latest=False, locale="vi", trace_loader=mock_loader)
        mock_loader.assert_not_called()
        mock_button.assert_not_called()


def test_cache_honesty_miss_and_hit(sample_valid_trace: EvidenceTrace) -> None:
    """Verify Cache Honesty: First render (Miss) has NO cached badge; Second render (Hit) HAS cached badge."""
    VIEWER_CACHE.clear()

    # 1. First render -> Cache Miss
    html_miss = render_evidence_graph_html(sample_valid_trace, locale="vi", use_cache=True)
    assert "egv-cached-badge" not in html_miss
    assert "(Đã tải từ bộ nhớ đệm)" not in html_miss

    # 2. Second render -> Cache Hit
    html_hit = render_evidence_graph_html(sample_valid_trace, locale="vi", use_cache=True)
    assert "egv-cached-badge" in html_hit
    assert "(Đã tải từ bộ nhớ đệm)" in html_hit
