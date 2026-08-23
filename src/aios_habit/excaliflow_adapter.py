# -*- coding: utf-8 -*-
"""Pure Python In-Process ExcaliFlow & Evidence Graph Adapter for AIOS WorkLens.

Milestone: Commit D (Milestone 1)
Key Guarantees:
1. Zero CLI Execution: In-process Python rendering only.
2. Zero Global PATH Search: No calls to external binaries.
3. Pure In-Process Rendering: Interfaces directly with AIOS WorkLens view models and renderers.
4. Multilingual CJK & Vietnamese Typography: High-fidelity font fallback stack across OS platforms.
5. Fail-Safe Offline Isolation: Catches exceptions and returns localized error fallback cards.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union

from aios_habit.evidence_graph_viewer import (
    EvidenceGraphViewModel,
    build_evidence_graph_view_model,
    render_evidence_graph_html,
)
from aios_habit.evidence_trace_schema import EvidenceTrace
from aios_habit.i18n import DEFAULT_LOCALE, normalize_locale, t

LOGGER = logging.getLogger(__name__)

# Multilingual font stacks ensuring crisp typography across Windows, macOS, Linux, Android
CJK_MULTI_LOCALE_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, '
    '"Noto Sans", "Noto Sans CJK SC", "Noto Sans CJK JP", "Microsoft YaHei", "Yu Gothic", '
    '"Meiryo", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", sans-serif'
)

CJK_MONOSPACE_FONT_STACK = (
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", '
    '"Noto Sans Mono CJK SC", "Noto Sans Mono CJK JP", monospace'
)


class CapabilityStatus(str, Enum):
    """Lifecycle and readiness status for rendering capabilities."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


@dataclass
class ExcaliFlowCapabilities:
    """Dataclass describing the availability and feature matrix of ExcaliFlow adapter."""
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    is_available: bool = True
    has_html_renderer: bool = True
    has_svg_renderer: bool = True
    has_excalidraw_export: bool = True
    renderer_version: str = "1.0.0"
    supported_formats: List[str] = field(
        default_factory=lambda: ["html", "svg", "excalidraw", "json"]
    )
    missing_dependencies: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary format."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


class _ExcaliFlowCapabilitiesMethod:
    """Descriptor enabling check_capabilities to be invoked on class or instance seamlessly."""

    def __init__(self, func: Any) -> None:
        self.func = func

    def __get__(self, instance: Optional[ExcaliFlowAdapter], owner: Optional[type] = None) -> Any:
        if instance is None:
            return lambda: owner._check_capabilities_impl(owner)  # type: ignore
        return lambda: instance._check_capabilities_impl(instance)


