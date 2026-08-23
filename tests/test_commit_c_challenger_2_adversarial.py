# -*- coding: utf-8 -*-
"""Empirical Adversarial Challenge Test Suite for AIOS_habbit Commit C.

Authored by Challenger 2 to rigorously probe:
1. White-box branch coverage of `evidence_graph_viewer.py`, `i18n.py`, `workspace_chat_ui.py`.
2. All conditional branches for `render_chat_bubble` (assistant valid, assistant missing, assistant error, user, other roles, is_latest).
3. `is_insufficient_evidence(trace)` across all locales (`vi`, `ja`, `zh-CN`, and fallback) ensuring zero fake graphs.
4. Cache mechanics: hit vs miss, eviction on max_entries, thread-safety, clear, key normalization.
5. Fail-safe exception handler branches across HTML and Streamlit rendering.
6. Zero cloud egress / sandbox isolation: strictly offline, no sockets, no subprocesses, no external CDNs/fonts.
"""
from __future__ import annotations

import concurrent.futures
import html
import json
import os
import socket
import subprocess
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest

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
# 1. White-Box Branch Coverage: compute_trace_content_hash & Viewer Engine
# ==============================================================================

class TestEvidenceGraphViewerBranchCoverage:
    """Probe conditional branches in hashing, model coercion, and node/edge mapping."""

    def test_compute_trace_content_hash_input_variants(self) -> None:
        """Probe branches: EvidenceTrace vs Dict vs Unknown/None types in hashing."""
        # Branch 1: EvidenceTrace with sparse/None optional fields
        sparse_trace = EvidenceTrace(
            trace_id="trc_sparse_001",
            query=None,
            answer_text=None,
            schema_version=None,
            nodes=[],
            edges=[],
            metadata=None,
        )
        hash_sparse = compute_trace_content_hash(sparse_trace)
        assert isinstance(hash_sparse, str) and len(hash_sparse) == 64

        # Branch 2: Dict with question/answer alternative key aliases
        dict_alt_keys = {
            "trace_id": "trc_dict_001",
            "question": "Hỏi với key question",
            "answer": "Trả lời với key answer",
            "nodes": [{"id": "n1", "title": "Node 1"}],
            "edges": [{"source_id": "n1", "target_id": "n2", "relation_type": "cites"}],
            "metadata": {"cached_at": "ignore-me", "render_time": "ignore-me", "real_key": "123"},
        }
        hash_dict = compute_trace_content_hash(dict_alt_keys)
        assert isinstance(hash_dict, str) and len(hash_dict) == 64

        # Verify cached_at / render_time metadata exclusion in canonicalization
        dict_alt_keys_diff_cache_time = dict(dict_alt_keys)
        dict_alt_keys_diff_cache_time["metadata"] = {
            "cached_at": "diff-time-123",
            "render_time": "diff-time-456",
            "real_key": "123",
        }
        hash_dict_same = compute_trace_content_hash(dict_alt_keys_diff_cache_time)
        assert hash_dict == hash_dict_same, "Metadata cached_at and render_time must be ignored in hash"

        # Branch 3: Unknown / invalid input type fallback (e.g. int, list, None)
        hash_none = compute_trace_content_hash(None)  # type: ignore
        assert isinstance(hash_none, str) and len(hash_none) == 64
        hash_int = compute_trace_content_hash(12345)  # type: ignore
        assert hash_none == hash_int

    def test_coerce_to_trace_error_branch(self) -> None:
        """Probe TypeError branch in _coerce_to_trace when input is neither trace nor dict."""
        with pytest.raises(TypeError) as excinfo:
            _coerce_to_trace(["invalid", "list"])  # type: ignore
        assert "Expected EvidenceTrace or dict, got list" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            _coerce_to_trace(12345)  # type: ignore
        assert "Expected EvidenceTrace or dict, got int" in str(excinfo.value)

    def test_view_model_strictly_filters_non_commit_c_node_types_and_dangling_edges(self) -> None:
        """Verify Commit C strict filtering: only question, answer, source, citation are kept;

        chunk, evidence, claim, verification, custom_unknown_type and dangling edges are filtered out.
        """
        node_types = [
            "question", "answer", "source", "citation",
            "chunk", "evidence", "claim", "verification",
            "custom_unknown_type",
        ]
        nodes = [
            EvidenceNode(
                id=f"node_{ntype}",
                node_type=ntype,
                title=f"Title {ntype}",
                snippet=f"Snippet for {ntype}",
                source_id=f"src_{ntype}" if ntype == "source" else "",
                citation_id=f"[{ntype}]" if ntype == "citation" else "",
                confidence=0.85,
            )
            for ntype in node_types
        ]
        edges = [
            EvidenceEdge(source_id="node_answer", target_id="node_question", relation_type="derives_from"),
            EvidenceEdge(source_id="node_answer", target_id="node_citation", relation_type="cites"),
            EvidenceEdge(source_id="node_citation", target_id="node_source", relation_type="extracted_from"),
            EvidenceEdge(source_id="node_claim", target_id="node_evidence", relation_type="supports"),
            EvidenceEdge(source_id="node_chunk", target_id="node_source", relation_type="custom_rel"),
        ]

        trace = EvidenceTrace(
            trace_id="trc_all_types",
            query="Test all types",
            answer_text="Answer all types",
            nodes=nodes,
            edges=edges,
            metadata={"status": "valid"},
        )

        vm = build_evidence_graph_view_model(trace, locale="vi")
        # Only 4 permitted Commit C node types are kept
        assert vm.stats["nodes"] == 4
        # Only 3 valid edges connecting permitted nodes are kept
        assert vm.stats["edges"] == 3
        assert vm.stats["sources"] == 1
        assert vm.stats["citations"] == 1

        allowed_ids = {"node_question", "node_answer", "node_source", "node_citation"}
        assert {n["id"] for n in vm.nodes} == allowed_ids

        # Verify non-Commit C types are strictly excluded
        filtered_out_types = {"chunk", "evidence", "claim", "verification", "custom_unknown_type"}
        actual_types = {n["node_type"] for n in vm.nodes}
        assert actual_types.isdisjoint(filtered_out_types)

    def test_view_model_insufficient_when_filtered_leaves_no_source_or_citation(self) -> None:
        """Verify that if filtering leaves zero valid source or citation nodes, graph is refused."""
        trace = EvidenceTrace(
            trace_id="trc_only_claims",
            query="Query",
            answer_text="Answer",
            nodes=[
                EvidenceNode(id="n_q", node_type="question", title="Q"),
                EvidenceNode(id="n_a", node_type="answer", title="A"),
                EvidenceNode(id="n_claim", node_type="claim", title="Claim only"),
            ],
            edges=[
                EvidenceEdge(source_id="n_a", target_id="n_q", relation_type="derives_from"),
            ],
            metadata={"status": "valid"},
        )
        vm = build_evidence_graph_view_model(trace, locale="vi")
        assert vm.is_insufficient is True
        assert vm.notice == "Chưa đủ bằng chứng để vẽ đồ thị"
        assert len(vm.nodes) == 0

    def test_view_model_to_dict_and_esc_helper(self) -> None:
        """Verify ViewModel to_dict completeness and _esc edge cases."""
        assert _esc(None) == ""
        assert _esc("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert _esc(12345) == "12345"

        vm = EvidenceGraphViewModel(
            trace_id="trc_dict_test",
            content_hash="h123",
            locale="vi",
            is_insufficient=False,
            notice=None,
            stats={"nodes": 1, "edges": 0},
            nodes=[{"id": "n1"}],
            edges=[],
        )
        d = vm.to_dict()
        assert d["trace_id"] == "trc_dict_test"
        assert d["content_hash"] == "h123"
        assert d["is_insufficient"] is False
        assert d["stats"]["nodes"] == 1


# ==============================================================================
# 2. Cache Mechanics: Eviction, Hit/Miss, Thread Safety
# ==============================================================================

class TestEvidenceGraphViewerCacheMechanics:
    """Stress-test cache lifecycle, capacity eviction, and concurrency."""

    def test_cache_eviction_when_capacity_exceeded(self) -> None:
        """Verify cache evicts oldest entry when max_entries is exceeded."""
        cache = EvidenceGraphViewerCache(max_entries=3)
        cache.clear()

        cache.set("trc_1", "hash_1", "html_1", locale="vi")
        cache.set("trc_2", "hash_2", "html_2", locale="vi")
        cache.set("trc_3", "hash_3", "html_3", locale="vi")
        assert cache.size() == 3

        # Insert 4th entry -> trc_1 should be evicted
        cache.set("trc_4", "hash_4", "html_4", locale="vi")
        assert cache.size() == 3
        assert cache.get("trc_1", "hash_1", locale="vi") is None
        assert cache.get("trc_2", "hash_2", locale="vi") == "html_2"
        assert cache.get("trc_3", "hash_3", locale="vi") == "html_3"
        assert cache.get("trc_4", "hash_4", locale="vi") == "html_4"

    def test_cache_key_normalization_and_whitespace_trimming(self) -> None:
        """Verify that trace_id/content_hash whitespace and locale casing are normalized."""
        cache = EvidenceGraphViewerCache(max_entries=10)
        cache.clear()

        cache.set("  trc_trim  ", "  hash_trim  ", "cached_html", locale="VI-vn")
        assert cache.get("trc_trim", "hash_trim", locale="vi") == "cached_html"
        assert cache.has("trc_trim", "hash_trim", locale="vi") is True

    def test_cache_thread_safety_concurrent_access(self) -> None:
        """Stress-test thread safety with concurrent readers and writers."""
        cache = EvidenceGraphViewerCache(max_entries=100)
        cache.clear()

        def worker(worker_id: int) -> None:
            for i in range(50):
                tid = f"trc_{worker_id}_{i}"
                h = f"hash_{worker_id}_{i}"
                cache.set(tid, h, f"content_{worker_id}_{i}", locale="vi")
                val = cache.get(tid, h, locale="vi")
                assert val == f"content_{worker_id}_{i}" or val is None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, w) for w in range(10)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        assert cache.size() <= 100


