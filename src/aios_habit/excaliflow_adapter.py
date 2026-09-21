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
import math
import re
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


def _atlas_label_lines(value: Any) -> List[str]:
    """Fit one Atlas node label inside its card, including CJK filenames."""
    text = " ".join(str(value or "").split()) or "-"
    contains_wide_chars = any(ord(char) >= 0x2E80 for char in text)
    line_limit = 18 if contains_wide_chars else 30
    lines: List[str] = []
    remaining = text
    while remaining and len(lines) < 2:
        if len(remaining) <= line_limit:
            lines.append(remaining)
            remaining = ""
            break
        split_at = remaining.rfind(" ", 0, line_limit + 1)
        if split_at < max(5, line_limit // 2):
            split_at = line_limit
        lines.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        lines[-1] = f"{lines[-1][:max(1, line_limit - 3)].rstrip()}..."
    return lines or ["-"]


def _atlas_relation_label(relation: Any) -> str:
    labels = {
        "supports": "dẫn chứng cho",
        "supported by": "dẫn chứng cho",
        "cites": "trích từ",
        "extracted_from": "trích từ",
        "derived_from": "suy ra từ",
        "mentions": "liên quan tới",
        "contains": "chứa đoạn",
    }
    raw = str(relation or "liên kết").strip().lower().replace("-", " ").replace("_", " ")
    return labels.get(raw, raw)


def _atlas_positions(graph: Dict[str, Any]) -> Dict[str, tuple[int, int]]:
    """Mirror the upstream Atlas grid so edge labels stay aligned with cards."""
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for node in graph.get("nodes", []):
        groups[str(node.get("type", ""))].append(node)
    positions: Dict[str, tuple[int, int]] = {}
    y = 75
    for node_type in ("answer", "claim", "entity", "code", "chunk", "document", "case"):
        items = groups[node_type]
        if not items:
            continue
        columns = min(3, len(items))
        for index, node in enumerate(items):
            positions[str(node["id"])] = (70 + (index % columns) * 335, y + (index // columns) * 140)
        y += ((len(items) + columns - 1) // columns) * 140 + 55
    return positions


def _polish_evidence_atlas_html(
    atlas_html: str,
    graph: Dict[str, Any],
    locale: str = DEFAULT_LOCALE,
) -> str:
    """Repair interaction, Dark Mode aesthetics, and readability shortcomings in upstream Atlas HTML.

    Flowsint 2.0 upgrades:
    1. Cubic Bezier curves (<path d="M... C...">) replacing straight rigid lines.
    2. Floating Canvas Toolbar (Zoom In/Out, Fit-to-View, Fullscreen) on canvas.
    3. Smooth Pan & Zoom canvas navigation engine.
    4. Collapsible Smart Inspector with graphical Confidence Gauge and Inbound/Outbound links.
    5. Real-time Search Box with node filtering and auto-dimming.
    """
    norm_loc = normalize_locale(locale)

    def replace_label(match: re.Match[str]) -> str:
        x, y = match.group("x"), match.group("y")
        raw_label = match.group("label")
        clean_label = re.sub(r"<[^>]+>", "", raw_label)
        unescaped_text = html.unescape(clean_label).strip()
        lines = _atlas_label_lines(unescaped_text)
        tspans = "".join(
            f'<tspan x="{x}" dy="{0 if index == 0 else 17}">{html.escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        return f'{match.group("open")}{tspans}</text>'

    atlas_html = re.sub(
        r'(?P<open><text class="node-label" x="(?P<x>[^"]+)" y="(?P<y>[^"]+)">)(?P<label>[\s\S]*?)</text>',
        replace_label,
        atlas_html,
    )

    # Convert straight <line class="edge..."> to smooth Cubic Bezier <path d="M... C...">
    def _line_to_bezier_path(match: re.Match[str]) -> str:
        attrs = match.group(1)
        x1_m = re.search(r'x1="([^"]+)"', attrs)
        y1_m = re.search(r'y1="([^"]+)"', attrs)
        x2_m = re.search(r'x2="([^"]+)"', attrs)
        y2_m = re.search(r'y2="([^"]+)"', attrs)
        if not (x1_m and y1_m and x2_m and y2_m):
            return match.group(0)
        x1, y1 = float(x1_m.group(1)), float(y1_m.group(1))
        x2, y2 = float(x2_m.group(1)), float(y2_m.group(1))
        dy = y2 - y1
        dx = x2 - x1
        if abs(dy) >= 10:
            cx1, cy1 = x1, y1 + dy * 0.45
            cx2, cy2 = x2, y2 - dy * 0.45
        else:
            cx1, cy1 = x1 + dx * 0.45, y1 - 25
            cx2, cy2 = x2 - dx * 0.45, y2 - 25
        clean_attrs = re.sub(r'\b(x1|y1|x2|y2)="[^"]*"\s*', '', attrs).strip()
        d = f"M {x1:.1f},{y1:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {x2:.1f},{y2:.1f}"
        return f'<path marker-end="url(#atlas-arrow)" fill="none" d="{d}" {clean_attrs} />'

    atlas_html = re.sub(r'<line\s+([^>]*\bclass="[^"]*edge[^"]*"[^>]*?)\s*/>', _line_to_bezier_path, atlas_html)

    # Neon marker for edge arrowheads
    atlas_html = re.sub(
        r'(<svg\b[^>]*>)',
        r'\1<defs><marker id="atlas-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="none" stroke="#38bdf8" stroke-width="1.3"/></marker></defs>',
        atlas_html,
        count=1,
    )
    positions = _atlas_positions(graph)

    # Calculate vertical bounds for each tier (e.g. answer, chunk, document)
    tier_ranges: Dict[str, List[int]] = {}
    for n in graph.get("nodes", []):
        nid = str(n.get("id", ""))
        ntype = str(n.get("type", ""))
        p = positions.get(nid)
        if p:
            y1, y2 = p[1], p[1] + 84
            if ntype not in tier_ranges:
                tier_ranges[ntype] = [y1, y2]
            else:
                tier_ranges[ntype][0] = min(tier_ranges[ntype][0], y1)
                tier_ranges[ntype][1] = max(tier_ranges[ntype][1], y2)

    # Bounding boxes of all nodes with 16px safety margin (cards must never be overlapped)
    node_boxes = [
        (p[0] - 16, p[1] - 16, p[0] + 260 + 16, p[1] + 84 + 16)
        for p in positions.values()
    ]

    edge_labels = []
    placed_label_coords: List[tuple[int, int]] = []

    # Safe whitespace channels between tiers where zero cards exist
    band_y1 = None
    if "answer" in tier_ranges and "chunk" in tier_ranges:
        band_y1 = (tier_ranges["answer"][1] + tier_ranges["chunk"][0]) // 2

    band_y2 = None
    if "chunk" in tier_ranges and "document" in tier_ranges:
        band_y2 = (tier_ranges["chunk"][1] + tier_ranges["document"][0]) // 2

    for edge in graph.get("edges", []):
        start = positions.get(str(edge.get("from")))
        end = positions.get(str(edge.get("to")))
        if not start or not end:
            continue
        label = html.escape(_atlas_relation_label(edge.get("relation")))
        p_start = (start[0] + 130, start[1] + 42)
        p_end = (end[0] + 130, end[1] + 42)

        cand_y = None
        if start[1] < end[1]:
            if band_y1 is not None and p_start[1] < band_y1 < p_end[1]:
                cand_y = band_y1
            elif band_y2 is not None and p_start[1] < band_y2 < p_end[1]:
                cand_y = band_y2
        else:
            if band_y2 is not None and p_end[1] < band_y2 < p_start[1]:
                cand_y = band_y2
            elif band_y1 is not None and p_end[1] < band_y1 < p_start[1]:
                cand_y = band_y1

        x1_pt, y1_pt = float(p_start[0]), float(p_start[1])
        x2_pt, y2_pt = float(p_end[0]), float(p_end[1])
        dy = y2_pt - y1_pt
        dx = x2_pt - x1_pt
        if abs(dy) >= 10:
            cx1, cy1 = x1_pt, y1_pt + dy * 0.45
            cx2, cy2 = x2_pt, y2_pt - dy * 0.45
        else:
            cx1, cy1 = x1_pt + dx * 0.45, y1_pt - 25
            cx2, cy2 = x2_pt - dx * 0.45, y2_pt - 25

        if cand_y is not None and p_end[1] != p_start[1]:
            t_param = (cand_y - p_start[1]) / (p_end[1] - p_start[1])
            t_param = max(0.0, min(1.0, t_param))
            cand_x = int(
                (1 - t_param)**3 * x1_pt
                + 3 * (1 - t_param)**2 * t_param * cx1
                + 3 * (1 - t_param) * t_param**2 * cx2
                + t_param**3 * x2_pt
            )
            cand_y = int(
                (1 - t_param)**3 * y1_pt
                + 3 * (1 - t_param)**2 * t_param * cy1
                + 3 * (1 - t_param) * t_param**2 * cy2
                + t_param**3 * y2_pt
            )
        else:
            cand_x = int(0.125 * x1_pt + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2_pt)
            cand_y = int(0.125 * y1_pt + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2_pt)

        width = min(140, max(76, 16 + len(label) * 6))
        height = 20
        bx1 = cand_x - width // 2
        bx2 = cand_x + width // 2
        by1 = cand_y - height // 2
        by2 = cand_y + height // 2

        # Strict collision check: NEVER overlap any node card
        collides_node = any(
            not (bx2 < nx1 or bx1 > nx2 or by2 < ny1 or by1 > ny2)
            for nx1, ny1, nx2, ny2 in node_boxes
        )
        # Avoid clutter: Ensure labels in the same tier maintain at least 70px spacing
        collides_label = any(
            math.hypot(cand_x - px, cand_y - py) < 70
            for px, py in placed_label_coords
        )

        if not collides_node and not collides_label:
            placed_label_coords.append((cand_x, cand_y))
            edge_labels.append(
                f'<g class="edge-label"><rect x="{bx1}" y="{by1}" width="{width}" height="{height}" rx="9999"/>'
                f'<text x="{cand_x}" y="{cand_y + 3}" text-anchor="middle">{label}</text></g>'
            )
    atlas_html = atlas_html.replace("</svg>", "".join(edge_labels) + "</svg>", 1)

    # Localize raw English relations remaining in SVG text
    atlas_html = atlas_html.replace(">supported by<", ">dẫn chứng cho<")
    atlas_html = atlas_html.replace(">contains<", ">chứa đoạn<")
    atlas_html = atlas_html.replace(">extracted from<", ">trích từ<")
    atlas_html = atlas_html.replace(">derived from<", ">suy ra từ<")
    atlas_html = atlas_html.replace("Loại: document", "Loại: Tài liệu nguồn")
    atlas_html = atlas_html.replace("Loại: chunk", "Loại: Đoạn trích bằng chứng")
    atlas_html = atlas_html.replace("Loại: answer", "Loại: Câu trả lời")

    # Inject Floating Canvas Toolbar into .canvas section
    floating_toolbar_html = (
        '<div class="atlas-floating-toolbar" role="toolbar" aria-label="Canvas controls">'
        f'<button type="button" id="atlas-btn-toggle-layout" class="atlas-tool-btn active-mode" title="{html.escape(t("layout_mode_switch", locale=norm_loc))}">🌌</button>'
        f'<button type="button" id="atlas-btn-zoom-in" class="atlas-tool-btn" title="{html.escape(t("zoom_in", locale=norm_loc))}">➕</button>'
        f'<button type="button" id="atlas-btn-zoom-out" class="atlas-tool-btn" title="{html.escape(t("zoom_out", locale=norm_loc))}">➖</button>'
        f'<button type="button" id="atlas-btn-fit" class="atlas-tool-btn" title="{html.escape(t("fit_view", locale=norm_loc))}">⊡</button>'
        f'<button type="button" id="atlas-btn-fullscreen" class="atlas-tool-btn" title="{html.escape(t("fullscreen_view", locale=norm_loc))}">⛶</button>'
        '</div>'
    )
    atlas_html = re.sub(
        r'(<section class="canvas"[^>]*>)',
        r'\1' + floating_toolbar_html,
        atlas_html,
        count=1,
    )

    # Inject Search Box into header toolbar
    search_box_html = (
        '<div class="atlas-search-box">'
        '<span class="atlas-search-icon">🔍</span>'
        f'<input type="text" id="atlas-search-input" placeholder="{html.escape(t("search_entities_placeholder", locale=norm_loc))}" class="atlas-search-input" />'
        '</div>'
    )
    atlas_html = re.sub(
        r'(<div class="toolbar"[^>]*>)',
        r'\1' + search_box_html,
        atlas_html,
        count=1,
    )

    # Inject Collapsible Inspector controls, Mini Radar, Confidence Gauge, and In/Out links into <aside>
    radar_title = t("radar_title", locale=norm_loc)
    aside_addons_html = (
        f'<button type="button" id="atlas-toggle-inspector" class="atlas-collapse-btn" title="{html.escape(t("collapse_panel", locale=norm_loc))}">›</button>'
        '<div id="atlas-mini-radar-container" class="mini-radar-card" style="display:none;">'
        '<div class="mini-radar-header">'
        f'<span>🛰️ {html.escape(radar_title)}</span>'
        '<span id="atlas-mini-radar-count" class="mini-radar-count">0</span>'
        '</div>'
        '<div class="mini-radar-canvas-wrap">'
        '<svg id="atlas-mini-radar-svg" viewBox="-80 -80 160 160" width="100%" height="150">'
        '<circle cx="0" cy="0" r="58" class="radar-orbit" />'
        '<circle cx="0" cy="0" r="32" class="radar-orbit inner" />'
        '<g id="atlas-radar-rays"></g>'
        '<g id="atlas-radar-neighbors"></g>'
        '<circle id="atlas-radar-center-node" cx="0" cy="0" r="9" class="radar-center" />'
        '</svg>'
        '</div>'
        '</div>'
        '<div id="atlas-confidence-box" class="confidence-gauge-card" style="display:none;">'
        '<div class="gauge-header">'
        f'<span class="gauge-title">{html.escape(t("confidence_score", locale=norm_loc))}</span>'
        '<span id="atlas-conf-pct" class="gauge-pct">--%</span>'
        '</div>'
        '<div class="gauge-track"><div id="atlas-conf-fill" class="gauge-fill" style="width:0%;"></div></div>'
        '</div>'
        '<div id="atlas-links-box" class="atlas-links-card" style="display:none;">'
        '<div id="atlas-inbound-section" style="margin-bottom:10px;">'
        f'<div class="links-title">📥 {html.escape(t("inbound_links", locale=norm_loc))} (<span id="atlas-in-count">0</span>)</div>'
        '<div id="atlas-in-chips" class="links-chips-wrap"></div>'
        '</div>'
        '<div id="atlas-outbound-section">'
        f'<div class="links-title">📤 {html.escape(t("outbound_links", locale=norm_loc))} (<span id="atlas-out-count">0</span>)</div>'
        '<div id="atlas-out-chips" class="links-chips-wrap"></div>'
        '</div>'
        '</div>'
    )
    atlas_html = re.sub(
        r'(<aside\b[^>]*>)',
        r'\1' + aside_addons_html,
        atlas_html,
        count=1,
    )

    # Dark Mode CSS Override matching Flowsint 2.0 & AIOS WorkLens
    dark_atlas_css = f"""<style>
:root {{
  --ink: #f8fafc;
  --muted: #94a3b8;
  --paper: #070b14;
  --panel: #0f172a;
  --line: #1e293b;
  --accent: #38bdf8;
  --accent-glow: rgba(56, 189, 248, 0.4);
  --orange: #f97316;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: {CJK_MULTI_LOCALE_FONT_STACK};
  overflow-x: hidden;
}}
header {{
  padding: 12px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}}
.eyebrow {{
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 11px;
  font-weight: 700;
}}
h1 {{
  margin: 4px 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: #f8fafc;
}}
.lede {{
  margin: 0;
  color: var(--muted);
  max-width: 850px;
  font-size: 12px;
  line-height: 1.5;
}}
main {{
  max-width: 1400px;
  margin: auto;
  padding: 16px;
}}
.toolbar {{
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 14px;
}}
button {{
  font: inherit;
  border: 1px solid #334155;
  background: #1e293b;
  border-radius: 9999px;
  padding: 6px 14px;
  cursor: pointer;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.15s ease;
}}
button:hover {{
  background: #334155;
  color: #fff;
  border-color: #475569;
}}
button.active {{
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
  font-weight: 700;
}}
.legend {{
  color: #64748b;
  font-size: 12px;
  margin-left: 6px;
}}
.atlas-search-box {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 9999px;
  padding: 4px 12px;
  margin-left: auto;
}}
.atlas-search-icon {{
  font-size: 12px;
}}
.atlas-search-input {{
  background: transparent;
  border: none;
  color: #f8fafc;
  font-size: 12px;
  outline: none;
  width: 160px;
  transition: width 0.2s ease;
}}
.atlas-search-input:focus {{
  width: 230px;
}}
.layout {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  transition: grid-template-columns 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}}
.layout.inspector-collapsed {{
  grid-template-columns: minmax(0, 1fr) 42px;
}}
.layout.inspector-collapsed aside > *:not(.atlas-collapse-btn) {{
  display: none !important;
}}
.canvas {{
  overflow: hidden;
  position: relative;
  border: 1px solid var(--line);
  border-radius: 12px;
  background-color: var(--paper);
  background-image: radial-gradient(#1e293b 1px, transparent 1px);
  background-size: 20px 20px;
  min-height: 580px;
  box-shadow: inset 0 2px 12px rgba(0, 0, 0, 0.5);
  cursor: grab;
  user-select: none;
}}
.canvas:active {{
  cursor: grabbing;
}}
.atlas-floating-toolbar {{
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 40;
  display: flex;
  gap: 6px;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(8px);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}}
.atlas-tool-btn {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #cbd5e1;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}}
.atlas-tool-btn:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
}}
.atlas-viewport svg {{
  display: block;
  min-width: 1080px;
  transform-origin: 0 0;
  transition: transform 0.05s ease-out;
}}
#atlas-mini-radar-svg {{
  min-width: 0 !important;
  width: 160px !important;
  max-width: 160px !important;
  height: 140px !important;
  display: block;
  margin: 0 auto;
  transform: none !important;
}}
@keyframes flowDash {{
  from {{ stroke-dashoffset: 24; }}
  to {{ stroke-dashoffset: 0; }}
}}
.edge {{
  stroke: #475569;
  stroke-width: 1.8;
  opacity: 0.7;
  transition: stroke 0.2s, stroke-width 0.2s, opacity 0.2s;
  fill: none;
}}
.edge:hover, .edge.active, .edge.focus {{
  stroke: var(--accent) !important;
  stroke-width: 2.8 !important;
  opacity: 1 !important;
  stroke-dasharray: 6 3 !important;
  animation: flowDash 0.8s linear infinite !important;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.7));
}}
.edge.dimmed, .node.dimmed {{
  opacity: 0.15 !important;
}}
.node.search-matched rect {{
  stroke: var(--success) !important;
  stroke-width: 3px !important;
  filter: drop-shadow(0 0 10px rgba(16, 185, 129, 0.6)) !important;
}}
.edge-label {{
  pointer-events: none;
}}
.edge-label rect {{
  fill: #0f172a;
  stroke: #334155;
  stroke-width: 1;
}}
.edge-label text {{
  font-size: 10px;
  font-weight: 600;
  fill: #94a3b8;
}}
.node {{
  cursor: pointer;
  outline: none;
}}
.node rect {{
  fill: var(--panel);
  stroke: var(--node-color);
  stroke-width: 1.8;
  rx: 12px;
  transition: all 0.15s ease;
}}
.node.needs-review rect {{
  stroke-dasharray: 6 3;
}}
.node:hover rect, .node.active rect {{
  fill: #1e293b;
  stroke-width: 3.2;
  filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.5));
}}
.node-type {{
  font-size: 11px;
  font-weight: 800;
  fill: #94a3b8;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}}
.node-label {{
  font-size: 13px;
  font-weight: 600;
  fill: #f8fafc;
  line-height: 1.4;
}}
.review-label {{
  font-size: 11px;
  font-weight: 800;
  fill: #f59e0b;
}}
body[data-view="answer"] .node:not(.focus), body[data-view="answer"] .edge:not(.focus) {{
  display: none;
}}
aside {{
  position: sticky;
  top: 70px;
  align-self: start;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  padding: 16px;
  max-height: calc(100vh - 90px);
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}}
aside h2 {{
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  margin: 4px 0 10px;
  word-break: break-word;
}}
.atlas-collapse-btn {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
  transition: all 0.15s ease;
}}
.atlas-collapse-btn:hover {{
  background: #334155;
  color: #38bdf8;
}}
.confidence-gauge-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}}
.gauge-header {{
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.gauge-pct {{
  color: #38bdf8;
  font-weight: 800;
}}
.gauge-track {{
  height: 6px;
  background: #0f172a;
  border-radius: 9999px;
  overflow: hidden;
}}
.gauge-fill {{
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background 0.3s ease;
}}
.atlas-links-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}}
.links-title {{
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.links-chips-wrap {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}
.atlas-link-chip {{
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.atlas-link-chip:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
}}
.mini-radar-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 10px 12px;
  margin: 10px 0;
  overflow: hidden;
  box-sizing: border-box;
}}
.mini-radar-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.mini-radar-count {{
  color: var(--accent);
  font-weight: 800;
}}
.mini-radar-canvas-wrap {{
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0f172a;
  border-radius: 6px;
  padding: 4px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
  max-width: 100%;
  box-sizing: border-box;
}}
.radar-orbit {{
  fill: none;
  stroke: #334155;
  stroke-width: 1;
  stroke-dasharray: 2 3;
}}
.radar-orbit.inner {{
  stroke: #1e293b;
}}
.radar-ray {{
  stroke: rgba(56, 189, 248, 0.35);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}}
.radar-dot {{
  stroke: #0f172a;
  stroke-width: 1.5;
  transition: all 0.2s ease;
  cursor: pointer;
}}
.radar-dot-group:hover .radar-dot {{
  r: 8;
  filter: drop-shadow(0 0 6px var(--accent));
}}
.radar-center {{
  fill: var(--accent);
  stroke: #0f172a;
  stroke-width: 2;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.8));
}}
.atlas-tool-btn.active-mode {{
  background: rgba(56, 189, 248, 0.2);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}}
.receipt {{
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 12.5px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  padding: 12px;
  word-break: break-word;
}}
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 9999px;
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  border: 1px solid rgba(56, 189, 248, 0.3);
  font-size: 11px;
  font-weight: 700;
  margin: 2px 4px 4px 0;
}}
.notice {{
  border-left: 3px solid #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  padding: 8px 12px;
  color: #fde68a;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 10px;
}}
.atlas-copy-btn {{
  background: #334155;
  color: #f8fafc;
  border: 1px solid #475569;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}}
.atlas-copy-btn:hover {{
  background: #475569;
}}
@media (max-width: 850px) {{
  .layout {{ display: block; }}
  aside {{ position: static; max-height: none; margin-top: 16px; }}
  h1 {{ font-size: 18px; }}
}}
</style>"""

    # Inject Dark Mode CSS replacing original upstream CSS block
    atlas_html = re.sub(r"<style>[\s\S]*?</style>", dark_atlas_css, atlas_html, count=1)

    atlas_html = atlas_html.replace("document.querySelectorAll('[data-view]')", "document.querySelectorAll('button[data-view]')")
    atlas_html = atlas_html.replace(
        "<span class=\"legend\">Bấm một khối hoặc đường nối để xem biên lai bằng chứng.</span>",
        '<span id="atlas-view-status" class="legend" aria-live="polite">Đang xem: Câu trả lời &amp; nguồn</span>',
    )
    atlas_html = atlas_html.replace(
        "document.body.dataset.view=button.dataset.view;document.querySelectorAll('button[data-view]').forEach(item=>item.classList.toggle('active',item===button));",
        "document.body.dataset.view=button.dataset.view;document.querySelectorAll('button[data-view]').forEach(item=>item.classList.toggle('active',item===button));document.getElementById('atlas-view-status').textContent=button.dataset.view==='full'?'Đang xem: Toàn bộ knowledge graph':'Đang xem: Câu trả lời & nguồn';",
    )

    # Controller with localized descriptions, pan/zoom, search filter, and interactive inspector
    payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    copy_label = t("copy_snippet", locale=norm_loc)
    copied_label = t("copied_snippet", locale=norm_loc)
    collapse_label = t("collapse_panel", locale=norm_loc)
    expand_label = t("expand_panel", locale=norm_loc)

    controller = f"""
<script>
(() => {{
  const DATA = {payload};
  const nodeById = Object.fromEntries(DATA.nodes.map(node => [node.id, node]));
  const edgeById = Object.fromEntries(DATA.edges.map(edge => [edge.id, edge]));
  const status = document.getElementById('atlas-view-status');
  const detailTitle = document.getElementById('detail-title');
  const detail = document.getElementById('detail');

  const confBox = document.getElementById('atlas-confidence-box');
  const confPct = document.getElementById('atlas-conf-pct');
  const confFill = document.getElementById('atlas-conf-fill');

  const linksBox = document.getElementById('atlas-links-box');
  const inChips = document.getElementById('atlas-in-chips');
  const inCount = document.getElementById('atlas-in-count');
  const outChips = document.getElementById('atlas-out-chips');
  const outCount = document.getElementById('atlas-out-count');

  const canvasSec = document.querySelector('.canvas');
  const svgElem = canvasSec ? canvasSec.querySelector('svg') : null;
  const layout = document.querySelector('.layout');
  const toggleInspectorBtn = document.getElementById('atlas-toggle-inspector');
  const searchInput = document.getElementById('atlas-search-input');

  const TYPE_NAMES = {{
    'document': '📁 Tệp tài liệu nguồn',
    'chunk': '🏷️ Đoạn trích bằng chứng',
    'answer': '💡 Câu trả lời tổng hợp',
    'question': '❓ Câu hỏi truy vấn',
    'claim': '📌 Nhận định trích xuất'
  }};

  const TYPE_COLORS = {{
    'question': '#0284c7',
    'answer': '#059669',
    'citation': '#d97706',
    'source': '#7c3aed',
    'chunk': '#38bdf8',
    'document': '#a855f7'
  }};

  const NEIGHBORS_PATTERN = {json.dumps(t("neighbors_count", locale=norm_loc), ensure_ascii=False)};

  function updateAtlasMiniRadar(nodeId) {{
    const radarContainer = document.getElementById('atlas-mini-radar-container');
    if (!radarContainer) return;

    const inEdges = DATA.edges.filter(e => e.to === nodeId);
    const outEdges = DATA.edges.filter(e => e.from === nodeId);
    const neighborIds = [...new Set([...inEdges.map(e => e.from), ...outEdges.map(e => e.to)])].filter(id => id !== nodeId);

    const countSpan = document.getElementById('atlas-mini-radar-count');
    if (countSpan) {{
      countSpan.textContent = NEIGHBORS_PATTERN.replace('{{count}}', neighborIds.length);
    }}

    if (neighborIds.length === 0) {{
      radarContainer.style.display = 'none';
      return;
    }}
    radarContainer.style.display = 'block';

    const raysGroup = document.getElementById('atlas-radar-rays');
    const neighborsGroup = document.getElementById('atlas-radar-neighbors');
    const centerNode = document.getElementById('atlas-radar-center-node');
    if (!raysGroup || !neighborsGroup) return;

    const currNode = nodeById[nodeId];
    if (centerNode && currNode) {{
      centerNode.setAttribute('fill', TYPE_COLORS[currNode.type] || '#38bdf8');
    }}

    raysGroup.innerHTML = '';
    neighborsGroup.innerHTML = '';

    const R = 58;
    const n = neighborIds.length;
    let raysHtml = '';
    let dotsHtml = '';
    neighborIds.forEach((nbId, idx) => {{
      const angle = (2 * Math.PI * idx / n) - Math.PI / 2;
      const nx = Math.cos(angle) * R;
      const ny = Math.sin(angle) * R;
      const nbObj = nodeById[nbId] || {{}};
      const ntype = nbObj.type || 'chunk';
      const nbLabel = (nbObj.label || nbId).replace(/"/g, '&quot;');
      const color = TYPE_COLORS[ntype] || '#38bdf8';

      raysHtml += `<line x1="0" y1="0" x2="${{nx.toFixed(1)}}" y2="${{ny.toFixed(1)}}" class="radar-ray" />`;
      dotsHtml += `<g class="radar-dot-group" cursor="pointer" onclick="selectAtlasNode('${{nbId}}')">` +
                  `<circle cx="${{nx.toFixed(1)}}" cy="${{ny.toFixed(1)}}" r="5.5" fill="${{color}}" class="radar-dot"><title>${{nbLabel}}</title></circle></g>`;
    }});
    raysGroup.innerHTML = raysHtml;
    neighborsGroup.innerHTML = dotsHtml;
  }}

  // --- Pan & Zoom Engine ---
  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  const updateTransform = () => {{
    if (!svgElem) return;
    svgElem.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
  }};

  if (canvasSec && svgElem) {{
    canvasSec.addEventListener('mousedown', (e) => {{
      if (e.target.closest('.node') || e.target.closest('button') || e.target.closest('input')) return;
      isPanning = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
      canvasSec.style.cursor = 'grabbing';
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!isPanning) return;
      panX = e.clientX - startX;
      panY = e.clientY - startY;
      updateTransform();
    }});

    window.addEventListener('mouseup', () => {{
      isPanning = false;
      if (canvasSec) canvasSec.style.cursor = 'grab';
    }});

    canvasSec.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
      scale = Math.min(Math.max(0.3, scale * zoomFactor), 3.0);
      updateTransform();
    }}, {{ passive: false }});
  }}

  // Toolbar button handlers
  const btnZoomIn = document.getElementById('atlas-btn-zoom-in');
  if (btnZoomIn) {{
    btnZoomIn.addEventListener('click', () => {{
      scale = Math.min(3.0, scale * 1.2);
      updateTransform();
    }});
  }}

  const btnZoomOut = document.getElementById('atlas-btn-zoom-out');
  if (btnZoomOut) {{
    btnZoomOut.addEventListener('click', () => {{
      scale = Math.max(0.3, scale / 1.2);
      updateTransform();
    }});
  }}

  const btnFit = document.getElementById('atlas-btn-fit');
  if (btnFit) {{
    btnFit.addEventListener('click', () => {{
      scale = 1.0;
      panX = 0;
      panY = 0;
      updateTransform();
    }});
  }}

  const btnFullscreen = document.getElementById('atlas-btn-fullscreen');
  if (btnFullscreen) {{
    btnFullscreen.addEventListener('click', () => {{
      const target = canvasSec || document.documentElement;
      if (!document.fullscreenElement) {{
        target.requestFullscreen().catch(() => {{}});
      }} else {{
        document.exitFullscreen().catch(() => {{}});
      }}
    }});
  }}

  // --- Collapsible Inspector ---
  if (toggleInspectorBtn && layout) {{
    toggleInspectorBtn.addEventListener('click', () => {{
      const isCollapsed = layout.classList.toggle('inspector-collapsed');
      toggleInspectorBtn.textContent = isCollapsed ? '‹' : '›';
      toggleInspectorBtn.title = isCollapsed ? {json.dumps(expand_label, ensure_ascii=False)} : {json.dumps(collapse_label, ensure_ascii=False)};
    }});
  }}

  // --- Real-time Search ---
  if (searchInput) {{
    searchInput.addEventListener('input', () => {{
      const q = searchInput.value.toLowerCase().trim();
      document.querySelectorAll('.node').forEach(nodeEl => {{
        const nid = nodeEl.dataset.node;
        const nObj = nodeById[nid];
        if (!q) {{
          nodeEl.classList.remove('search-matched', 'dimmed');
          return;
        }}
        const haystack = ((nObj?.label || '') + ' ' + (nObj?.properties?.text || '') + ' ' + (nObj?.properties?.location || '')).toLowerCase();
        const matched = haystack.includes(q);
        nodeEl.classList.toggle('search-matched', matched);
        nodeEl.classList.toggle('dimmed', !matched);
      }});

      document.querySelectorAll('.edge').forEach(edgeEl => {{
        if (!q) {{
          edgeEl.classList.remove('dimmed');
          return;
        }}
        const eObj = edgeById[edgeEl.dataset.edge];
        if (!eObj) return;
        const sMatch = document.querySelector(`.node[data-node="${{eObj.from}}"]`)?.classList.contains('search-matched');
        const tMatch = document.querySelector(`.node[data-node="${{eObj.to}}"]`)?.classList.contains('search-matched');
        edgeEl.classList.toggle('dimmed', !(sMatch && tMatch));
      }});
    }});
  }}

  // --- Node Selection & Focus ---
  window.selectAtlasNode = (nodeId) => {{
    const node = nodeById[nodeId];
    if (!node || !detailTitle || !detail) return;

    detailTitle.textContent = node.label;
    const typeLabel = TYPE_NAMES[node.type] || node.type;
    const loc = node.properties?.location || node.properties?.source_id || '';
    const text = node.properties?.text || node.label || '';

    detail.innerHTML = `
      <div style="font-size:11px; font-weight:700; color:#38bdf8; margin-bottom:6px;">${{typeLabel}}</div>
      ${{loc ? `<div style="font-size:11px; color:#a78bfa; margin-bottom:8px; word-break:break-all;">📁 ${{loc}}</div>` : ''}}
      <div style="font-size:12px; line-height:1.6; color:#e2e8f0; white-space:pre-wrap; word-break:break-word;">${{text}}</div>
      <button type="button" class="atlas-copy-btn" onclick="navigator.clipboard.writeText(this.dataset.snippet); this.textContent=${{JSON.stringify({json.dumps(copied_label, ensure_ascii=False)})}}; setTimeout(() => this.textContent=${{JSON.stringify({json.dumps(copy_label, ensure_ascii=False)})}}, 2000);" data-snippet="${{encodeURIComponent(text)}}">
        📋 {html.escape(copy_label)}
      </button>
    `;
    const btn = detail.querySelector('.atlas-copy-btn');
    if (btn) btn.dataset.snippet = text;

    // Update Mini Radar
    updateAtlasMiniRadar(nodeId);

    // Update Confidence Gauge
    if (confBox && confPct && confFill) {{
      const rawScore = node.properties?.score || node.properties?.confidence;
      if (rawScore !== undefined && rawScore !== null) {{
        const pct = Math.round(Number(rawScore) * 100);
        confPct.textContent = pct + '%';
        confFill.style.width = pct + '%';
        confFill.style.backgroundColor = pct >= 80 ? 'var(--success)' : (pct >= 50 ? 'var(--warning)' : 'var(--danger)');
        confBox.style.display = 'block';
      }} else {{
        confBox.style.display = 'none';
      }}
    }}

    // Update Inbound & Outbound Connections
    if (linksBox && inChips && outChips && inCount && outCount) {{
      const inboundEdges = DATA.edges.filter(e => e.to === nodeId);
      const outboundEdges = DATA.edges.filter(e => e.from === nodeId);

      inCount.textContent = inboundEdges.length;
      inChips.innerHTML = inboundEdges.map(e => {{
        const src = nodeById[e.from];
        const srcLabel = src?.label || e.from;
        return `<div class="atlas-link-chip" onclick="selectAtlasNode('${{e.from}}')">${{srcLabel}}</div>`;
      }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

      outCount.textContent = outboundEdges.length;
      outChips.innerHTML = outboundEdges.map(e => {{
        const tgt = nodeById[e.to];
        const tgtLabel = tgt?.label || e.to;
        return `<div class="atlas-link-chip" onclick="selectAtlasNode('${{e.to}}')">${{tgtLabel}}</div>`;
      }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

      linksBox.style.display = (inboundEdges.length > 0 || outboundEdges.length > 0) ? 'block' : 'none';
    }}

    // Visual active & highlight states
    const connectedEdges = new Set();
    const connectedNodeIds = new Set([nodeId]);

    DATA.edges.forEach(edge => {{
      if (edge.from === nodeId || edge.to === nodeId) {{
        connectedEdges.add(edge.id);
        connectedNodeIds.add(edge.from);
        connectedNodeIds.add(edge.to);
      }}
    }});

    document.querySelectorAll('.node').forEach(el => {{
      const isSelf = el.dataset.node === nodeId;
      el.classList.toggle('active', isSelf);
      el.classList.toggle('dimmed', !connectedNodeIds.has(el.dataset.node));
    }});

    document.querySelectorAll('.edge').forEach(el => {{
      const isConnected = connectedEdges.has(el.dataset.edge);
      el.classList.toggle('active', isConnected);
      el.classList.toggle('dimmed', !isConnected);
    }});
  }};

  const setView = (view) => {{
    document.body.dataset.view = view;
    document.querySelectorAll('button[data-view]').forEach(button => {{
      button.classList.toggle('active', button.dataset.view === view);
    }});
    if (status) status.textContent = view === 'full'
      ? 'Đang xem: Toàn bộ knowledge graph'
      : 'Đang xem: Câu trả lời & nguồn';
  }};

  document.querySelectorAll('button[data-view]').forEach(button => {{
    button.addEventListener('click', () => setView(button.dataset.view));
  }});

  document.querySelectorAll('[data-node]').forEach(element => {{
    element.addEventListener('click', () => window.selectAtlasNode(element.dataset.node));
  }});

  document.querySelectorAll('[data-edge]').forEach(element => {{
    element.addEventListener('click', () => {{
      const edge = edgeById[element.dataset.edge];
      if (!edge || !detailTitle || !detail) return;
      const relName = edge.relation.replaceAll('_', ' ');
      detailTitle.textContent = relName;
      const source = nodeById[edge.from]?.label || edge.from;
      const target = nodeById[edge.to]?.label || edge.to;
      const locations = (edge.receipts || []).map(item => item.location).filter(Boolean).join(', ');
      detail.innerHTML = `
        <div style="font-size:12px; color:#38bdf8; font-weight:700; margin-bottom:6px;">Quan hệ liên kết</div>
        <div style="font-size:12.5px; color:#f8fafc; line-height:1.5;"><strong>${{source}}</strong><br>───▶ <strong>${{target}}</strong></div>
        ${{locations ? `<div style="font-size:11px; color:#a78bfa; margin-top:8px;">Vị trí: ${{locations}}</div>` : ''}}
      `;
      if (confBox) confBox.style.display = 'none';
      if (linksBox) linksBox.style.display = 'none';
    }});
  }});
}})();
</script>"""
    atlas_html = atlas_html.replace("</body>", controller + "</body>", 1)
    return atlas_html


def _build_evidence_scene_layout(view_model: EvidenceGraphViewModel) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """Create a compact, Flowsint-inspired evidence layout with pill nodes."""
    cards: List[Dict[str, Any]] = []
    source_card_by_node_id: Dict[str, str] = {}
    source_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for node in view_model.nodes:
        if node["node_type"] == "source":
            source_groups[str(node.get("source_id") or node["title"])].append(node)

    def append_card(
        node: Dict[str, Any],
        *,
        x: int,
        y: int,
        width: int = 220,
        height: int = 44,
        card_id: Optional[str] = None,
        detail: Optional[str] = None,
        badge: str = "",
        display_label: Optional[str] = None,
    ) -> None:
        raw_title = str(node.get("title") or node.get("id") or "")
        cards.append({
            "id": card_id or str(node["id"]),
            "node_type": node["node_type"],
            "kind": str(node.get("type_label") or node["node_type"]),
            "title": raw_title,
            "display_label": display_label or raw_title,
            "summary": _compact_scene_text(node.get("snippet") or node.get("title")),
            "detail": detail if detail is not None else str(node.get("snippet") or node.get("title") or ""),
            "badge": badge or str(node.get("citation_id") or ""),
            "confidence": node.get("confidence"),
            "source_id": node.get("source_id") or "",
            "source_path": node.get("metadata", {}).get("source_path") or node.get("source_id") or "",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        })

    # Question pill (max ~60 chars)
    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "question"):
        q_text = str(node.get("title") or node.get("snippet") or "")
        if len(q_text) > 42:
            q_text = f"{q_text[:39]}…"
        append_card(node, x=40, y=50 + index * 54, width=220, height=44, display_label=q_text)

    # Answer pill
    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "answer"):
        ans_text = str(node.get("title") or "Câu trả lời")
        if len(ans_text) > 36:
            ans_text = f"{ans_text[:33]}…"
        append_card(node, x=290, y=50 + index * 54, width=200, height=44, display_label=ans_text)

    # Citation pill (compact [1], [2], etc.)
    for index, node in enumerate(n for n in view_model.nodes if n["node_type"] == "citation"):
        cid = str(node.get("citation_id") or f"[{index+1}]")
        col = index % 3
        row = index // 3
        append_card(node, x=520 + col * 86, y=50 + row * 48, width=76, height=38, display_label=cid, badge=cid)

    # Source pills (short filenames)
    for index, (source_key, nodes) in enumerate(source_groups.items()):
        first = nodes[0]
        group_id = f"document:{source_key}"
        citation_ids = [str(node.get("citation_id") or "") for node in nodes if node.get("citation_id")]
        grouped_detail = "\n\n".join(
            f"{node.get('citation_id') or node['id']}: {node.get('snippet') or ''}" for node in nodes
        )
        src_name = source_key.replace("\\", "/").split("/")[-1]
        if len(src_name) > 28:
            src_name = f"{src_name[:25]}…"
        append_card(
            first,
            x=810,
            y=50 + index * 54,
            width=240,
            height=44,
            card_id=group_id,
            display_label=src_name,
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

    highest_bottom = max((int(card["y"]) + int(card["height"]) for card in cards), default=360)
    return cards, edges, 1100, max(380, highest_bottom + 60)


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
                excaliflow_version = getattr(excaliflow, "__version__", "0.1.5")
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
        norm_loc = normalize_locale(locale)
        return _polish_evidence_atlas_html(ea.build_evidence_atlas_html(graph), graph, locale=norm_loc)

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
            "question": ("#0c4a6e", "#0284c7"),
            "answer": ("#064e3b", "#059669"),
            "citation": ("#451a03", "#d97706"),
            "source": ("#2e1065", "#7c3aed"),
        }

        edge_svg: List[str] = []
        for edge in edges:
            source = card_by_id[edge["source_id"]]
            target = card_by_id[edge["target_id"]]
            x1 = int(source["x"]) + int(source["width"])
            y1 = int(source["y"]) + int(source["height"]) // 2
            x2 = int(target["x"])
            y2 = int(target["y"]) + int(target["height"]) // 2
            edge_id = f"edge_{source['id']}_{target['id']}"
            edge_svg.append(
                f'<path class="scene-edge" id="{edge_id}" data-edge-id="{edge_id}" data-source="{html.escape(str(source["id"]), quote=True)}" data-target="{html.escape(str(target["id"]), quote=True)}" d="M{x1},{y1} C{x1 + 35},{y1} {x2 - 35},{y2} {x2},{y2}" />'
            )

        card_svg: List[str] = []
        for card in cards:
            fill, stroke = colors.get(str(card["node_type"]), ("#0f172a", "#64748b"))
            x, y = int(card["x"]), int(card["y"])
            w, h = int(card["width"]), int(card["height"])
            card_id = html.escape(str(card["id"]), quote=True)
            ntype = str(card["node_type"])
            is_micro = ntype in ("citation", "chunk")
            icon = {"question": "❓", "answer": "💡", "citation": "🏷️", "source": "📄"}.get(ntype, "🔹")
            disp_label = html.escape(str(card.get("display_label") or card["title"]))
            micro_class = " micro-dot" if is_micro else " hub-pill"
            card_svg.append(
                f'<g class="scene-node egv-node-card {html.escape(ntype, quote=True)}{micro_class}" tabindex="0" '
                f'role="button" data-node="{card_id}" data-type="{html.escape(ntype, quote=True)}" '
                f'data-base-x="{x}" data-base-y="{y}" data-base-w="{w}" data-base-h="{h}" '
                f'transform="translate({x}, {y})">'
                f'<rect class="scene-shadow" x="1" y="2" width="{w}" height="{h}" rx="20" />'
                f'<rect class="scene-card" x="0" y="0" width="{w}" height="{h}" rx="20" fill="{fill}" stroke="{stroke}" />'
                f'<text class="scene-pill-text" x="14" y="{h // 2 + 4}">'
                f'<tspan class="scene-icon">{icon} </tspan>'
                f'<tspan class="scene-label">{disp_label}</tspan>'
                f'</text></g>'
            )

        # Build Sidebar Entity Items
        entity_items_html: List[str] = []
        grouped_cards: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for c in cards:
            grouped_cards[str(c["node_type"])].append(c)

        group_labels = {
            "question": f"❓ {t('node_type_question', locale=norm_loc)}",
            "answer": f"💡 {t('node_type_answer', locale=norm_loc)}",
            "citation": f"🏷️ {t('citations', locale=norm_loc)}",
            "source": f"📄 {t('evidence_graph_source_nodes', locale=norm_loc)}",
        }
        for gtype in ("question", "answer", "citation", "source"):
            gitems = grouped_cards.get(gtype, [])
            if not gitems:
                continue
            entity_items_html.append(f'<div class="entity-group-label">{html.escape(group_labels.get(gtype, gtype))} ({len(gitems)})</div>')
            for c in gitems:
                c_icon = {"question": "❓", "answer": "💡", "citation": "🏷️", "source": "📄"}.get(str(c["node_type"]), "🔹")
                c_disp = html.escape(str(c.get("display_label") or c["title"]))
                c_badge = f'<span class="entity-badge" style="background:rgba(255,255,255,0.08);">{html.escape(str(c["badge"]))}</span>' if c.get("badge") else ""
                entity_items_html.append(
                    f'<div class="entity-item" data-node-ref="{html.escape(str(c["id"]), quote=True)}" '
                    f'data-search="{html.escape(str(c["title"]) + " " + str(c.get("detail", "")), quote=True)}">'
                    f'<span>{c_icon}</span>'
                    f'<span style="overflow:hidden; text-overflow:ellipsis;">{c_disp}</span>'
                    f'{c_badge}</div>'
                )
        entities_list_html = "".join(entity_items_html)

        payload = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")
        edges_payload = json.dumps(edges, ensure_ascii=False).replace("</", "<\\/")
        scene_payload = json.dumps(scene, ensure_ascii=False).replace("</", "<\\/")
        initial_detail_title = t("excalidraw_scene_select_node", locale=norm_loc)
        initial_detail_hint = t("excalidraw_scene_select_node_desc", locale=norm_loc)
        initial_detail_title_js = json.dumps(initial_detail_title, ensure_ascii=False)
        initial_detail_hint_js = json.dumps(initial_detail_hint, ensure_ascii=False)
        entities_title = t("entities_title", locale=norm_loc)
        inspector_title = t("inspector_title", locale=norm_loc)
        search_placeholder = t("search_entities_placeholder", locale=norm_loc)
        confidence_label = t("confidence_score", locale=norm_loc)
        source_file_label = t("source_file", locale=norm_loc)
        snippet_label = t("full_snippet", locale=norm_loc)
        copy_label = t("copy_snippet", locale=norm_loc)
        copied_label = t("copied_snippet", locale=norm_loc)
        zoom_in_label = t("zoom_in", locale=norm_loc)
        zoom_out_label = t("zoom_out", locale=norm_loc)
        fit_view_label = t("fit_view", locale=norm_loc)
        fullscreen_label = t("fullscreen_view", locale=norm_loc)
        collapse_label = t("collapse_panel", locale=norm_loc)
        expand_label = t("expand_panel", locale=norm_loc)
        inbound_label = t("inbound_links", locale=norm_loc)
        outbound_label = t("outbound_links", locale=norm_loc)
        radar_title = t("radar_title", locale=norm_loc)
        neighbors_pattern = t("neighbors_count", locale=norm_loc)
        galaxy_mode_label = t("galaxy_mode", locale=norm_loc)
        hierarchical_mode_label = t("hierarchical_mode", locale=norm_loc)
        layout_switch_label = t("layout_mode_switch", locale=norm_loc)
        drag_hint_label = t("drag_node_hint", locale=norm_loc)

        return f"""<!doctype html>
<html lang="{norm_loc}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root {{
  --bg-dark: #070b14;
  --panel-bg: #0f172a;
  --border-color: #1e293b;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --accent: #38bdf8;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0;
  background: var(--bg-dark);
  color: var(--text-main);
  font-family: {CJK_MULTI_LOCALE_FONT_STACK};
  height: 100%;
  overflow: hidden;
}}
.scene-shell {{
  padding: 4px;
  background: var(--bg-dark);
  height: 100%;
  box-sizing: border-box;
}}
.flowsint-layout {{
  display: flex;
  height: 100%;
  width: 100%;
  min-width: 0;
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
  position: relative;
}}
/* Column 1: Entities Sidebar */
.flowsint-sidebar {{
  flex: 0 1 200px;
  width: 200px;
  min-width: 148px;
  max-width: 30%;
  background: var(--panel-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}}
.sidebar-header {{
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
}}
.sidebar-title {{
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.search-input {{
  width: 100%;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s ease;
}}
.search-input:focus {{
  border-color: var(--accent);
}}
.entity-list {{
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
}}
.entity-group-label {{
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  margin: 10px 4px 4px;
}}
.entity-item {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.entity-item:hover {{
  background: rgba(30, 41, 59, 0.9);
  border-color: #475569;
}}
.entity-item.active {{
  background: rgba(56, 189, 248, 0.15);
  border-color: var(--accent);
  color: var(--accent);
}}
.entity-badge {{
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: auto;
}}

/* Column 2: Center Canvas */
.flowsint-canvas-wrapper {{
  flex: 1 1 360px;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  background-color: var(--bg-dark);
  background-image: radial-gradient(#1e293b 1px, transparent 1px);
  background-size: 20px 20px;
}}
.scene-head {{
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  border-bottom: 1px solid var(--border-color);
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(8px);
}}
.scene-head strong {{
  font-size: 14px;
  color: #f8fafc;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.scene-head span {{
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(56, 189, 248, 0.1);
  padding: 2px 8px;
  border-radius: 9999px;
  border: 1px solid rgba(56, 189, 248, 0.25);
}}
.scene-board {{
  flex: 1;
  overflow: hidden;
  position: relative;
  cursor: grab;
  user-select: none;
}}
.scene-board:active {{
  cursor: grabbing;
}}
.scene-floating-toolbar {{
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 50;
  display: flex;
  gap: 6px;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(8px);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}}
.scene-tool-btn {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #cbd5e1;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}}
.scene-tool-btn:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
  transform: translateY(-1px);
}}
.scene-tool-btn.active-mode {{
  background: rgba(56, 189, 248, 0.2);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}}
.scene-board svg {{
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  max-width: 100%;
  transform-origin: 0 0;
  transition: transform 0.05s ease-out;
}}
#mini-radar-svg {{
  min-width: 0 !important;
  width: 160px !important;
  max-width: 160px !important;
  height: 140px !important;
  display: block;
  margin: 0 auto;
  transform: none !important;
}}
@keyframes flowPulse {{
  from {{ stroke-dashoffset: 24; }}
  to {{ stroke-dashoffset: 0; }}
}}
.scene-edge {{
  fill: none;
  stroke: #475569;
  stroke-width: 1.8;
  stroke-dasharray: 4 3;
  transition: stroke 0.2s, stroke-width 0.2s, opacity 0.2s;
}}
.scene-edge.highlight {{
  stroke: var(--accent) !important;
  stroke-width: 3 !important;
  stroke-dasharray: 6 3 !important;
  animation: flowPulse 0.8s linear infinite !important;
  opacity: 1 !important;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.7));
}}
.scene-edge.dimmed {{
  opacity: 0.15;
}}
.scene-node {{
  cursor: grab;
  outline: none;
  transition: opacity 0.2s;
}}
.scene-node:active {{
  cursor: grabbing;
}}
.scene-node:hover .scene-card, .scene-node:focus .scene-card {{
  filter: brightness(1.25);
  stroke-width: 2.5;
}}
.scene-node.active .scene-card {{
  stroke: #38bdf8 !important;
  stroke-width: 3.5 !important;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.7));
}}
.scene-node.dimmed {{
  opacity: 0.25;
}}
.scene-pill-text {{
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  fill: #f8fafc;
}}
.scene-shadow {{
  fill: rgba(0, 0, 0, 0.35);
  stroke: none;
}}
.scene-card {{
  stroke-width: 1.8;
}}

/* Micro-dots & Level of Detail (LOD) */
.galaxy-mode .scene-node.micro-dot .scene-card {{
  rx: 9999px !important;
  stroke-width: 2px !important;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.5));
}}
.galaxy-mode .scene-node.micro-dot .scene-pill-text {{
  opacity: 0;
  transition: opacity 0.15s ease;
}}
.galaxy-mode .scene-node.micro-dot:hover .scene-pill-text,
.galaxy-mode .scene-node.micro-dot.active .scene-pill-text {{
  opacity: 1;
}}

/* Celestial Concentric Orbits Backdrop */
.galaxy-orbit-backdrop {{
  display: none;
  pointer-events: none;
}}
.galaxy-mode .galaxy-orbit-backdrop {{
  display: block;
}}
.celestial-orbit {{
  fill: none;
  stroke-width: 1.2;
}}
.celestial-orbit.orbit-core {{
  stroke: rgba(56, 189, 248, 0.22);
  stroke-dasharray: 4 6;
}}
.celestial-orbit.orbit-mid {{
  stroke: rgba(217, 119, 6, 0.2);
  stroke-dasharray: 4 6;
}}
.celestial-orbit.orbit-outer {{
  stroke: rgba(124, 58, 237, 0.2);
  stroke-dasharray: 6 8;
}}
.celestial-axis {{
  stroke: rgba(148, 163, 184, 0.08);
  stroke-width: 1;
  stroke-dasharray: 3 5;
}}

/* Mini Radar (Ego Graph / Neighbors Ring) */
.mini-radar-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  overflow: hidden;
  box-sizing: border-box;
}}
.mini-radar-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.mini-radar-count {{
  color: var(--accent);
  font-weight: 800;
}}
.mini-radar-canvas-wrap {{
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0f172a;
  border-radius: 6px;
  padding: 4px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
  max-width: 100%;
  box-sizing: border-box;
}}
.radar-orbit {{
  fill: none;
  stroke: #334155;
  stroke-width: 1;
  stroke-dasharray: 2 3;
}}
.radar-orbit.inner {{
  stroke: #1e293b;
}}
.radar-ray {{
  stroke: rgba(56, 189, 248, 0.35);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}}
.radar-dot {{
  stroke: #0f172a;
  stroke-width: 1.5;
  transition: all 0.2s ease;
  cursor: pointer;
}}
.radar-dot-group:hover .radar-dot {{
  r: 8;
  filter: drop-shadow(0 0 6px var(--accent));
}}
.radar-center {{
  fill: var(--accent);
  stroke: #0f172a;
  stroke-width: 2;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.8));
}}

/* Column 3: Inspector Panel */
.flowsint-inspector {{
  flex: 0 1 240px;
  width: 240px;
  min-width: 160px;
  max-width: 34%;
  background: var(--panel-bg);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1), padding 0.25s ease, min-width 0.25s ease;
}}
.flowsint-layout.inspector-collapsed .flowsint-inspector {{
  width: 0;
  min-width: 0;
  padding: 0;
  border-left: none;
  overflow: hidden;
  visibility: hidden;
}}
.inspector-header {{
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  margin-bottom: 14px;
}}
.inspector-main-title {{
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 6px;
  word-break: break-word;
}}
.inspector-type-badge {{
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 9999px;
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
}}
.inspector-field {{
  margin-bottom: 14px;
}}
.inspector-field-label {{
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}}
.inspector-gauge-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 14px;
}}
.inspector-gauge-header {{
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.inspector-gauge-track {{
  height: 6px;
  background: #0f172a;
  border-radius: 9999px;
  overflow: hidden;
}}
.inspector-gauge-bar {{
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background-color 0.3s ease;
}}
.inspector-links-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 14px;
}}
.inspector-links-title {{
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.inspector-chips-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}
.scene-link-chip {{
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.scene-link-chip:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
}}
.inspector-snippet-box {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #e2e8f0;
  max-height: 240px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}}
.copy-btn {{
  background: #334155;
  color: #f8fafc;
  border: 1px solid #475569;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}}
.copy-btn:hover {{
  background: #475569;
}}
.excalidraw-evidence-error {{
  padding: 16px;
  border: 1px solid #c28a10;
  border-radius: 10px;
  background: #fff7d8;
  color: #6c4a00;
}}
</style></head><body>
<main class="scene-shell" data-excalidraw-elements="{len(scene.get('elements', []))}">
<div class="flowsint-layout">
  <!-- Column 1: Entities Sidebar -->
  <aside class="flowsint-sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title"><span>📂</span> {html.escape(entities_title)}</div>
      <input type="text" id="entity-search" class="search-input" placeholder="{html.escape(search_placeholder)}" />
    </div>
    <div class="entity-list" id="entity-list">
      {entities_list_html}
    </div>
  </aside>

  <!-- Column 2: Center Canvas -->
  <div class="flowsint-canvas-wrapper">
    <div class="scene-head">
      <strong>🕸️ {html.escape(t('evidence_graph_title', locale=norm_loc))}</strong>
      <span>{html.escape(view_model.stats_label)}</span>
    </div>
    <section class="scene-board">
      <div class="scene-floating-toolbar" role="toolbar" aria-label="Canvas controls">
        <button type="button" id="scene-btn-toggle-layout" class="scene-tool-btn active-mode" title="{html.escape(layout_switch_label)}">🌌</button>
        <button type="button" id="scene-btn-zoom-in" class="scene-tool-btn" title="{html.escape(zoom_in_label)}">➕</button>
        <button type="button" id="scene-btn-zoom-out" class="scene-tool-btn" title="{html.escape(zoom_out_label)}">➖</button>
        <button type="button" id="scene-btn-fit" class="scene-tool-btn" title="{html.escape(fit_view_label)}">⊡</button>
        <button type="button" id="scene-btn-fullscreen" class="scene-tool-btn" title="{html.escape(fullscreen_label)}">⛶</button>
        <button type="button" id="scene-btn-toggle-inspector" class="scene-tool-btn" title="{html.escape(collapse_label)}">›</button>
      </div>
      <svg viewBox="0 0 {scene_width} {scene_height}" role="img" aria-label="Evidence graph in Flowsint style">
        <defs>
          <marker id="scene-arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto">
            <path d="M0,0 L9,4 L0,8" fill="none" stroke="#697586" stroke-width="1.5"/>
          </marker>
        </defs>
        <g class="galaxy-orbit-backdrop" id="galaxy-backdrop">
          <circle cx="{scene_width // 2}" cy="{scene_height // 2}" r="75" class="celestial-orbit orbit-core" />
          <circle cx="{scene_width // 2}" cy="{scene_height // 2}" r="195" class="celestial-orbit orbit-mid" />
          <circle cx="{scene_width // 2}" cy="{scene_height // 2}" r="355" class="celestial-orbit orbit-outer" />
          <line x1="{scene_width // 2 - 400}" y1="{scene_height // 2}" x2="{scene_width // 2 + 400}" y2="{scene_height // 2}" class="celestial-axis" />
          <line x1="{scene_width // 2}" y1="{scene_height // 2 - 400}" x2="{scene_width // 2}" y2="{scene_height // 2 + 400}" class="celestial-axis" />
        </g>
        {''.join(edge_svg)}
        {''.join(card_svg)}
      </svg>
    </section>
  </div>

  <!-- Column 3: Inspector Panel -->
  <aside class="flowsint-inspector scene-detail" aria-live="polite">
    <div class="inspector-header">
      <div class="sidebar-title"><span>🔍</span> {html.escape(inspector_title)}</div>
      <div class="inspector-main-title" id="scene-detail-title">{html.escape(initial_detail_title)}</div>
      <span class="inspector-type-badge" id="inspector-badge" style="display:none;"></span>
    </div>

    <!-- Mini Radar Inspector (Ego Graph) -->
    <div class="mini-radar-card" id="mini-radar-container" style="display:none;">
      <div class="mini-radar-header">
        <span>🛰️ {html.escape(radar_title)}</span>
        <span class="mini-radar-count" id="mini-radar-count">0</span>
      </div>
      <div class="mini-radar-canvas-wrap">
        <svg id="mini-radar-svg" viewBox="-80 -80 160 160" width="100%" height="150">
          <circle cx="0" cy="0" r="58" class="radar-orbit" />
          <circle cx="0" cy="0" r="32" class="radar-orbit inner" />
          <g id="radar-rays"></g>
          <g id="radar-neighbors"></g>
          <circle id="radar-center-node" cx="0" cy="0" r="9" class="radar-center" />
        </svg>
      </div>
    </div>

    <div class="inspector-field" id="inspector-meta-source" style="display:none;">
      <div class="inspector-field-label">{html.escape(source_file_label)}</div>
      <div id="inspector-source-val" style="font-size:12px; color:#a78bfa; word-break:break-all;"></div>
    </div>

    <div class="inspector-gauge-card" id="inspector-gauge-container" style="display:none;">
      <div class="inspector-gauge-header">
        <span>{html.escape(confidence_label)}</span>
        <span id="inspector-conf-val" style="color:#38bdf8; font-weight:800;">--%</span>
      </div>
      <div class="inspector-gauge-track">
        <div id="inspector-gauge-bar" class="inspector-gauge-bar" style="width:0%;"></div>
      </div>
    </div>

    <div class="inspector-links-card" id="inspector-links-container" style="display:none;">
      <div id="inspector-inbound-group" style="margin-bottom:8px;">
        <div class="inspector-links-title">📥 {html.escape(inbound_label)} (<span id="scene-inbound-count">0</span>)</div>
        <div id="scene-inbound-chips" class="inspector-chips-row"></div>
      </div>
      <div id="inspector-outbound-group">
        <div class="inspector-links-title">📤 {html.escape(outbound_label)} (<span id="scene-outbound-count">0</span>)</div>
        <div id="scene-outbound-chips" class="inspector-chips-row"></div>
      </div>
    </div>

    <div class="inspector-field">
      <div class="inspector-field-label">{html.escape(snippet_label)}</div>
      <div class="inspector-snippet-box" id="scene-detail-content">{html.escape(initial_detail_hint)}</div>
      <button type="button" class="copy-btn" id="inspector-copy-btn" style="display:none;">
        <span>📋</span> <span id="copy-btn-text">{html.escape(copy_label)}</span>
      </button>
    </div>
  </aside>
</div>
</main>

<script>
const EXCALIDRAW_SCENE = {scene_payload};
const INITIAL_DETAIL_TITLE = {initial_detail_title_js};
const INITIAL_DETAIL_HINT = {initial_detail_hint_js};
const NODES = {payload};
const EDGES = {edges_payload};
const byId = Object.fromEntries(NODES.map(node => [node.id, node]));
const NEIGHBORS_PATTERN = {json.dumps(neighbors_pattern, ensure_ascii=False)};

const titleElem = document.getElementById('scene-detail-title');
const contentElem = document.getElementById('scene-detail-content');
const badgeElem = document.getElementById('inspector-badge');
const metaSourceElem = document.getElementById('inspector-meta-source');
const sourceValElem = document.getElementById('inspector-source-val');
const gaugeContainer = document.getElementById('inspector-gauge-container');
const gaugeBar = document.getElementById('inspector-gauge-bar');
const confValElem = document.getElementById('inspector-conf-val');
const linksContainer = document.getElementById('inspector-links-container');
const inboundChips = document.getElementById('scene-inbound-chips');
const inboundCount = document.getElementById('scene-inbound-count');
const outboundChips = document.getElementById('scene-outbound-chips');
const outboundCount = document.getElementById('scene-outbound-count');
const copyBtn = document.getElementById('inspector-copy-btn');
const copyBtnText = document.getElementById('copy-btn-text');
const searchInput = document.getElementById('entity-search');

const board = document.querySelector('.scene-board');
const svg = board ? board.querySelector('svg') : null;
const layout = document.querySelector('.flowsint-layout');
const toggleInspectorBtn = document.getElementById('scene-btn-toggle-inspector');
const toggleLayoutBtn = document.getElementById('scene-btn-toggle-layout');

// --- Pan & Zoom Engine ---
let scale = 1.0;
let panX = 0;
let panY = 0;
let isPanning = false;
let startX = 0;
let startY = 0;

const updateTransform = () => {{
  if (!svg) return;
  svg.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
}};

if (board && svg) {{
  board.addEventListener('mousedown', (e) => {{
    if (e.target.closest('.scene-node') || e.target.closest('button') || e.target.closest('input')) return;
    isPanning = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    board.style.cursor = 'grabbing';
  }});

  window.addEventListener('mousemove', (e) => {{
    if (!isPanning) return;
    panX = e.clientX - startX;
    panY = e.clientY - startY;
    updateTransform();
  }});

  window.addEventListener('mouseup', () => {{
    isPanning = false;
    if (board) board.style.cursor = 'grab';
  }});

  board.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
    scale = Math.min(Math.max(0.3, scale * zoomFactor), 3.0);
    updateTransform();
  }}, {{ passive: false }});
}}

document.getElementById('scene-btn-zoom-in')?.addEventListener('click', () => {{
  scale = Math.min(3.0, scale * 1.2);
  updateTransform();
}});

document.getElementById('scene-btn-zoom-out')?.addEventListener('click', () => {{
  scale = Math.max(0.3, scale / 1.2);
  updateTransform();
}});

document.getElementById('scene-btn-fit')?.addEventListener('click', () => {{
  scale = 1.0;
  panX = 0;
  panY = 0;
  updateTransform();
}});

document.getElementById('scene-btn-fullscreen')?.addEventListener('click', () => {{
  const target = layout || document.documentElement;
  if (!document.fullscreenElement) {{
    target.requestFullscreen().catch(() => {{}});
  }} else {{
    document.exitFullscreen().catch(() => {{}});
  }}
}});

if (toggleInspectorBtn && layout) {{
  toggleInspectorBtn.addEventListener('click', () => {{
    const isCollapsed = layout.classList.toggle('inspector-collapsed');
    toggleInspectorBtn.textContent = isCollapsed ? '‹' : '›';
    toggleInspectorBtn.title = isCollapsed ? {json.dumps(expand_label, ensure_ascii=False)} : {json.dumps(collapse_label, ensure_ascii=False)};
  }});
}}

// --- Mini Radar Inspector (Ego Graph) ---
const TYPE_COLORS = {{
  'question': '#0284c7',
  'answer': '#059669',
  'citation': '#d97706',
  'source': '#7c3aed',
  'chunk': '#38bdf8',
  'document': '#a855f7'
}};

function updateMiniRadar(nodeId) {{
  const radarContainer = document.getElementById('mini-radar-container');
  if (!radarContainer) return;

  const inEdges = EDGES.filter(e => e.target_id === nodeId);
  const outEdges = EDGES.filter(e => e.source_id === nodeId);
  const neighborIds = [...new Set([...inEdges.map(e => e.source_id), ...outEdges.map(e => e.target_id)])].filter(id => id !== nodeId);

  const countSpan = document.getElementById('mini-radar-count');
  if (countSpan) {{
    countSpan.textContent = NEIGHBORS_PATTERN.replace('{{count}}', neighborIds.length);
  }}

  if (neighborIds.length === 0) {{
    radarContainer.style.display = 'none';
    return;
  }}
  radarContainer.style.display = 'block';

  const raysGroup = document.getElementById('radar-rays');
  const neighborsGroup = document.getElementById('radar-neighbors');
  const centerNode = document.getElementById('radar-center-node');
  if (!raysGroup || !neighborsGroup) return;

  const currNode = byId[nodeId];
  if (centerNode && currNode) {{
    centerNode.setAttribute('fill', TYPE_COLORS[currNode.node_type] || '#38bdf8');
  }}

  raysGroup.innerHTML = '';
  neighborsGroup.innerHTML = '';

  const R = 58;
  const n = neighborIds.length;
  let raysHtml = '';
  let dotsHtml = '';
  neighborIds.forEach((nbId, idx) => {{
    const angle = (2 * Math.PI * idx / n) - Math.PI / 2;
    const nx = Math.cos(angle) * R;
    const ny = Math.sin(angle) * R;
    const nbObj = byId[nbId] || {{}};
    const ntype = nbObj.node_type || 'chunk';
    const nbLabel = (nbObj.display_label || nbObj.title || nbId).replace(/"/g, '&quot;');
    const color = TYPE_COLORS[ntype] || '#38bdf8';

    raysHtml += `<line x1="0" y1="0" x2="${{nx.toFixed(1)}}" y2="${{ny.toFixed(1)}}" class="radar-ray" />`;
    dotsHtml += `<g class="radar-dot-group" cursor="pointer" onclick="showNode('${{nbId}}')">` +
                `<circle cx="${{nx.toFixed(1)}}" cy="${{ny.toFixed(1)}}" r="5.5" fill="${{color}}" class="radar-dot"><title>${{nbLabel}}</title></circle></g>`;
  }});
  raysGroup.innerHTML = raysHtml;
  neighborsGroup.innerHTML = dotsHtml;
}}

// --- Force-Directed Galaxy Simulation Engine ---
let currentLayout = 'galaxy';
let simNodes = [];
let simEdges = [];
let simRunning = true;
let animFrameId = null;
let draggedNode = null;
let dragStartX = 0;
let dragStartY = 0;
let nodeStartX = 0;
let nodeStartY = 0;

function initForceSimulation() {{
  const svgViewBox = svg ? svg.viewBox.baseVal : {{ width: 1200, height: 800 }};
  const cx = (svgViewBox.width || 1200) / 2;
  const cy = (svgViewBox.height || 800) / 2;

  const hubs = NODES.filter(n => n.node_type === 'answer' || n.node_type === 'question');
  const citations = NODES.filter(n => n.node_type === 'citation' || n.node_type === 'chunk');
  const docs = NODES.filter(n => n.node_type === 'source' || n.node_type === 'document');

  let hubIdx = 0, citeIdx = 0, docIdx = 0;
  simNodes = NODES.map((n) => {{
    const isHub = (n.node_type === 'answer' || n.node_type === 'question');
    const isCite = (n.node_type === 'citation' || n.node_type === 'chunk');
    const isDoc = (n.node_type === 'source' || n.node_type === 'document');

    let dist = 195;
    let angle = 0;
    let idealRadius = 195;
    let mass = 1.0;
    let w = Number(n.width) || 140;
    let h = Number(n.height) || 40;

    if (isHub) {{
      mass = 5.0;
      idealRadius = 35;
      dist = 15 + (hubIdx * 25);
      angle = hubs.length > 1 ? (2 * Math.PI * hubIdx / hubs.length) - Math.PI / 2 : 0;
      hubIdx++;
    }} else if (isCite) {{
      mass = 1.2;
      idealRadius = 195;
      dist = 185 + (citeIdx % 3) * 15;
      angle = (2 * Math.PI * citeIdx / (citations.length || 1)) - Math.PI / 2 + 0.15;
      w = 76;
      h = 38;
      citeIdx++;
    }} else if (isDoc) {{
      mass = 2.8;
      idealRadius = 355;
      dist = 345 + (docIdx % 3) * 20;
      angle = (2 * Math.PI * docIdx / (docs.length || 1)) - Math.PI / 2 + 0.35;
      w = 200;
      h = 44;
      docIdx++;
    }}

    const baseX = Number(n.x) || 0;
    const baseY = Number(n.y) || 0;

    return {{
      id: n.id,
      baseX: baseX,
      baseY: baseY,
      width: w,
      height: h,
      x: cx + Math.cos(angle) * dist,
      y: cy + Math.sin(angle) * dist,
      vx: 0,
      vy: 0,
      isHub: isHub,
      isCite: isCite,
      isDoc: isDoc,
      idealRadius: idealRadius,
      mass: mass,
      elem: document.querySelector(`.scene-node[data-node="${{n.id}}"]`)
    }};
  }});

  const simById = Object.fromEntries(simNodes.map(sn => [sn.id, sn]));
  simEdges = EDGES.map(e => ({{
    source: simById[e.source_id],
    target: simById[e.target_id],
    elem: document.getElementById(`edge_${{e.source_id}}_${{e.target_id}}`) || document.querySelector(`.scene-edge[data-source="${{e.source_id}}"][data-target="${{e.target_id}}"]`)
  }})).filter(e => e.source && e.target);

  let alpha = 1.0;
  function physicsTick() {{
    if (currentLayout !== 'galaxy') return;

    // Repulsion
    const kRepel = 4200;
    for (let i = 0; i < simNodes.length; i++) {{
      const n1 = simNodes[i];
      for (let j = i + 1; j < simNodes.length; j++) {{
        const n2 = simNodes[j];
        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let d2 = dx * dx + dy * dy + 1;
        let d = Math.sqrt(d2);
        if (d < 650) {{
          let force = (kRepel / (d2 + 90)) * alpha;
          let fx = (dx / d) * force;
          let fy = (dy / d) * force;
          if (n1 !== draggedNode) {{ n1.vx += fx / n1.mass; n1.vy += fy / n1.mass; }}
          if (n2 !== draggedNode) {{ n2.vx -= fx / n2.mass; n2.vy -= fy / n2.mass; }}
        }}
      }}
    }}

    // Springs with tiered distances
    const kSpring = 0.04;
    for (let e of simEdges) {{
      let dx = e.target.x - e.source.x;
      let dy = e.target.y - e.source.y;
      let d = Math.sqrt(dx * dx + dy * dy) || 1;
      let targetDist = 140;
      if (e.source.isHub || e.target.isHub) {{
        targetDist = 165;
      }} else if (e.source.isDoc || e.target.isDoc) {{
        targetDist = 185;
      }}
      let force = (d - targetDist) * kSpring * alpha;
      let fx = (dx / d) * force;
      let fy = (dy / d) * force;
      if (e.source !== draggedNode) {{ e.source.vx += fx / e.source.mass; e.source.vy += fy / e.source.mass; }}
      if (e.target !== draggedNode) {{ e.target.vx -= fx / e.target.mass; e.target.vy -= fy / e.target.mass; }}
    }}

    // Orbital concentric bias & gravity
    const kOrbit = 0.008;
    const kGravity = 0.012;
    for (let n of simNodes) {{
      if (n === draggedNode) continue;
      let dxC = n.x - cx;
      let dyC = n.y - cy;
      let distC = Math.sqrt(dxC * dxC + dyC * dyC) || 1;
      let rDelta = distC - n.idealRadius;
      n.vx -= (dxC / distC) * rDelta * kOrbit * alpha;
      n.vy -= (dyC / distC) * rDelta * kOrbit * alpha;

      n.vx += (cx - n.x) * kGravity * alpha;
      n.vy += (cy - n.y) * kGravity * alpha;
      n.vx *= 0.88;
      n.vy *= 0.88;
      n.x += n.vx;
      n.y += n.vy;
    }}

    // AABB Box Collision Resolution (Strict no-overlap)
    const pad = 12;
    for (let i = 0; i < simNodes.length; i++) {{
      const n1 = simNodes[i];
      const halfW1 = (n1.width / 2) + pad;
      const halfH1 = (n1.height / 2) + pad;
      for (let j = i + 1; j < simNodes.length; j++) {{
        const n2 = simNodes[j];
        const halfW2 = (n2.width / 2) + pad;
        const halfH2 = (n2.height / 2) + pad;

        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let minX = halfW1 + halfW2;
        let minY = halfH1 + halfH2;

        let overlapX = minX - Math.abs(dx);
        let overlapY = minY - Math.abs(dy);

        if (overlapX > 0 && overlapY > 0) {{
          if (overlapX < overlapY) {{
            let signX = dx >= 0 ? 1 : -1;
            let pushX = overlapX * 0.5;
            if (n1 !== draggedNode) n1.x += pushX * signX;
            if (n2 !== draggedNode) n2.x -= pushX * signX;
            n1.vx *= 0.5;
            n2.vx *= 0.5;
          }} else {{
            let signY = dy >= 0 ? 1 : -1;
            let pushY = overlapY * 0.5;
            if (n1 !== draggedNode) n1.y += pushY * signY;
            if (n2 !== draggedNode) n2.y -= pushY * signY;
            n1.vy *= 0.5;
            n2.vy *= 0.5;
          }}
        }}
      }}
    }}

    // Update positions
    for (let n of simNodes) {{
      if (n.elem) {{
        n.elem.setAttribute('transform', `translate(${{n.x - n.width / 2}}, ${{n.y - n.height / 2}})`);
      }}
    }}

    for (let e of simEdges) {{
      if (e.elem) {{
        const x1 = e.source.x;
        const y1 = e.source.y;
        const x2 = e.target.x;
        const y2 = e.target.y;
        const dx = x2 - x1;
        const dy = y2 - y1;
        const cx1 = x1 + dx * 0.4;
        const cy1 = y1 + dy * 0.1;
        const cx2 = x2 - dx * 0.4;
        const cy2 = y2 - dy * 0.1;
        e.elem.setAttribute('d', `M ${{x1.toFixed(1)}},${{y1.toFixed(1)}} C ${{cx1.toFixed(1)}},${{cy1.toFixed(1)}} ${{cx2.toFixed(1)}},${{cy2.toFixed(1)}} ${{x2.toFixed(1)}},${{y2.toFixed(1)}}`);
      }}
    }}

    alpha *= 0.993;
    if (alpha > 0.005 || draggedNode) {{
      animFrameId = requestAnimationFrame(physicsTick);
    }} else {{
      simRunning = false;
    }}
  }}

  animFrameId = requestAnimationFrame(physicsTick);
}}

function switchLayout(mode) {{
  currentLayout = mode;
  if (layout) {{
    layout.classList.toggle('galaxy-mode', mode === 'galaxy');
  }}
  if (toggleLayoutBtn) {{
    toggleLayoutBtn.classList.toggle('active-mode', mode === 'galaxy');
    toggleLayoutBtn.textContent = mode === 'galaxy' ? '🌌' : '📑';
    toggleLayoutBtn.title = mode === 'galaxy' ? {json.dumps(hierarchical_mode_label, ensure_ascii=False)} : {json.dumps(galaxy_mode_label, ensure_ascii=False)};
  }}

  if (mode === 'hierarchical') {{
    if (animFrameId) cancelAnimationFrame(animFrameId);
    simRunning = false;
    simNodes.forEach(n => {{
      if (n.elem) {{
        n.elem.setAttribute('transform', `translate(${{n.baseX}}, ${{n.baseY}})`);
      }}
    }});
    simEdges.forEach(e => {{
      if (e.elem) {{
        const x1 = e.source.baseX + e.source.width;
        const y1 = e.source.baseY + e.source.height / 2;
        const x2 = e.target.baseX;
        const y2 = e.target.baseY + e.target.height / 2;
        e.elem.setAttribute('d', `M ${{x1}},${{y1}} C ${{x1 + 35}},${{y1}} ${{x2 - 35}},${{y2}} ${{x2}},${{y2}}`);
      }}
    }});
  }} else {{
    initForceSimulation();
  }}
}}

if (toggleLayoutBtn) {{
  toggleLayoutBtn.addEventListener('click', () => {{
    switchLayout(currentLayout === 'galaxy' ? 'hierarchical' : 'galaxy');
  }});
}}

// --- Drag-and-Drop Node Physics ---
document.querySelectorAll('.scene-node').forEach(nodeEl => {{
  nodeEl.addEventListener('mousedown', (e) => {{
    e.stopPropagation();
    const nid = nodeEl.dataset.node;
    draggedNode = simNodes.find(sn => sn.id === nid);
    if (!draggedNode) return;

    dragStartX = e.clientX;
    dragStartY = e.clientY;
    nodeStartX = draggedNode.x;
    nodeStartY = draggedNode.y;

    if (!simRunning) {{
      simRunning = true;
      initForceSimulation();
    }}
  }});
}});

window.addEventListener('mousemove', (e) => {{
  if (!draggedNode) return;
  const dx = (e.clientX - dragStartX) / scale;
  const dy = (e.clientY - dragStartY) / scale;
  draggedNode.x = nodeStartX + dx;
  draggedNode.y = nodeStartY + dy;
  draggedNode.vx = 0;
  draggedNode.vy = 0;
}});

window.addEventListener('mouseup', () => {{
  draggedNode = null;
}});

function showNode(id) {{
  const node = byId[id];
  if (!node) return;

  titleElem.textContent = node.title;
  contentElem.textContent = node.detail || node.summary;

  if (badgeElem) {{
    badgeElem.textContent = node.kind || node.node_type;
    badgeElem.style.display = 'inline-block';
  }}

  if (metaSourceElem && sourceValElem) {{
    if (node.source_path || node.source_id) {{
      sourceValElem.textContent = node.source_path || node.source_id;
      metaSourceElem.style.display = 'block';
    }} else {{
      metaSourceElem.style.display = 'none';
    }}
  }}

  // Mini Radar update
  updateMiniRadar(id);

  // Confidence Gauge
  if (gaugeContainer && gaugeBar && confValElem) {{
    if (node.confidence !== null && node.confidence !== undefined) {{
      const pct = Math.round(Number(node.confidence) * 100);
      confValElem.textContent = pct + '%';
      gaugeBar.style.width = pct + '%';
      gaugeBar.style.backgroundColor = pct >= 80 ? 'var(--success)' : (pct >= 50 ? 'var(--warning)' : 'var(--danger)');
      gaugeContainer.style.display = 'block';
    }} else {{
      gaugeContainer.style.display = 'none';
    }}
  }}

  // Inbound & Outbound Connections
  if (linksContainer && inboundChips && outboundChips && inboundCount && outboundCount) {{
    const inEdges = EDGES.filter(e => e.target_id === id);
    const outEdges = EDGES.filter(e => e.source_id === id);

    inboundCount.textContent = inEdges.length;
    inboundChips.innerHTML = inEdges.map(e => {{
      const src = byId[e.source_id];
      const lbl = src ? (src.display_label || src.title) : e.source_id;
      return `<div class="scene-link-chip" onclick="showNode('${{e.source_id}}')">${{lbl}}</div>`;
    }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

    outboundCount.textContent = outEdges.length;
    outboundChips.innerHTML = outEdges.map(e => {{
      const tgt = byId[e.target_id];
      const lbl = tgt ? (tgt.display_label || tgt.title) : e.target_id;
      return `<div class="scene-link-chip" onclick="showNode('${{e.target_id}}')">${{lbl}}</div>`;
    }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

    linksContainer.style.display = (inEdges.length > 0 || outEdges.length > 0) ? 'block' : 'none';
  }}

  if (copyBtn) {{
    copyBtn.style.display = 'inline-flex';
    copyBtnText.textContent = {json.dumps(copy_label, ensure_ascii=False)};
  }}

  // Active state for nodes
  document.querySelectorAll('.scene-node').forEach(item => {{
    const isTarget = item.dataset.node === id;
    item.classList.toggle('active', isTarget);
    item.classList.toggle('dimmed', !isTarget);
  }});

  // Active state for sidebar entities
  document.querySelectorAll('.entity-item').forEach(item => {{
    item.classList.toggle('active', item.dataset.nodeRef === id);
  }});

  // Cross-highlight connected edges with flowing pulse
  const connectedIds = new Set([id]);
  document.querySelectorAll('.scene-edge').forEach(edge => {{
    const s = edge.dataset.source;
    const t = edge.dataset.target;
    if (s === id || t === id) {{
      edge.classList.add('highlight');
      edge.classList.remove('dimmed');
      if (s) connectedIds.add(s);
      if (t) connectedIds.add(t);
    }} else {{
      edge.classList.remove('highlight');
      edge.classList.add('dimmed');
    }}
  }});

  // Undim directly connected nodes
  document.querySelectorAll('.scene-node').forEach(item => {{
    if (connectedIds.has(item.dataset.node)) {{
      item.classList.remove('dimmed');
    }}
  }});
}}

// Node click and keydown
document.querySelectorAll('.scene-node').forEach(item => {{
  item.addEventListener('click', () => showNode(item.dataset.node));
  item.addEventListener('keydown', event => {{
    if (event.key === 'Enter' || event.key === ' ') {{
      event.preventDefault();
      showNode(item.dataset.node);
    }}
  }});
}});

// Sidebar click
document.querySelectorAll('.entity-item').forEach(item => {{
  item.addEventListener('click', () => showNode(item.dataset.nodeRef));
}});

// Realtime search
if (searchInput) {{
  searchInput.addEventListener('input', () => {{
    const q = searchInput.value.toLowerCase().trim();
    document.querySelectorAll('.entity-item').forEach(item => {{
      const searchTarget = (item.dataset.search || item.textContent).toLowerCase();
      item.style.display = searchTarget.includes(q) ? 'flex' : 'none';
    }});
  }});
}}

// Copy button
if (copyBtn) {{
  copyBtn.addEventListener('click', () => {{
    const textToCopy = contentElem.textContent || '';
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(textToCopy).then(() => {{
        copyBtnText.textContent = {json.dumps(copied_label, ensure_ascii=False)};
        setTimeout(() => {{
          copyBtnText.textContent = {json.dumps(copy_label, ensure_ascii=False)};
        }}, 2000);
      }});
    }}
  }});
}}

// Kick off simulation on page load
initForceSimulation();
</script></body></html>"""

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
