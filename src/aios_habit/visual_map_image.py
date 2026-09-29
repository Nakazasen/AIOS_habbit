"""Render a compact knowledge map to PNG with Pillow (no browser, no network).

The chat actions (TOOL-5) draw the local knowledge maps as images inside the
answer bubble through the proven `chart` block (TOOL-2). Streamlit's Mermaid
element was rejected for this: on the app page it computes a too-small viewBox
and cuts the diagram (see the TOOL-5 report). Pillow is already a project
dependency (`production_prediction/spc_chart.py` uses the same font fallback
idea), so the map is drawn server-side, deterministically and offline.

Layout: one column per zone (nodes grouped by zone, chunks of `_NODES_PER_COLUMN`),
nodes as rounded boxes, directed edges as elbow lines with optional labels.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:  # Pillow is a required dependency; degrade politely in odd test venvs.
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore

MARGIN = 28
TITLE_HEIGHT = 46
NODE_WIDTH = 240
NODE_HEIGHT = 62
NODE_V_GAP = 26
COLUMN_GAP = 76
NODES_PER_COLUMN = 6
MAX_EDGE_LABELS = 8
MAX_EDGES_DRAWN = 24
MAX_IMAGE_WIDTH = 1400
MAX_IMAGE_HEIGHT = 1000

# Columns that still fit inside MAX_IMAGE_WIDTH.
MAX_COLUMNS = max(
    1,
    (MAX_IMAGE_WIDTH - MARGIN * 2 + COLUMN_GAP) // (NODE_WIDTH + COLUMN_GAP),
)
MAX_IMAGE_NODES = MAX_COLUMNS * NODES_PER_COLUMN

_BACKGROUND = (255, 255, 255)
_TEXT = (15, 23, 42)
_LABEL_TEXT = (71, 85, 105)
_LINE = (148, 163, 184)
_ARROW = (100, 116, 139)

# Fill/border per node kind; unknown kinds use the neutral entry.
_KIND_COLORS: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
    "case": ((249, 168, 212), (190, 24, 93)),
    "evidence": ((191, 219, 254), (29, 78, 216)),
    "answer": ((187, 247, 208), (21, 128, 61)),
    "lesson": ((254, 202, 202), (185, 28, 28)),
    "system": ((221, 214, 254), (109, 40, 217)),
    "process": ((207, 250, 254), (14, 116, 144)),
    "setting": ((209, 250, 229), (4, 120, 87)),
    "error": ((254, 215, 215), (185, 28, 28)),
    "cause": ((253, 230, 138), (180, 83, 9)),
    "action": ((233, 213, 255), (109, 40, 217)),
    "learning": ((254, 202, 202), (185, 28, 28)),
    "document": ((226, 232, 240), (51, 65, 85)),
    "question": ((186, 230, 253), (3, 105, 161)),
    "citation": ((254, 240, 138), (161, 98, 7)),
    "source": ((221, 214, 254), (109, 40, 217)),
}
_DEFAULT_COLORS = ((226, 232, 240), (71, 85, 105))


@dataclass(frozen=True)
class MapNodeSpec:
    """One node of the picture: `kind` picks the colors, `zone` picks the column."""

    node_id: str
    label: str
    zone: str = "Khác"
    kind: str = "other"


@dataclass(frozen=True)
class MapEdgeSpec:
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class MapImageSpec:
    title: str = ""
    nodes: Sequence[MapNodeSpec] = field(default_factory=tuple)
    edges: Sequence[MapEdgeSpec] = field(default_factory=tuple)


@lru_cache(maxsize=64)
def _font(size: int):
    if ImageFont is None:  # pragma: no cover
        return None
    candidates = [
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(r"C:\Windows\Fonts\tahoma.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except (OSError, ValueError):
            continue
    try:
        return ImageFont.load_default()
    except Exception:  # pragma: no cover
        return None


def _text_width(draw, text: str, font) -> float:
    try:
        return draw.textlength(text, font=font)
    except AttributeError:  # pragma: no cover - very old Pillow
        return draw.textsize(text, font=font)[0]


def _wrap(draw, text: str, font, max_width: float, max_lines: int = 2) -> List[str]:
    """Greedy wrap; the last allowed line is ellipsized when the text overflows."""
    words = str(text or "").split()
    if not words:
        return []
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if len(lines) + 1 >= max_lines:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    trimmed: List[str] = []
    for line in lines:
        if _text_width(draw, line, font) > max_width:
            while line and _text_width(draw, line + "…", font) > max_width:
                line = line[:-1]
            line = line.rstrip() + "…"
        trimmed.append(line)
    return trimmed


def _columns(nodes: Sequence[MapNodeSpec]) -> List[List[MapNodeSpec]]:
    """Group nodes by zone into columns, chunking long zones for readable height."""
    order: List[str] = []
    grouped: Dict[str, List[MapNodeSpec]] = {}
    for node in nodes:
        zone = node.zone or "Khác"
        if zone not in grouped:
            order.append(zone)
            grouped[zone] = []
        grouped[zone].append(node)
    columns: List[List[MapNodeSpec]] = []
    for zone in order:
        chunk = grouped[zone]
        for start in range(0, len(chunk), NODES_PER_COLUMN):
            columns.append(chunk[start : start + NODES_PER_COLUMN])
    return columns


def _box_layout(columns: Sequence[Sequence[MapNodeSpec]]) -> Dict[str, Tuple[int, int, int, int]]:
    boxes: Dict[str, Tuple[int, int, int, int]] = {}
    top = MARGIN + TITLE_HEIGHT
    for column_index, column in enumerate(columns):
        left = MARGIN + column_index * (NODE_WIDTH + COLUMN_GAP)
        for row_index, node in enumerate(column):
            box_top = top + row_index * (NODE_HEIGHT + NODE_V_GAP)
            boxes[node.node_id] = (left, box_top, left + NODE_WIDTH, box_top + NODE_HEIGHT)
    return boxes


def _edge_anchor(box: Tuple[int, int, int, int], towards: Tuple[float, float]) -> Tuple[int, int]:
    """Point on the box border on the segment from the box center towards `towards`."""
    left, top, right, bottom = box
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    dx = towards[0] - center_x
    dy = towards[1] - center_y
    if dx == 0 and dy == 0:
        return int(center_x), int(center_y)
    scale_x = (NODE_WIDTH / 2) / abs(dx) if dx else float("inf")
    scale_y = (NODE_HEIGHT / 2) / abs(dy) if dy else float("inf")
    scale = min(scale_x, scale_y)
    return int(center_x + dx * scale), int(center_y + dy * scale)


def _arrowhead(draw, tip: Tuple[int, int], direction: Tuple[float, float]) -> None:
    length = 9
    half_width = 4.5
    dx, dy = direction
    norm = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / norm, dy / norm
    base_x, base_y = tip[0] - ux * length, tip[1] - uy * length
    px, py = -uy, ux
    draw.polygon(
        [
            tip,
            (base_x + px * half_width, base_y + py * half_width),
            (base_x - px * half_width, base_y - py * half_width),
        ],
        fill=_ARROW,
    )


def render_map_png(spec: MapImageSpec) -> bytes:
    """Draw the map and return PNG bytes (an empty spec still returns a valid PNG)."""
    if Image is None:  # pragma: no cover
        raise RuntimeError("Pillow không sẵn sàng để vẽ bản đồ")

    font_label = _font(14)
    font_zone = _font(12)
    font_title = _font(16)
    font_edge = _font(12)

    nodes = [node for node in spec.nodes if str(node.node_id)]
    columns = _columns(nodes)[:MAX_COLUMNS]
    boxes = _box_layout(columns)

    column_count = max(1, len(columns))
    content_bottom = max((box[3] for box in boxes.values()), default=MARGIN + TITLE_HEIGHT)
    width = min(
        MAX_IMAGE_WIDTH,
        MARGIN * 2 + column_count * NODE_WIDTH + (column_count - 1) * COLUMN_GAP,
    )
    height = min(MAX_IMAGE_HEIGHT, int(content_bottom + MARGIN))

    image = Image.new("RGB", (width, height), _BACKGROUND)
    draw = ImageDraw.Draw(image)

    for column_index, column in enumerate(columns):
        if not column:
            continue
        left = MARGIN + column_index * (NODE_WIDTH + COLUMN_GAP)
        zone_lines = _wrap(draw, column[0].zone or "Khác", font_zone, NODE_WIDTH, 1)
        if zone_lines:
            draw.text((left, MARGIN - 6), zone_lines[0], font=font_zone, fill=_LABEL_TEXT)

    if spec.title:
        title_lines = _wrap(draw, spec.title, font_title, max(200, width - 2 * MARGIN), 1)
        if title_lines:
            draw.text((MARGIN, MARGIN - 34), title_lines[0], font=font_title, fill=_TEXT)

    # Edges first so the node boxes sit on top.
    edge_labels: List[Tuple[int, int, str]] = []
    known = set(boxes)
    drawn_edges = [
        edge for edge in spec.edges if edge.source in known and edge.target in known
    ][:MAX_EDGES_DRAWN]
    draw_edge_labels = len(drawn_edges) <= MAX_EDGE_LABELS
    for edge in drawn_edges:
        source_box = boxes[edge.source]
        target_box = boxes[edge.target]
        source_center = ((source_box[0] + source_box[2]) / 2, (source_box[1] + source_box[3]) / 2)
        target_center = ((target_box[0] + target_box[2]) / 2, (target_box[1] + target_box[3]) / 2)
        start = _edge_anchor(source_box, target_center)
        end = _edge_anchor(target_box, source_center)
        mid_x = (start[0] + end[0]) // 2
        points = [start, (mid_x, start[1]), (mid_x, end[1]), end]
        draw.line(points, fill=_LINE, width=2, joint="curve")
        _arrowhead(draw, end, (end[0] - mid_x, 0.0))
        label = str(edge.label or "").strip()
        if label and draw_edge_labels:
            edge_labels.append((mid_x, (start[1] + end[1]) // 2, label))

    for label_index, (label_x, label_y, label) in enumerate(edge_labels):
        label_lines = _wrap(draw, label, font_edge, COLUMN_GAP - 6, 1)
        if not label_lines:
            continue
        text = label_lines[0]
        text_w = _text_width(draw, text, font_edge)
        label_y += (label_index % 3) * 16
        draw.rectangle(
            (label_x - text_w / 2 - 3, label_y - 16, label_x + text_w / 2 + 3, label_y - 3),
            fill=_BACKGROUND,
            outline=(203, 213, 225),
        )
        draw.text((label_x - text_w / 2, label_y - 15), text, font=font_edge, fill=_LABEL_TEXT)

    for node in nodes:
        box = boxes.get(node.node_id)
        if box is None:
            continue
        fill, border = _KIND_COLORS.get(str(node.kind or "").lower(), _DEFAULT_COLORS)
        draw.rounded_rectangle(box, radius=10, fill=fill, outline=border, width=2)
        lines = _wrap(draw, node.label, font_label, NODE_WIDTH - 24, 2)
        text_top = box[1] + (NODE_HEIGHT - len(lines) * 18) // 2
        for index, line in enumerate(lines):
            text_w = _text_width(draw, line, font_label)
            draw.text(
                (box[0] + (NODE_WIDTH - text_w) / 2, text_top + index * 18),
                line,
                font=font_label,
                fill=_TEXT,
            )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