# ==============================================================================
# 3. Insufficient Evidence Guards: Probing all Locales & Fallbacks
# ==============================================================================

class TestInsufficientEvidenceGuardsAcrossLocales:
    """Verify insufficient evidence refusal and exact localized warnings across VI, JA, ZH, and fallback."""

    @pytest.mark.parametrize(
        "loc,expected_notice,expected_desc",
        [
            ("vi", "Chưa đủ bằng chứng để vẽ đồ thị", "Câu trả lời này chưa có trích dẫn bằng chứng hợp lệ từ tài liệu đã bật."),
            ("ja", "根拠が不足しているためグラフを描画できません", "この回答には有効化されたドキュメントからの有効な証拠引用が含まれていません。"),
            ("zh-CN", "证据不足，无法生成图谱", "该回答未包含来自已启用文档的有效证据引用。"),
            ("fr", "Chưa đủ bằng chứng để vẽ đồ thị", "Câu trả lời này chưa có trích dẫn bằng chứng hợp lệ từ tài liệu đã bật."),  # Fallback to vi
        ],
    )
    def test_insufficient_evidence_notice_per_locale(self, loc: str, expected_notice: str, expected_desc: str) -> None:
        """Verify view model and HTML output contain exact localized strings for insufficient evidence."""
        trace = EvidenceTrace(
            trace_id=f"trc_insuf_{loc}",
            query="Câu hỏi không có tài liệu",
            answer_text="Tôi không biết",
            ui_locale=loc,
            answer_language=loc,
            nodes=[],
            edges=[],
            metadata={"status": "insufficient_evidence", "insufficient_evidence": True},
        )

        vm = build_evidence_graph_view_model(trace, locale=loc)
        assert vm.is_insufficient is True
        assert vm.notice == expected_notice
        assert vm.notice_desc == expected_desc
        assert vm.nodes == []
        assert vm.edges == []
        assert vm.stats["nodes"] == 0
        assert vm.stats["edges"] == 0

        html_out = render_evidence_graph_html(trace, locale=loc)
        assert expected_notice in html_out
        assert expected_desc in html_out
        assert "egv-insufficient" in html_out
        assert "egv-node-card" not in html_out

    def test_render_evidence_graph_streamlit_insufficient_evidence(self) -> None:
        """Verify Streamlit renderer calls st.warning and st.caption on insufficient trace."""
        trace = EvidenceTrace(
            trace_id="trc_insuf_st",
            query="Q",
            answer_text="A",
            nodes=[],
            edges=[],
            metadata={"insufficient_evidence": True},
        )

        with patch("streamlit.warning") as mock_warn, patch("streamlit.caption") as mock_caption:
            render_evidence_graph_streamlit(trace, locale="ja")
            mock_warn.assert_called_once_with("⚠️ 根拠が不足しているためグラフを描画できません")
            mock_caption.assert_called_once_with("この回答には有効化されたドキュメントからの有効な証拠引用が含まれていません。")


