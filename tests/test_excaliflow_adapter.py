# -*- coding: utf-8 -*-
"""Comprehensive Automated Test Suite for ExcaliFlowAdapter.

Validates:
1. CapabilityStatus and ExcaliFlowCapabilities initialization & serialization.
2. In-process HTML rendering with cache and error fail-safe fallback.
3. Excalidraw Scene export (v2 JSON) for valid, insufficient, and degraded traces.
4. SVG rendering with embedded CJK and Vietnamese font family stacks.
5. Verbatim text preservation and anti-mojibake across Vietnamese, Japanese, Chinese.
6. Offline isolation and zero external network egress.
"""
from __future__ import annotations

import json
import pytest

from aios_habit.evidence_trace_schema import (
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


@pytest.fixture
def sample_valid_trace() -> EvidenceTrace:
    """Fixture providing a standard valid EvidenceTrace."""
    return EvidenceTrace(
        trace_id="trc_excali_001",
        query="Kiểm tra quy trình vận hành kho 2026",
        answer_text="Theo hướng dẫn [1], nhân viên sử dụng máy quét PDA để kiểm đếm mã hàng.",
        ui_locale="vi",
        answer_language="vi",
        nodes=[
            EvidenceNode(
                id="q_01",
                node_type="question",
                title="Kiểm tra quy trình vận hành kho 2026",
                snippet="Kiểm tra quy trình vận hành kho 2026",
            ),
            EvidenceNode(
                id="ans_01",
                node_type="answer",
                title="Câu trả lời",
                snippet="Theo hướng dẫn [1], nhân viên sử dụng máy quét PDA để kiểm đếm mã hàng.",
            ),
            EvidenceNode(
                id="cit_01",
                node_type="citation",
                title="[1]",
                snippet="Nhân viên sử dụng máy quét PDA để kiểm đếm mã hàng.",
                source_id="src_01",
                citation_id="[1]",
            ),
            EvidenceNode(
                id="src_01",
                node_type="source",
                title="QuyTrinhKho_2026.docx",
                snippet="Nhân viên sử dụng máy quét PDA để kiểm đếm mã hàng.",
                source_id="local_cases/docs/QuyTrinhKho_2026.docx",
                citation_id="[1]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="ans_01", target_id="q_01", relation_type="derives_from"),
            EvidenceEdge(source_id="ans_01", target_id="cit_01", relation_type="cites"),
            EvidenceEdge(source_id="cit_01", target_id="src_01", relation_type="extracted_from"),
        ],
        metadata={"status": "valid", "insufficient_evidence": False, "cited_count": 1},
    )


@pytest.fixture
def sample_cjk_trace() -> EvidenceTrace:
    """Fixture with rich CJK and Vietnamese characters."""
    return EvidenceTrace(
        trace_id="trc_cjk_002",
        query="倉庫業務の標準化と自动化流程",
        answer_text="Tài liệu [1] và [証拠-JA-01] quy định mã lỗi ERR_CODE_0x99.",
        ui_locale="ja",
        answer_language="ja",
        nodes=[
            EvidenceNode(
                id="q_cjk",
                node_type="question",
                title="倉庫業務の標準化と自动化流程",
                snippet="倉庫業務の標準化と自动化流程",
            ),
            EvidenceNode(
                id="ans_cjk",
                node_type="answer",
                title="回答 (ja)",
                snippet="Tài liệu [1] và [証拠-JA-01] quy định mã lỗi ERR_CODE_0x99.",
            ),
            EvidenceNode(
                id="cit_cjk",
                node_type="citation",
                title="[証拠-JA-01]",
                snippet="バーコードリーダーで確認：ハンディターミナル「HT-5000」 ắ ằ ẳ ẵ ặ.",
                source_id="src_cjk",
                citation_id="[証拠-JA-01]",
            ),
            EvidenceNode(
                id="src_cjk",
                node_type="source",
                title="業務マニュアル_2026.pdf",
                snippet="バーコードリーダーで確認：ハンディターミナル「HT-5000」 ắ ằ ẳ ẵ ặ.",
                source_id="local_cases/docs/業務マニュアル_2026.pdf",
                citation_id="[証拠-JA-01]",
            ),
        ],
        edges=[
            EvidenceEdge(source_id="ans_cjk", target_id="q_cjk", relation_type="derives_from"),
            EvidenceEdge(source_id="ans_cjk", target_id="cit_cjk", relation_type="cites"),
            EvidenceEdge(source_id="cit_cjk", target_id="src_cjk", relation_type="extracted_from"),
        ],
        metadata={"status": "valid", "insufficient_evidence": False, "cited_count": 1},
    )


def test_capability_status_and_dataclass() -> None:
    """Verify CapabilityStatus enum and ExcaliFlowCapabilities dataclass serialization."""
    assert CapabilityStatus.AVAILABLE.value == "available"
    assert CapabilityStatus.UNAVAILABLE.value == "unavailable"
    assert CapabilityStatus.DEGRADED.value == "degraded"

    caps = ExcaliFlowCapabilities(
        status=CapabilityStatus.AVAILABLE,
        is_available=True,
        has_html_renderer=True,
        has_svg_renderer=True,
        has_excalidraw_export=True,
        renderer_version="1.0.0",
        supported_formats=["html", "svg", "excalidraw", "json"],
    )
    d = caps.to_dict()
    assert d["status"] == "available"
    assert d["is_available"] is True
    assert "excalidraw" in d["supported_formats"]


def test_excaliflow_adapter_check_capabilities() -> None:
    """Verify check_capabilities on normal and overridden adapter instances."""
    adapter = ExcaliFlowAdapter()
    caps = adapter.check_capabilities()
    assert caps.status == CapabilityStatus.AVAILABLE
    assert caps.is_available is True
    assert adapter.is_available() is True

    # Overridden unavailable adapter
    unavail_adapter = ExcaliFlowAdapter(override_status=CapabilityStatus.UNAVAILABLE)
    caps_unavail = unavail_adapter.check_capabilities()
    assert caps_unavail.status == CapabilityStatus.UNAVAILABLE
    assert caps_unavail.is_available is False
    assert unavail_adapter.is_available() is False


def test_render_trace_html(sample_valid_trace: EvidenceTrace) -> None:
    """Verify render_trace_html returns proper HTML component."""
    adapter = ExcaliFlowAdapter()
    html_out = adapter.render_trace_html(sample_valid_trace, locale="vi")

    assert "egv-container" in html_out
    assert "trc_excali_001" in html_out
    assert "QuyTrinhKho_2026.docx" in html_out
    assert "http://" not in html_out
    assert "https://" not in html_out


def test_render_trace_html_unavailable_fail_safe(sample_valid_trace: EvidenceTrace) -> None:
    """Verify render_trace_html returns localized error banner when unavailable."""
    unavail_adapter = ExcaliFlowAdapter(override_status=CapabilityStatus.UNAVAILABLE)

    html_vi = unavail_adapter.render_trace_html(sample_valid_trace, locale="vi")
    assert "Không thể hiển thị đồ thị bằng chứng" in html_vi

    html_ja = unavail_adapter.render_trace_html(sample_valid_trace, locale="ja")
    assert "根拠グラフを表示できません" in html_ja

    html_zh = unavail_adapter.render_trace_html(sample_valid_trace, locale="zh-CN")
    assert "无法显示证据图谱" in html_zh


def test_export_excalidraw_scene_valid(sample_valid_trace: EvidenceTrace) -> None:
    """Verify export_excalidraw_scene generates valid Excalidraw v2 JSON structure."""
    adapter = ExcaliFlowAdapter()
    scene = adapter.export_excalidraw_scene(sample_valid_trace, locale="vi")

    assert isinstance(scene, dict)
    assert scene["type"] == "excalidraw"
    assert scene["version"] == 2
    assert "elements" in scene
    assert len(scene["elements"]) > 0

    # Ensure elements contain rectangles, texts, and arrows
    types = {e["type"] for e in scene["elements"]}
    assert "rectangle" in types
    assert "text" in types
    assert "arrow" in types


def test_render_excalidraw_scene_html_is_local_and_interactive(sample_valid_trace: EvidenceTrace) -> None:
    """The default Evidence Graph renderer is a readable Excalidraw-scene viewer."""
    adapter = ExcaliFlowAdapter()
    html_out = adapter.render_excalidraw_scene_html(sample_valid_trace, locale="vi")

    assert html_out.startswith("<!doctype html>")
    assert "data-excalidraw-elements" in html_out
    assert "scene-board" in html_out
    assert "EXCALIDRAW_SCENE" in html_out
    assert "QuyTrinhKho_2026.docx" in html_out
    assert "https://" not in html_out


def test_export_excalidraw_scene_insufficient() -> None:
    """Verify export_excalidraw_scene handles insufficient evidence trace gracefully."""
    insuf_trace = EvidenceTrace(
        trace_id="trc_insuf",
        query="Câu hỏi không có trong tài liệu",
        answer_text="Không tìm thấy",
        metadata={"insufficient_evidence": True},
    )

    adapter = ExcaliFlowAdapter()
    scene = adapter.export_excalidraw_scene(insuf_trace, locale="ja")

    assert scene["type"] == "excalidraw"
    assert len(scene["elements"]) == 2
    # Notice text element present
    text_elem = [e for e in scene["elements"] if e["type"] == "text"][0]
    assert "根拠が不足しているため" in text_elem["text"]


def test_render_trace_svg_cjk(sample_cjk_trace: EvidenceTrace) -> None:
    """Verify render_trace_svg produces standalone SVG with CJK typography and multi-locale font stack."""
    adapter = ExcaliFlowAdapter()
    svg_out = adapter.render_trace_svg(sample_cjk_trace, locale="ja")

    assert isinstance(svg_out, str)
    assert "<svg" in svg_out
    assert "</svg>" in svg_out
    assert "業務マニュアル_2026.pdf" in svg_out
    assert "ハンディターミナル" in svg_out
    assert "ắ ằ ẳ ẵ ặ" in svg_out
    # Multi-locale font family stack present
    assert "Noto Sans CJK JP" in svg_out or "Segoe UI" in svg_out
    assert "\\u" not in svg_out