class ExcaliFlowAdapter:
    """Pure in-process Python adapter for ExcaliFlow and Evidence Graph visual artifacts."""

    def __init__(
        self,
        override_available: Optional[bool] = None,
        override_status: Optional[CapabilityStatus] = None,
    ) -> None:
        self._override_available = override_available
        self._override_status = override_status
        if override_status is not None and override_available is None:
            self._override_available = (override_status != CapabilityStatus.UNAVAILABLE)
        elif override_available is not None and override_status is None:
            self._override_status = (
                CapabilityStatus.AVAILABLE if override_available else CapabilityStatus.UNAVAILABLE
            )

    @classmethod
    def _check_capabilities_impl(cls_or_self, target: Any) -> ExcaliFlowCapabilities:
        """Evaluate and return runtime rendering capabilities."""
        if isinstance(target, ExcaliFlowAdapter):
            if target._override_status is not None or target._override_available is not None:
                is_avail = (
                    target._override_available
                    if target._override_available is not None
                    else (target._override_status != CapabilityStatus.UNAVAILABLE)
                )
                status = (
                    target._override_status
                    if target._override_status is not None
                    else (CapabilityStatus.AVAILABLE if is_avail else CapabilityStatus.UNAVAILABLE)
                )
                return ExcaliFlowCapabilities(
                    status=status,
                    is_available=is_avail,
                    has_html_renderer=is_avail,
                    has_svg_renderer=is_avail,
                    has_excalidraw_export=is_avail,
                    renderer_version="1.0.0",
                    supported_formats=["html", "svg", "excalidraw", "json"] if is_avail else [],
                    missing_dependencies=["simulated_override"] if not is_avail else [],
                    details={"external_cli": False, "in_process": True, "override": True},
                )

        # In-process standard capabilities with real excaliflow package detection
        excaliflow_pkg_available = False
        excaliflow_version = "none"
        try:
            import importlib
            if importlib.util.find_spec("excaliflow") is not None:
                import excaliflow
                excaliflow_pkg_available = True
                excaliflow_version = getattr(excaliflow, "__version__", "0.1.1")
        except Exception:
            pass

        return ExcaliFlowCapabilities(
            status=CapabilityStatus.AVAILABLE,
            is_available=True,
            has_html_renderer=True,
            has_svg_renderer=True,
            has_excalidraw_export=True,
            renderer_version=excaliflow_version if excaliflow_pkg_available else "1.0.0",
            supported_formats=["html", "svg", "excalidraw", "json"],
            missing_dependencies=[],
            details={
                "external_cli": False,
                "in_process": True,
                "excaliflow_package_installed": excaliflow_pkg_available,
                "excaliflow_version": excaliflow_version,
                "font_stack": CJK_MULTI_LOCALE_FONT_STACK,
            },
        )

    check_capabilities = _ExcaliFlowCapabilitiesMethod(_check_capabilities_impl)

    def is_available(self) -> bool:
        """Quick boolean availability check."""
        return self.check_capabilities().is_available

    @staticmethod
    def to_canonical_excaliflow_trace(trace_or_dict: Union[EvidenceTrace, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert EvidenceTrace or trace dict into ExcaliFlow canonical rag-trace/v1 format."""
        if hasattr(trace_or_dict, "to_dict"):
            raw = trace_or_dict.to_dict()
        elif isinstance(trace_or_dict, dict):
            raw = trace_or_dict
        else:
            raw = asdict(trace_or_dict)

        nodes = raw.get("nodes", [])
        documents = []
        chunks = []
        citations = []
        doc_ids = set()

        query = raw.get("query", "")
        answer_text = raw.get("answer_text", "")
        for n in nodes:
            ntype = n.get("node_type")
            if ntype == "question" and not query:
                query = n.get("snippet", "")
            elif ntype == "answer" and not answer_text:
                answer_text = n.get("snippet", "")
            elif ntype == "source":
                doc_id = n.get("id") or f"doc-{len(documents) + 1}"
                if doc_id not in doc_ids:
                    doc_ids.add(doc_id)
                    documents.append({
                        "id": doc_id,
                        "location": n.get("source_path") or n.get("title") or doc_id,
                        "title": n.get("title") or n.get("source_path") or doc_id,
                    })
            elif ntype == "citation":
                cid = n.get("id") or f"chunk-{len(chunks) + 1}"
                src_id = n.get("metadata", {}).get("source_id") or (documents[0]["id"] if documents else "doc-1")
                if src_id not in doc_ids:
                    doc_ids.add(src_id)
                    documents.append({
                        "id": src_id,
                        "location": n.get("source_path") or src_id,
                        "title": n.get("source_path") or src_id,
                    })
                chunks.append({
                    "id": cid,
                    "document_id": src_id,
                    "text": n.get("snippet") or n.get("title") or cid,
                    "location": n.get("source_path") or "document",
                    "score": float(n.get("confidence") or 1.0),
                })
                citations.append(cid)

        if not documents:
            documents.append({"id": "doc-default", "location": "local_document", "title": "Tài liệu cục bộ"})
        if not chunks:
            chunks.append({
                "id": "chunk-default",
                "document_id": documents[0]["id"],
                "text": "Đoạn bằng chứng",
                "location": documents[0]["location"],
                "score": 1.0,
            })
            citations.append("chunk-default")

        return {
            "schema_version": "rag-trace/v1",
            "query": query or "Truy vấn",
            "title": raw.get("title") or query or "Trace bằng chứng",
            "documents": documents,
            "chunks": chunks,
            "answer": {
                "id": "answer-1",
                "text": answer_text or "Câu trả lời",
                "citations": citations,
            },
        }

    def render_evidence_atlas_html(
        self,
        trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
        locale: str = DEFAULT_LOCALE,
    ) -> str:
        """Render evidence trace using genuine ExcaliFlow Studio knowledge & atlas engine."""
        import excaliflow.knowledge as ek
        import excaliflow.evidence_atlas as ea

        canonical = self.to_canonical_excaliflow_trace(trace_or_dict)
        graph = ek.graph_from_rag_trace(canonical)
        return ea.build_evidence_atlas_html(graph)

    def render_trace_html(
        self,
        trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
        locale: str = DEFAULT_LOCALE,
        use_cache: bool = True,
        engine: str = "auto",
    ) -> str:
        """Render localized evidence graph HTML visualization safely in-process.

        Args:
            trace_or_dict: EvidenceTrace instance or raw dictionary representation.
            locale: UI locale ('vi', 'ja', 'zh-CN').
            use_cache: Whether to check and populate thread-safe cache.
            engine: Rendering engine ('auto', 'excaliflow', 'view_model').

        Returns:
            HTML string containing complete self-contained visualization or fail-safe error card.
        """
        norm_loc = normalize_locale(locale)
        caps = self.check_capabilities()
        if not caps.is_available or caps.status == CapabilityStatus.UNAVAILABLE:
            err_msg = t("evidence_graph_render_error", locale=norm_loc)
            return (
                f'<div class="egv-container egv-error" style="background:#261313; '
                f'border:1px solid #991b1b; border-radius:10px; padding:16px 20px; '
                f'color:#fca5a5; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0;">'
                f'<div style="display:flex; align-items:center; gap:8px; font-size:14px; font-weight:600; color:#ef4444;">'
                f'<span>❌</span>'
                f'<span>{html.escape(err_msg)}</span></div></div>'
            )

        try:
            if engine == "excaliflow":
                return self.render_evidence_atlas_html(trace_or_dict, locale=norm_loc)
            return render_evidence_graph_html(trace_or_dict, locale=norm_loc, use_cache=use_cache)
        except Exception as exc:
            LOGGER.exception("ExcaliFlowAdapter: HTML rendering failed: %s", exc)
            err_msg = t("evidence_graph_render_error", locale=norm_loc)
            return (
                f'<div class="egv-container egv-error" style="background:#261313; '
                f'border:1px solid #991b1b; border-radius:10px; padding:16px 20px; '
                f'color:#fca5a5; font-family:{CJK_MULTI_LOCALE_FONT_STACK}; margin:10px 0;">'
                f'<div style="display:flex; align-items:center; gap:8px; font-size:14px; font-weight:600; color:#ef4444;">'
                f'<span>❌</span>'
                f'<span>{html.escape(err_msg)}</span></div></div>'
            )

    def export_excalidraw_scene(
        self,
        trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
        locale: str = DEFAULT_LOCALE,
    ) -> Dict[str, Any]:
        """Export evidence trace as an Excalidraw scene JSON dictionary.

        Args:
            trace_or_dict: EvidenceTrace instance or raw dictionary.
            locale: UI locale ('vi', 'ja', 'zh-CN').

        Returns:
            Excalidraw scene dictionary with structured visual elements.
        """
        norm_loc = normalize_locale(locale)
        caps = self.check_capabilities()
        if not caps.is_available or caps.status == CapabilityStatus.UNAVAILABLE:
            raise RuntimeError(
                f"ExcaliFlowAdapter renderer is unavailable in current runtime: status={caps.status.value}"
            )

        view_model: EvidenceGraphViewModel = build_evidence_graph_view_model(trace_or_dict, locale=norm_loc)

        if view_model.is_insufficient:
            notice = view_model.notice or t("evidence_graph_insufficient", locale=norm_loc)
            return {
                "type": "excalidraw",
                "version": 2,
                "source": "aios_habit.excaliflow_adapter",
                "elements": [
                    {
                        "id": "insufficient_box",
                        "type": "rectangle",
                        "x": 100,
                        "y": 100,
                        "width": 640,
                        "height": 100,
                        "strokeColor": "#f59e0b",
                        "backgroundColor": "#451a03",
                        "fillStyle": "solid",
                        "strokeWidth": 2,
                        "roughness": 0,
                    },
                    {
                        "id": "insufficient_text",
                        "type": "text",
                        "x": 120,
                        "y": 135,
                        "width": 600,
                        "height": 30,
                        "text": f"⚠️ {notice}",
                        "fontSize": 16,
                        "fontFamily": 1,
                        "strokeColor": "#fef3c7",
                    },
                ],
                "appState": {"viewBackgroundColor": "#0f172a", "gridSize": None},
                "files": {},
            }

        elements: List[Dict[str, Any]] = []

        # Color schemes matching dark theme
        bg_colors = {
            "question": "#1e3a8a",
            "answer": "#064e3b",
            "citation": "#581c87",
            "source": "#1e293b",
        }
        border_colors = {
            "question": "#3b82f6",
            "answer": "#10b981",
            "citation": "#a855f7",
            "source": "#64748b",
        }

        # Layout coordinates mapping
        col_x = {
            "question": 80,
            "answer": 80,
            "citation": 520,
            "source": 960,
        }

        node_positions: Dict[str, Dict[str, float]] = {}
        y_counters: Dict[str, float] = {
            "question": 100.0,
            "answer": 260.0,
            "citation": 100.0,
            "source": 100.0,
        }

        card_width = 360.0
        card_height = 120.0

        for node in view_model.nodes:
            nid = node["id"]
            ntype = node["node_type"]
            x = col_x.get(ntype, 100.0)
            y = y_counters.get(ntype, 100.0)
            y_counters[ntype] = y + card_height + 30.0

            node_positions[nid] = {"x": x, "y": y, "width": card_width, "height": card_height}

            # Node background card
            rect_elem = {
                "id": f"node_{nid}_rect",
                "type": "rectangle",
                "x": x,
                "y": y,
                "width": card_width,
                "height": card_height,
                "strokeColor": border_colors.get(ntype, "#64748b"),
                "backgroundColor": bg_colors.get(ntype, "#1e293b"),
                "fillStyle": "solid",
                "strokeWidth": 1.5,
                "roughness": 0,
                "roundness": {"type": 3},
            }
            elements.append(rect_elem)

            # Node title text
            title_text = node.get("title", "")
            title_elem = {
                "id": f"node_{nid}_title",
                "type": "text",
                "x": x + 12.0,
                "y": y + 10.0,
                "width": card_width - 24.0,
                "height": 20.0,
                "text": f"{node.get('badge_label', ntype.upper())}: {title_text[:40]}",
                "fontSize": 13,
                "fontFamily": 1,
                "strokeColor": "#f8fafc",
            }
            elements.append(title_elem)

            # Snippet excerpt text
            snippet = node.get("snippet", "")
            if snippet:
                snippet_clean = snippet.replace("\n", " ")[:75]
                snippet_elem = {
                    "id": f"node_{nid}_snippet",
                    "type": "text",
                    "x": x + 12.0,
                    "y": y + 40.0,
                    "width": card_width - 24.0,
                    "height": 60.0,
                    "text": snippet_clean,
                    "fontSize": 11,
                    "fontFamily": 1,
                    "strokeColor": "#cbd5e1",
                }
                elements.append(snippet_elem)

        # Edges (connecting arrows)
        for i, edge in enumerate(view_model.edges):
            src_id = edge["source_id"]
            tgt_id = edge["target_id"]
            if src_id in node_positions and tgt_id in node_positions:
                src_pos = node_positions[src_id]
                tgt_pos = node_positions[tgt_id]

                start_x = src_pos["x"] + src_pos["width"]
                start_y = src_pos["y"] + (src_pos["height"] / 2.0)
                end_x = tgt_pos["x"]
                end_y = tgt_pos["y"] + (tgt_pos["height"] / 2.0)

                arrow_elem = {
                    "id": f"edge_{i}_{src_id}_{tgt_id}",
                    "type": "arrow",
                    "x": start_x,
                    "y": start_y,
                    "width": end_x - start_x,
                    "height": end_y - start_y,
                    "points": [[0, 0], [end_x - start_x, end_y - start_y]],
                    "strokeColor": "#94a3b8",
                    "strokeWidth": 1.5,
                    "roughness": 0,
                    "endArrowhead": "arrow",
                }
                elements.append(arrow_elem)

        return {
            "type": "excalidraw",
            "version": 2,
            "source": "aios_habit.excaliflow_adapter",
            "elements": elements,
            "appState": {
                "viewBackgroundColor": "#0f172a",
                "gridSize": None,
            },
            "files": {},
        }

    def render_trace_svg(
        self,
        trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
        locale: str = DEFAULT_LOCALE,
    ) -> str:
        """Render evidence graph as a standalone vector SVG string with multi-locale font stack.

        Args:
            trace_or_dict: EvidenceTrace instance or raw dictionary.
            locale: UI locale ('vi', 'ja', 'zh-CN').

        Returns:
            SVG XML markup string.
        """
        norm_loc = normalize_locale(locale)
        caps = self.check_capabilities()
        if not caps.is_available or caps.status == CapabilityStatus.UNAVAILABLE:
            err_msg = t("evidence_graph_render_error", locale=norm_loc)
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="120" viewBox="0 0 600 120">'
                f'<rect width="600" height="120" rx="8" fill="#450a0a" stroke="#dc2626" stroke-width="2"/>'
                f'<text x="20" y="65" fill="#fca5a5" font-family="{CJK_MULTI_LOCALE_FONT_STACK}" font-size="16">'
                f'❌ {html.escape(err_msg)}</text></svg>'
            )

        view_model: EvidenceGraphViewModel = build_evidence_graph_view_model(trace_or_dict, locale=norm_loc)

        if view_model.is_insufficient:
            notice = view_model.notice or t("evidence_graph_insufficient", locale=norm_loc)
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="100" viewBox="0 0 640 100">'
                f'<rect width="640" height="100" rx="8" fill="#451a03" stroke="#f59e0b" stroke-width="2"/>'
                f'<text x="24" y="55" fill="#fef3c7" font-family="{CJK_MULTI_LOCALE_FONT_STACK}" font-size="15" font-weight="bold">'
                f'⚠️ {html.escape(notice)}</text></svg>'
            )

        # Colors
        bg_colors = {
            "question": "#1e3a8a",
            "answer": "#064e3b",
            "citation": "#581c87",
            "source": "#1e293b",
        }
        border_colors = {
            "question": "#3b82f6",
            "answer": "#10b981",
            "citation": "#a855f7",
            "source": "#64748b",
        }

        col_x = {"question": 60, "answer": 60, "citation": 520, "source": 980}
        y_counters: Dict[str, float] = {"question": 80.0, "answer": 260.0, "citation": 80.0, "source": 80.0}
        node_coords: Dict[str, Dict[str, float]] = {}

        card_w = 380.0
        card_h = 130.0

        nodes_svg_parts = []
        for node in view_model.nodes:
            nid = node["id"]
            ntype = node["node_type"]
            x = col_x.get(ntype, 60.0)
            y = y_counters.get(ntype, 80.0)
            y_counters[ntype] = y + card_h + 30.0

            node_coords[nid] = {"x": x, "y": y, "w": card_w, "h": card_h}

            bg = bg_colors.get(ntype, "#1e293b")
            border = border_colors.get(ntype, "#64748b")
            title = html.escape(str(node.get("title", "")))
            badge = html.escape(str(node.get("badge_label", ntype.upper())))
            snippet = html.escape(str(node.get("snippet", ""))[:80])

            nodes_svg_parts.append(
                f'<g id="node_{html.escape(nid)}">'
                f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1.5"/>'
                f'<text x="{x+14}" y="{y+26}" fill="#93c5fd" font-family="{CJK_MULTI_LOCALE_FONT_STACK}" font-size="11" font-weight="bold">{badge}</text>'
                f'<text x="{x+14}" y="{y+48}" fill="#f8fafc" font-family="{CJK_MULTI_LOCALE_FONT_STACK}" font-size="13" font-weight="600">{title[:80]}</text>'
                f'<text x="{x+14}" y="{y+75}" fill="#cbd5e1" font-family="{CJK_MULTI_LOCALE_FONT_STACK}" font-size="11">{snippet}</text>'
                f'</g>'
            )

        # Calculate dynamic SVG dimensions based on layout
        svg_width = 1400
        svg_height = max(600, int(max(y_counters.values()) + 60))

        # Edges SVG parts
        edges_svg_parts = []
        for edge in view_model.edges:
            src_id = edge["source_id"]
            tgt_id = edge["target_id"]
            if src_id in node_coords and tgt_id in node_coords:
                sc = node_coords[src_id]
                tc = node_coords[tgt_id]
                x1 = sc["x"] + sc["w"]
                y1 = sc["y"] + (sc["h"] / 2.0)
                x2 = tc["x"]
                y2 = tc["y"] + (tc["h"] / 2.0)

                edges_svg_parts.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#arrowhead)"/>'
                )

        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">'
            f'<defs>'
            f'<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">'
            f'<polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8"/>'
            f'</marker>'
            f'</defs>'
            f'<rect width="{svg_width}" height="{svg_height}" fill="#0f172a"/>'
            f'{"".join(edges_svg_parts)}'
            f'{"".join(nodes_svg_parts)}'
            f'</svg>'
        )
        return svg_content

    @staticmethod
    def get_excaliflow_module() -> Optional[Any]:
        """Return the underlying in-process excaliflow module if installed."""
        try:
            import excaliflow
            return excaliflow
        except ImportError:
            return None


__all__ = [
    "CJK_MULTI_LOCALE_FONT_STACK",
    "CJK_MONOSPACE_FONT_STACK",
    "CapabilityStatus",
    "ExcaliFlowCapabilities",
    "ExcaliFlowAdapter",
]