# ==============================================================================
# 4. Fail-Safe Exception Handling & Corrupted Data Handling
# ==============================================================================

class TestFailSafeRenderingExceptionHandling:
    """Verify that malformed inputs and renderer crashes are caught without impacting chat UI."""

    def test_render_evidence_graph_html_corrupted_inputs(self) -> None:
        """Verify corrupted inputs return localized error banner without uncaught exception."""
        corrupted_cases = [
            {"trace_id": 12345, "nodes": "not-a-list"},
            {"nodes": [{"id": None, "node_type": {}}]},
            "completely-invalid-string",
            None,
        ]

        for case in corrupted_cases:
            html_vi = render_evidence_graph_html(case, locale="vi", use_cache=False)  # type: ignore
            assert "Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra." in html_vi
            assert "egv-error" in html_vi

            html_ja = render_evidence_graph_html(case, locale="ja", use_cache=False)  # type: ignore
            assert "根拠グラフを表示できません。エラーが発生しました。" in html_ja

            html_zh = render_evidence_graph_html(case, locale="zh-CN", use_cache=False)  # type: ignore
            assert "无法显示证据图谱。发生错误。" in html_zh

    def test_render_evidence_graph_streamlit_exception_fallback(self) -> None:
        """Verify Streamlit renderer traps unexpected exception and outputs st.error."""
        with patch("aios_habit.evidence_graph_viewer._coerce_to_trace", side_effect=RuntimeError("Simulated Boom")), \
             patch("streamlit.error") as mock_st_error:
            render_evidence_graph_streamlit({"dummy": "dict"}, locale="vi")
            mock_st_error.assert_called_once_with("❌ Không thể hiển thị đồ thị bằng chứng. Đã có lỗi xảy ra.")

    def test_render_evidence_graph_streamlit_import_error(self) -> None:
        """Verify Streamlit renderer exits cleanly if Streamlit is not installed."""
        with patch.dict("sys.modules", {"streamlit": None}):
            # Should not raise exception
            render_evidence_graph_streamlit(
                EvidenceTrace(trace_id="t1", query="q", answer_text="a", nodes=[], edges=[]),
                locale="vi",
            )


