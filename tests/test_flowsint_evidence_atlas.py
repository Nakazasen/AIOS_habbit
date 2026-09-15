"""Unit tests for Flowsint-style 3-column Evidence Graph & Atlas UX (Feature 013).

Validates:
- 3-column layout: Entities Sidebar, Dark Pill-Node Canvas, Inspector Panel.
- 100% Offline-safe, Zero Cloud Egress, No external CDN.
- Multi-locale support across VI, JA, ZH-CN with no hardcoded strings.
- Verbatim preservation of snippets and clean node pill labels (no raw <tspan> leak).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from aios_habit.excaliflow_adapter import ExcaliFlowAdapter
from aios_habit.evidence_trace_schema import EvidenceEdge, EvidenceNode, EvidenceTrace


def _make_sample_trace(
    query: str = "Lỗi đồng bộ kho hàng",
    answer_text: str = "Ghi nhận mã lỗi ERR_KHO_SYNC_0x80040111 trong báo cáo [1] và hướng dẫn [2].",
    locale: str = "vi",
) -> EvidenceTrace:
    nodes = [
        EvidenceNode(
            id="q1",
            node_type="question",
            title=query,
            snippet=query,
        ),
        EvidenceNode(
            id="ans1",
            node_type="answer",
            title="Câu trả lời",
            snippet=answer_text,
        ),
        EvidenceNode(
            id="cit1",
            node_type="citation",
            title="[1]",
            snippet="Đoạn trích chi tiết về ERR_KHO_SYNC_0x80040111 trong quá trình kiểm toán hàng tồn kho.",
            source_id="local_cases/docs/Bao_cao_kiem_toan_kho.pdf",
            citation_id="[1]",
        ),
        EvidenceNode(
            id="cit2",
            node_type="citation",
            title="[2]",
            snippet="Hướng dẫn vận hành máy quét mã vạch và xử lý ngắt kết nối.",
            source_id="local_cases/docs/Huong_dan_may_quet.docx",
            citation_id="[2]",
        ),
        EvidenceNode(
            id="src1",
            node_type="source",
            title="Bao_cao_kiem_toan_kho.pdf",
            snippet="Đoạn trích chi tiết về ERR_KHO_SYNC_0x80040111 trong quá trình kiểm toán hàng tồn kho.",
            source_id="local_cases/docs/Bao_cao_kiem_toan_kho.pdf",
            citation_id="[1]",
        ),
        EvidenceNode(
            id="src2",
            node_type="source",
            title="Huong_dan_may_quet.docx",
            snippet="Hướng dẫn vận hành máy quét mã vạch và xử lý ngắt kết nối.",
            source_id="local_cases/docs/Huong_dan_may_quet.docx",
            citation_id="[2]",
        ),
    ]
    edges = [
        EvidenceEdge(source_id="ans1", target_id="q1", relation_type="derives_from"),
        EvidenceEdge(source_id="ans1", target_id="cit1", relation_type="cites"),
        EvidenceEdge(source_id="ans1", target_id="cit2", relation_type="cites"),
        EvidenceEdge(source_id="cit1", target_id="src1", relation_type="extracted_from"),
        EvidenceEdge(source_id="cit2", target_id="src2", relation_type="extracted_from"),
    ]
    return EvidenceTrace(
        trace_id="trc_flowsint_001",
        query=query,
        answer_text=answer_text,
        ui_locale=locale,
        answer_language=locale,
        nodes=nodes,
        edges=edges,
        metadata={"status": "valid", "insufficient_evidence": False, "cited_count": 2},
    )


class TestFlowsintEvidenceAtlas:
    """Test suite for Flowsint-style Evidence Graph visualization."""

    def test_flowsint_3_column_layout_structure(self) -> None:
        """Verify presence of 3-column layout: Sidebar, Canvas, and Inspector."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        html_out = adapter.render_excalidraw_scene_html(trace, locale="vi")

        # Layout container
        assert 'class="flowsint-layout"' in html_out
        assert 'class="flowsint-sidebar"' in html_out
        assert 'class="flowsint-canvas-wrapper"' in html_out
        assert 'flowsint-inspector' in html_out

        # Search bar and entity items
        assert 'class="search-input"' in html_out
        assert 'class="entity-item"' in html_out
        assert 'data-node-ref="cit1"' in html_out
        assert 'data-node-ref="document:local_cases/docs/Bao_cao_kiem_toan_kho.pdf"' in html_out

        # Inspector controls
        assert 'id="scene-detail-title"' in html_out
        assert 'id="scene-detail-content"' in html_out
        assert 'class="copy-btn"' in html_out

    def test_flowsint_pill_nodes_on_canvas(self) -> None:
        """Verify canvas renders compact pill nodes with rx='20' and icon badges."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        html_out = adapter.render_excalidraw_scene_html(trace, locale="vi")

        # Pill geometry
        assert 'rx="20"' in html_out
        assert 'class="scene-pill-text"' in html_out
        assert 'class="scene-node egv-node-card' in html_out

        # Ensure no raw escaped <tspan> in output
        assert "&lt;tspan" not in html_out

    def test_flowsint_multilingual_i18n(self) -> None:
        """Verify localized UI headers across VI, JA, and ZH-CN."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        # 1. Vietnamese
        trace_vi = _make_sample_trace(locale="vi")
        html_vi = adapter.render_excalidraw_scene_html(trace_vi, locale="vi")
        assert "Danh sách thực thể" in html_vi
        assert "Bảng kiểm tra bằng chứng" in html_vi
        assert "Tìm kiếm thực thể" in html_vi

        # 2. Japanese
        trace_ja = _make_sample_trace(
            query="在庫同期エラー",
            answer_text="監査レポート [1] でエラー ORA-001 が検出されました。",
            locale="ja",
        )
        html_ja = adapter.render_excalidraw_scene_html(trace_ja, locale="ja")
        assert "エンティティ一覧" in html_ja
        assert "根拠インスペクター" in html_ja
        assert "エンティティを検索..." in html_ja

        # 3. Simplified Chinese
        trace_zh = _make_sample_trace(
            query="库存同步错误",
            answer_text="审计报告 [1] 中记录了错误代码 ERR_SYNC。",
            locale="zh-CN",
        )
        html_zh = adapter.render_excalidraw_scene_html(trace_zh, locale="zh-CN")
        assert "实体列表" in html_zh
        assert "证据检查面板" in html_zh
        assert "搜索实体..." in html_zh

    def test_flowsint_verbatim_preservation_in_embedded_payload(self) -> None:
        """Verify full un-truncated snippets and error codes are preserved verbatim in JSON payload."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        html_out = adapter.render_excalidraw_scene_html(trace, locale="vi")

        # Verbatim error code & sensitive terms must exist in the embedded payload
        assert "ERR_KHO_SYNC_0x80040111" in html_out
        assert "Bao_cao_kiem_toan_kho.pdf" in html_out
        assert "Huong_dan_may_quet.docx" in html_out

    def test_flowsint_zero_cloud_egress_offline_safety(self) -> None:
        """Verify no external network dependencies or remote scripts are embedded."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        html_out = adapter.render_excalidraw_scene_html(trace, locale="vi")

        # Zero Cloud Egress invariants
        assert "http://" not in html_out
        assert "https://" not in html_out
        assert "<script src=" not in html_out
        assert "<link rel=\"stylesheet\" href=\"http" not in html_out

    def test_flowsint_atlas_edge_labels_never_collide_with_node_cards(self) -> None:
        """Verify that edge relation labels (dẫn chứng cho, chứa đoạn) never collide with node cards."""
        import re

        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")

        # Extract all edge-label boxes
        edge_labels = re.findall(
            r'<g class="edge-label"><rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"',
            atlas_html,
        )
        # Extract all node card boxes
        node_cards = re.findall(
            r'<g class="[^"]*node[^"]*"[^>]*><rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"',
            atlas_html,
        )

        assert len(node_cards) > 0, "Atlas must contain node cards"

        for lx, ly, lw, lh in edge_labels:
            lx1, ly1, lx2, ly2 = float(lx), float(ly), float(lx) + float(lw), float(ly) + float(lh)
            for nx, ny, nw, nh in node_cards:
                nx1, ny1, nx2, ny2 = float(nx), float(ny), float(nx) + float(nw), float(ny) + float(nh)
                # AABB collision condition: both intervals overlap in X and Y
                overlaps = not (lx2 <= nx1 or lx1 >= nx2 or ly2 <= ny1 or ly1 >= ny2)
                assert not overlaps, (
                    f"Collision detected between edge label at [{lx1}, {ly1}, {lx2}, {ly2}] "
                    f"and node card at [{nx1}, {ny1}, {nx2}, {ny2}]"
                )

    def test_flowsint_floating_canvas_toolbar(self) -> None:
        """Verify presence of floating toolbar with Zoom, Fit, Fullscreen, and Collapse controls."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")

        # 1. Check in Atlas HTML
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")
        assert 'class="atlas-floating-toolbar"' in atlas_html
        assert 'id="atlas-btn-zoom-in"' in atlas_html
        assert 'id="atlas-btn-zoom-out"' in atlas_html
        assert 'id="atlas-btn-fit"' in atlas_html
        assert 'id="atlas-btn-fullscreen"' in atlas_html
        assert 'id="atlas-toggle-inspector"' in atlas_html

        # 2. Check in Inline Scene HTML
        scene_html = adapter.render_excalidraw_scene_html(trace, locale="vi")
        assert 'class="scene-floating-toolbar"' in scene_html
        assert 'id="scene-btn-zoom-in"' in scene_html
        assert 'id="scene-btn-zoom-out"' in scene_html
        assert 'id="scene-btn-fit"' in scene_html
        assert 'id="scene-btn-fullscreen"' in scene_html
        assert 'id="scene-btn-toggle-inspector"' in scene_html

    def test_flowsint_smooth_cubic_bezier_edges_and_neon_marker(self) -> None:
        """Verify straight lines are replaced with smooth Cubic Bezier paths and neon markers."""
        import re

        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")

        # 1. No straight <line class="edge..."> remaining
        assert not re.search(r'<line\s+[^>]*class="[^"]*edge[^"]*"', atlas_html), (
            "Atlas must not contain rigid straight <line class='edge...'>"
        )

        # 2. Contains Cubic Bezier <path d="M... C...">
        bezier_paths = re.findall(r'<path\s+[^>]*d="M\s*[^"]+C\s*[^"]+"[^>]*class="[^"]*edge[^"]*"', atlas_html)
        assert len(bezier_paths) > 0, "Atlas must contain smooth Cubic Bezier edge paths"

        # 3. Neon marker arrowhead with stroke #38bdf8
        assert 'marker id="atlas-arrow"' in atlas_html
        assert 'stroke="#38bdf8"' in atlas_html

        # 4. Animated pulse keyframes in CSS
        assert "@keyframes flowDash" in atlas_html

    def test_flowsint_collapsible_inspector_with_confidence_gauge_and_connections(self) -> None:
        """Verify collapsible inspector with graphical confidence gauge and bidirectional connection chips."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")

        # 1. Atlas Inspector
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")
        assert 'id="atlas-confidence-box"' in atlas_html
        assert 'class="gauge-track"' in atlas_html
        assert 'id="atlas-conf-fill"' in atlas_html
        assert 'id="atlas-links-box"' in atlas_html
        assert 'id="atlas-in-chips"' in atlas_html
        assert 'id="atlas-out-chips"' in atlas_html

        # 2. Scene Inspector
        scene_html = adapter.render_excalidraw_scene_html(trace, locale="vi")
        assert 'id="inspector-gauge-container"' in scene_html
        assert 'id="inspector-gauge-bar"' in scene_html
        assert 'id="inspector-links-container"' in scene_html
        assert 'id="scene-inbound-chips"' in scene_html
        assert 'id="scene-outbound-chips"' in scene_html

    def test_flowsint_realtime_search_and_pan_zoom_controller(self) -> None:
        """Verify realtime search input and pan/zoom interaction engine in controller."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")

        # Search box in header toolbar
        assert 'id="atlas-search-input"' in atlas_html
        assert 'class="atlas-search-box"' in atlas_html

        # Pan & Zoom events in JS
        assert "isPanning" in atlas_html
        assert "updateTransform" in atlas_html
        assert "wheel" in atlas_html
        assert "scale" in atlas_html

    def test_flowsint_mini_radar_inspector_ego_graph(self) -> None:
        """Verify Mini Radar Inspector (Ego Graph / Neighbors Ring) presence and localization."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")

        # 1. Atlas Mini Radar
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")
        assert 'id="atlas-mini-radar-container"' in atlas_html
        assert 'class="mini-radar-card"' in atlas_html
        assert 'class="radar-orbit"' in atlas_html
        assert 'id="atlas-radar-rays"' in atlas_html
        assert 'id="atlas-radar-neighbors"' in atlas_html
        assert "updateAtlasMiniRadar" in atlas_html
        assert "Định vị lân cận (Radar)" in atlas_html

        # 2. Scene Mini Radar
        scene_html = adapter.render_excalidraw_scene_html(trace, locale="vi")
        assert 'id="mini-radar-container"' in scene_html
        assert 'class="mini-radar-card"' in scene_html
        assert 'id="mini-radar-count"' in scene_html
        assert 'class="radar-orbit"' in scene_html
        assert 'id="radar-rays"' in scene_html
        assert 'id="radar-neighbors"' in scene_html
        assert "updateMiniRadar" in scene_html
        assert "Định vị lân cận (Radar)" in scene_html

        # 3. Multilingual radar titles
        scene_ja = adapter.render_excalidraw_scene_html(trace, locale="ja")
        assert "近傍レーダー" in scene_ja

        scene_zh = adapter.render_excalidraw_scene_html(trace, locale="zh-CN")
        assert "邻近雷达" in scene_zh

    def test_flowsint_force_directed_galaxy_and_micro_dots(self) -> None:
        """Verify Force-Directed Galaxy simulation engine, drag physics, and micro-dots LOD."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        scene_html = adapter.render_excalidraw_scene_html(trace, locale="vi")

        # Layout toggle button
        assert 'id="scene-btn-toggle-layout"' in scene_html
        assert 'class="scene-tool-btn active-mode"' in scene_html

        # Force simulation physics engine in JS
        assert "initForceSimulation" in scene_html
        assert "physicsTick" in scene_html
        assert "kRepel" in scene_html
        assert "kSpring" in scene_html
        assert "kGravity" in scene_html
        assert "draggedNode" in scene_html
        assert "switchLayout" in scene_html

        # Micro-dots for citations/chunks
        assert "micro-dot" in scene_html
        assert "galaxy-mode" in scene_html

    def test_flowsint_concentric_celestial_orbits_and_mini_radar_containment(self) -> None:
        """Verify concentric celestial orbit backdrop, AABB box collision, and mini radar containment."""
        adapter = ExcaliFlowAdapter()
        if not adapter.is_available():
            pytest.skip("ExcaliFlowAdapter not available in this environment")

        trace = _make_sample_trace(locale="vi")
        scene_html = adapter.render_excalidraw_scene_html(trace, locale="vi")
        atlas_html = adapter.render_evidence_atlas_html(trace, locale="vi")

        # 1. Mini Radar containment & CSS scoping
        assert "#mini-radar-svg" in scene_html
        assert "min-width: 0 !important;" in scene_html
        assert "width: 160px !important;" in scene_html
        assert ".scene-board svg" in scene_html

        assert "#atlas-mini-radar-svg" in atlas_html
        assert "min-width: 0 !important;" in atlas_html
        assert "width: 160px !important;" in atlas_html
        assert ".atlas-viewport svg" in atlas_html

        # 2. Celestial Concentric Orbits Backdrop in Scene
        assert 'id="galaxy-backdrop"' in scene_html
        assert 'class="galaxy-orbit-backdrop"' in scene_html
        assert 'class="celestial-orbit orbit-core"' in scene_html
        assert 'class="celestial-orbit orbit-mid"' in scene_html
        assert 'class="celestial-orbit orbit-outer"' in scene_html
        assert 'class="celestial-axis"' in scene_html

        # 3. AABB Collision Resolution in Physics Simulation
        assert "overlapX" in scene_html
        assert "overlapY" in scene_html
        assert "idealRadius" in scene_html
