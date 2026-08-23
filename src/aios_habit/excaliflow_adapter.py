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

from collections import defaultdict
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


def _compact_scene_text(value: Any, limit: int = 96) -> str:
    """Keep the map scannable; full evidence remains available on node click."""
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1].rstrip()}…"


def _scene_text_lines(value: str, line_size: int, max_lines: int) -> List[str]:
    """Split Latin and CJK labels predictably without depending on browser wrap."""
    text = _compact_scene_text(value, line_size * max_lines)
    return [text[index:index + line_size] for index in range(0, len(text), line_size)][:max_lines] or ["—"]


def _build_evidence_scene_layout(view_model: EvidenceGraphViewModel) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """Create a compact, evidence-faithful layout for a hand-drawn scene.

    Source cards are grouped only by their existing ``source_id``. This does
    not create new evidence: it prevents the same document from being drawn
    repeatedly when several cited passages come from it.
    """
    cards: List[Dict[str, Any]] = []
    source_card_by_node_id: Dict[str, str] = {}
    source_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for node in view_model.nodes:
        if node["node_type"] == "source":
            source_groups[str(node.get("source_id") or node["title"])].append(node)

    def append_card(node: Dict[str, Any], *, x: int, y: int, card_id: Optional[str] = None, detail: Optional[str] = None, badge: str = "") -> None:
        cards.append({
            "id": card_id or str(node["id"]),
            "node_type": node["node_type"],
            "kind": str(node.get("type_label") or node["node_type"]),
            "title": str(node.get("title") or node["id"]),
            "summary": _compact_scene_text(node.get("snippet") or node.get("title")),
            "detail": detail if detail is not None else str(node.get("snippet") or node.get("title") or ""),
            "badge": badge or str(node.get("citation_id") or ""),
            "x": x,
            "y": y,
            "width": 250,
            "height": 108,
        })

    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "question"):
        append_card(node, x=55, y=70 + index * 128)
    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "answer"):
        append_card(node, x=355, y=70 + index * 128)
    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "citation"):
        append_card(node, x=670 + (index % 2) * 255, y=70 + (index // 2) * 128)

    for index, (source_key, nodes) in enumerate(source_groups.items()):
        first = nodes[0]
        group_id = f"document:{source_key}"
        citation_ids = [str(node.get("citation_id") or "") for node in nodes if node.get("citation_id")]
        grouped_detail = "\n\n".join(
            f"{node.get('citation_id') or node['id']}: {node.get('snippet') or ''}" for node in nodes
        )
        append_card(
            first,
            x=1190,
            y=70 + index * 132,
            card_id=group_id,
            detail=grouped_detail or str(first.get("snippet") or ""),
            badge=" ".join(citation_ids),
        )
        for node in nodes:
            source_card_by_node_id[str(node["id"])] = group_id

    card_ids = {str(card["id"]) for card in cards}
    edges: List[Dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for edge in view_model.edges:
        source_id = str(edge["source_id"])
        target_id = str(edge["target_id"])
        relation = str(edge.get("display_label") or edge.get("label") or edge.get("relation") or "")
        if str(edge.get("relation_type")) == "derives_from":
            source_id, target_id = target_id, source_id
        source_id = source_card_by_node_id.get(source_id, source_id)
        target_id = source_card_by_node_id.get(target_id, target_id)
        pair = (source_id, target_id)
        if source_id in card_ids and target_id in card_ids and source_id != target_id and pair not in seen_edges:
            edges.append({"source_id": source_id, "target_id": target_id, "label": relation})
            seen_edges.add(pair)

    highest_bottom = max((int(card["y"]) + int(card["height"]) for card in cards), default=420)
    return cards, edges, 1500, max(480, highest_bottom + 70)


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

    def render_excalidraw_scene_html(
        self,
        trace_or_dict: Union[EvidenceTrace, Dict[str, Any]],
        locale: str = DEFAULT_LOCALE,
    ) -> str:
        """Render the exported Excalidraw evidence scene as an offline viewer.

        The package provides the scene contract but intentionally carries no
        bundled browser editor. This viewer renders that scene locally with
        the same warm-paper, hand-drawn visual language and retains the scene
        JSON in the page for export/audit. It never contacts a CDN or service.
        """
        norm_loc = normalize_locale(locale)
        caps = self.check_capabilities()
        if not caps.is_available or caps.status == CapabilityStatus.UNAVAILABLE:
            raise RuntimeError("excalidraw_scene_renderer_unavailable")

        view_model = build_evidence_graph_view_model(trace_or_dict, locale=norm_loc)
        if view_model.is_insufficient:
            notice = view_model.notice or t("evidence_graph_insufficient", locale=norm_loc)
            return (
                '<div class="excalidraw-evidence-error">'
                f'{html.escape(notice)}</div>'
            )

        scene = self.export_excalidraw_scene(trace_or_dict, locale=norm_loc)
        cards, edges, scene_width, scene_height = _build_evidence_scene_layout(view_model)
        card_by_id = {str(card["id"]): card for card in cards}
        colors = {
            "question": ("#e7f0ff", "#3b82f6"),
            "answer": ("#fff0e8", "#e8753a"),
            "citation": ("#fff7d8", "#c28a10"),
            "source": ("#f2ebff", "#7c5bb8"),
        }

        edge_svg: List[str] = []
        for edge in edges:
            source = card_by_id[edge["source_id"]]
            target = card_by_id[edge["target_id"]]
            x1 = int(source["x"]) + int(source["width"])
            y1 = int(source["y"]) + int(source["height"]) // 2
            x2 = int(target["x"])
            y2 = int(target["y"]) + int(target["height"]) // 2
            edge_svg.append(
                f'<path class="scene-edge" d="M{x1},{y1} C{x1 + 35},{y1} {x2 - 35},{y2} {x2},{y2}" />'
            )

        card_svg: List[str] = []
        for card in cards:
            fill, stroke = colors.get(str(card["node_type"]), ("#ffffff", "#64748b"))
            x, y = int(card["x"]), int(card["y"])
            card_id = html.escape(str(card["id"]), quote=True)
            title_lines = _scene_text_lines(str(card["title"]), 29, 2)
            summary_lines = _scene_text_lines(str(card["summary"]), 38, 2)
            title_svg = "".join(
                f'<text class="scene-title" x="{x + 14}" y="{y + 44 + line_index * 17}">{html.escape(line)}</text>'
                for line_index, line in enumerate(title_lines)
            )
            summary_y = y + 79
            summary_svg = "".join(
                f'<text class="scene-summary" x="{x + 14}" y="{summary_y + line_index * 14}">{html.escape(line)}</text>'
                for line_index, line in enumerate(summary_lines)
            )
            badge = html.escape(str(card.get("badge") or ""))
            badge_svg = (
                f'<text class="scene-badge" x="{x + 14}" y="{y + 23}">{badge}</text>' if badge else ""
            )
            kind = html.escape(str(card["kind"]))
            card_svg.append(
                f'<g class="scene-node {html.escape(str(card["node_type"]), quote=True)}" tabindex="0" '
                f'role="button" data-node="{card_id}">'
                f'<rect class="scene-shadow" x="{x + 2}" y="{y + 2}" width="{card["width"]}" height="{card["height"]}" rx="10" />'
                f'<rect class="scene-card" x="{x}" y="{y}" width="{card["width"]}" height="{card["height"]}" '
                f'rx="10" fill="{fill}" stroke="{stroke}" />'
                f'<text class="scene-kind" x="{x + 14}" y="{y + 23}">{kind}</text>{badge_svg}{title_svg}{summary_svg}</g>'
            )

        payload = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")
        scene_payload = json.dumps(scene, ensure_ascii=False).replace("</", "<\\/")
        initial_detail_title = t("excalidraw_scene_select_node", locale=norm_loc)
        initial_detail_hint = t("excalidraw_scene_select_node_desc", locale=norm_loc)
        initial_detail_title_js = json.dumps(initial_detail_title, ensure_ascii=False)
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--paper:#fdfbf7;--ink:#23262b;--line:#d7d1c6}}*{{box-sizing:border-box}}html,body{{margin:0;background:var(--paper);color:var(--ink);font-family:{CJK_MULTI_LOCALE_FONT_STACK}}}
.scene-shell{{padding:14px;background:var(--paper)}}.scene-head{{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:0 4px 10px;flex-wrap:wrap}}.scene-head strong{{font-size:16px}}.scene-head span{{font-size:12px;color:#5f6670}}.scene-board{{overflow:auto;border:1px solid var(--line);border-radius:14px;background-image:radial-gradient(#d9d2c7 .8px,transparent .8px);background-size:18px 18px;box-shadow:0 3px 12px rgba(52,45,34,.12)}}svg{{display:block;min-width:1100px;width:100%;height:auto}}.scene-edge{{fill:none;stroke:#697586;stroke-width:2.3;stroke-linecap:round;stroke-dasharray:8 5;marker-end:url(#scene-arrow)}}.scene-node{{cursor:pointer;outline:none}}.scene-shadow{{fill:none;stroke:#9b9488;stroke-width:1;opacity:.45;transform:rotate(.25deg);transform-origin:center}}.scene-card{{stroke-width:2.2;stroke-linejoin:round;stroke-dasharray:1 0.7}}.scene-node:hover .scene-card,.scene-node:focus .scene-card{{stroke-width:4;filter:brightness(.98)}}.scene-kind{{font-size:10px;font-weight:800;letter-spacing:1px;fill:#5d6670}}.scene-title{{font-size:14px;font-weight:700;fill:#22252a}}.scene-summary{{font-size:11px;fill:#4d5560}}.scene-badge{{font-size:10px;font-weight:800;fill:#9c6511}}.scene-detail{{margin:12px 4px 2px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:#fffdfa;white-space:pre-wrap;line-height:1.5;font-size:13px;max-height:170px;overflow:auto}}.scene-detail strong{{display:block;margin-bottom:5px}}.excalidraw-evidence-error{{padding:16px;border:1px solid #c28a10;border-radius:10px;background:#fff7d8;color:#6c4a00}}
</style></head><body><main class="scene-shell" data-excalidraw-elements="{len(scene.get('elements', []))}"><div class="scene-head"><strong>✏️ {html.escape(t('evidence_graph_title', locale=norm_loc))}</strong><span>{html.escape(view_model.stats_label)}</span></div><section class="scene-board"><svg viewBox="0 0 {scene_width} {scene_height}" role="img" aria-label="Evidence graph in Excalidraw style"><defs><marker id="scene-arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L9,4 L0,8" fill="none" stroke="#697586" stroke-width="1.5"/></marker></defs>{''.join(edge_svg)}{''.join(card_svg)}</svg></section><section class="scene-detail" aria-live="polite"><strong id="scene-detail-title">{html.escape(initial_detail_title)}</strong><div id="scene-detail-content">{html.escape(initial_detail_hint)}</div></section></main><script>const EXCALIDRAW_SCENE={scene_payload};const INITIAL_DETAIL_TITLE={initial_detail_title_js};const NODES={payload};const byId=Object.fromEntries(NODES.map(node=>[node.id,node]));function showNode(id){{const node=byId[id];if(!node)return;document.getElementById('scene-detail-title').textContent=node.title;document.getElementById('scene-detail-content').textContent=node.detail||node.summary;document.querySelectorAll('.scene-node').forEach(item=>item.classList.toggle('active',item.dataset.node===id));}}document.querySelectorAll('.scene-node').forEach(item=>{{item.addEventListener('click',()=>showNode(item.dataset.node));item.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault();showNode(item.dataset.node);}}}});}});</script></body></html>"""

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