# ==============================================================================
# 5. Chat Bubble Branch Exploration: Role, Trace Exists, Missing, Error, Latest
# ==============================================================================

class TestChatBubbleBranchExploration:
    """Exhaustively test every conditional branch in `render_chat_bubble`."""

    def test_chat_bubble_assistant_with_valid_trace_in_store(self) -> None:
        """Branch: msg.role == 'assistant' and valid trace found -> renders st.button and on-demand triggers."""
        valid_trace = EvidenceTrace(
            trace_id="trc_bubble_001",
            query="Q",
            answer_text="A",
            nodes=[
                EvidenceNode(id="n1", node_type="question", title="Q"),
                EvidenceNode(id="n2", node_type="answer", title="A"),
                EvidenceNode(id="n3", node_type="source", title="S", source_id="s1"),
                EvidenceNode(id="n4", node_type="citation", title="[1]", citation_id="[1]", source_id="s1"),
            ],
            edges=[EvidenceEdge(source_id="n2", target_id="n1", relation_type="derives_from")],
            metadata={"status": "valid"},
        )
        msg = ChatMessage(
            id="msg_001",
            conversation_id="conv_1",
            role="assistant",
            content="Valid answer with trace.",
            trace_id="trc_bubble_001",
        )
        mock_loader = MagicMock(return_value=valid_trace)

        for loc, expected_label in [
            ("vi", "🕸️ Xem đồ thị bằng chứng"),
            ("ja", "🕸️ 根拠グラフを見る"),
            ("zh-CN", "🕸️ 查看证据图谱"),
        ]:
            with patch("streamlit.chat_message") as mock_cm, \
                 patch("streamlit.button", return_value=True) as mock_btn, \
                 patch("streamlit.markdown") as mock_md, \
                 patch("aios_habit.workspace_chat_ui.render_evidence_graph_streamlit") as mock_render_st:

                mock_cm.return_value.__enter__ = MagicMock()
                mock_cm.return_value.__exit__ = MagicMock()

                mock_session_state: Dict[str, Any] = {}
                with patch("streamlit.session_state", mock_session_state):
                    render_chat_bubble(msg, is_latest=False, locale=loc, trace_loader=mock_loader)
                    mock_btn.assert_called_once_with(expected_label, key="btn_view_graph_msg_001")
                    mock_loader.assert_called_with("trc_bubble_001")
                    mock_render_st.assert_called_once_with(valid_trace, locale=loc)

    def test_chat_bubble_assistant_trace_loader_exception_handling(self) -> None:
        """Branch: msg.role == 'assistant' and trace_loader raises exception -> warning shown, no crash."""
        msg = ChatMessage(
            id="msg_002",
            conversation_id="conv_1",
            role="assistant",
            content="Answer where loader explodes.",
            trace_id="trc_exploding",
        )
        mock_loader = MagicMock(side_effect=IOError("Corrupted trace file"))

        with patch("streamlit.chat_message") as mock_cm, \
             patch("streamlit.button", return_value=True) as mock_btn, \
             patch("streamlit.warning") as mock_warning, \
             patch("streamlit.markdown") as mock_md:

            mock_cm.return_value.__enter__ = MagicMock()
            mock_cm.return_value.__exit__ = MagicMock()

            # Should not crash and should show friendly warning
            mock_session_state: Dict[str, Any] = {}
            with patch("streamlit.session_state", mock_session_state):
                render_chat_bubble(msg, is_latest=False, locale="vi", trace_loader=mock_loader)
                mock_loader.assert_called_once_with("trc_exploding")
                mock_warning.assert_called_once_with("Không tìm thấy vết bằng chứng tương ứng.")

    def test_chat_bubble_assistant_is_latest_badge_branch(self) -> None:
        """Branch: msg.role == 'assistant' and is_latest == True/False."""
        msg = ChatMessage(
            id="msg_003",
            conversation_id="conv_1",
            role="assistant",
            content="Latest answer content.",
            trace_id=None,
        )

        # Case 1: is_latest = True
        with patch("streamlit.chat_message") as mock_cm, patch("streamlit.markdown") as mock_md:
            mock_cm.return_value.__enter__ = MagicMock()
            mock_cm.return_value.__exit__ = MagicMock()

            render_chat_bubble(msg, is_latest=True, locale="ja")
            # Should have called markdown for latest badge AND for content
            assert mock_md.call_count == 2
            # Check latest answer badge string in call
            badge_call_str = str(mock_md.call_args_list[0])
            assert "最新の回答" in badge_call_str

        # Case 2: is_latest = False
        with patch("streamlit.chat_message") as mock_cm, patch("streamlit.markdown") as mock_md:
            mock_cm.return_value.__enter__ = MagicMock()
            mock_cm.return_value.__exit__ = MagicMock()

            render_chat_bubble(msg, is_latest=False, locale="ja")
            assert mock_md.call_count == 1

    def test_chat_bubble_non_assistant_roles(self) -> None:
        """Branch: msg.role == 'user' vs msg.role == 'system' / other."""
        # User message
        user_msg = ChatMessage(id="u1", conversation_id="c1", role="user", content="User text", trace_id="trc_x")
        with patch("streamlit.chat_message") as mock_cm, patch("streamlit.markdown") as mock_md:
            mock_cm.return_value.__enter__ = MagicMock()
            mock_cm.return_value.__exit__ = MagicMock()
            render_chat_bubble(user_msg, is_latest=False, locale="vi")
            mock_cm.assert_called_once_with("user")
            mock_md.assert_called_once_with("User text")

        # System / unknown message
        sys_msg = ChatMessage(id="s1", conversation_id="c1", role="system", content="System notice")
        with patch("streamlit.info") as mock_info:
            render_chat_bubble(sys_msg, is_latest=False, locale="vi")
            mock_info.assert_called_once_with("System notice")


# ==============================================================================
# 6. Zero Cloud Egress & Sandbox Isolation Verification
# ==============================================================================

class TestZeroCloudEgressAndSandboxIsolation:
    """Verify strict 0 cloud egress, no network calls, no subprocesses, 100% offline."""

    def test_strict_zero_network_egress_during_all_operations(self) -> None:
        """Ensure no socket connection or HTTP call is attempted during rendering and hashing."""
        trace = EvidenceTrace(
            trace_id="trc_offline_001",
            query="Kiểm tra offline isolation",
            answer_text="Đồ thị hoàn toàn chạy cục bộ không gửi ra internet.",
            nodes=[
                EvidenceNode(id="n1", node_type="question", title="Q"),
                EvidenceNode(id="n2", node_type="answer", title="A"),
                EvidenceNode(id="n3", node_type="source", title="offline.txt", source_id="src1"),
                EvidenceNode(id="n4", node_type="citation", title="[1]", citation_id="[1]", source_id="src1"),
            ],
            edges=[
                EvidenceEdge(source_id="n2", target_id="n1", relation_type="derives_from"),
                EvidenceEdge(source_id="n2", target_id="n4", relation_type="cites"),
                EvidenceEdge(source_id="n4", target_id="n3", relation_type="extracted_from"),
            ],
            metadata={"status": "valid"},
        )

        def blocked_socket(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("EGRESS VIOLATION: socket.socket() was called!")

        def blocked_getaddrinfo(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("EGRESS VIOLATION: socket.getaddrinfo() was called!")

        with patch("socket.socket", side_effect=blocked_socket), \
             patch("socket.getaddrinfo", side_effect=blocked_getaddrinfo):

            # Compute hash
            h = compute_trace_content_hash(trace)
            assert isinstance(h, str)

            # Build view model
            vm = build_evidence_graph_view_model(trace, locale="vi")
            assert vm.stats["nodes"] == 4

            # Render HTML across all 3 locales
            for loc in ("vi", "ja", "zh-CN"):
                html_out = render_evidence_graph_html(trace, locale=loc, use_cache=False)
                assert len(html_out) > 100
                assert "http://" not in html_out
                assert "https://" not in html_out
                assert "cdn" not in html_out

    def test_strict_zero_subprocess_spawn(self) -> None:
        """Ensure no external CLI command or subprocess is executed."""
        trace = EvidenceTrace(
            trace_id="trc_no_cli",
            query="Q",
            answer_text="A",
            nodes=[EvidenceNode(id="n1", node_type="question", title="Q")],
            edges=[],
            metadata={"status": "valid"},
        )

        def blocked_popen(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("CLI VIOLATION: subprocess.Popen() was called!")

        def blocked_run(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("CLI VIOLATION: subprocess.run() was called!")

        with patch("subprocess.Popen", side_effect=blocked_popen), \
             patch("subprocess.run", side_effect=blocked_run), \
             patch("os.system", side_effect=blocked_popen):

            html_out = render_evidence_graph_html(trace, locale="vi")
            assert "trc_no_cli" in html_out
