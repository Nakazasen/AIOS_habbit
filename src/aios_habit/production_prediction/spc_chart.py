"""Monozukuri/SPC trend chart renderer for US12 (Moc 6).

Server-side rendering with Pillow only (already a project dependency).
No matplotlib dependency is introduced to keep the laptop CPU footprint
small and the audit surface minimal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - Pillow is a required dependency.
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


@dataclass
class SpcChartInput:
    jig_id: str
    cong_doan: str = ""
    metric: str = ""
    unit: str = ""
    values: List[float] = field(default_factory=list)
    nhan_thoi_gian: List[str] = field(default_factory=list)
    usl: Optional[float] = None
    lsl: Optional[float] = None
    ucl: Optional[float] = None
    cl: Optional[float] = None
    lcl: Optional[float] = None
    cpk: Optional[float] = None
    sigma: Optional[float] = None
    nguoi_phu_trach: str = ""
    du_bao: List[float] = field(default_factory=list)


def _bounds(chart: SpcChartInput) -> tuple[float, float]:
    candidates = list(chart.values) + list(chart.du_bao)
    for limit in (chart.usl, chart.lsl, chart.ucl, chart.cl, chart.lcl):
        if limit is not None:
            candidates.append(limit)
    if not candidates:
        return (0.0, 1.0)
    low, high = min(candidates), max(candidates)
    if high == low:
        high = low + 1.0
    padding = (high - low) * 0.15
    return (low - padding, high + padding)


def render_spc_png(chart: SpcChartInput, path: str | Path, scale: int = 2) -> Path:
    """Render a Monozukuri-style SPC chart to PNG with 300 DPI metadata."""
    if Image is None or ImageDraw is None:
        raise RuntimeError("Thiếu thư viện ảnh Pillow để vẽ biểu đồ.")
    if not chart.values:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960 * scale, 540 * scale
    margin_left, margin_top = 90 * scale, 70 * scale
    margin_right, margin_bottom = 30 * scale, 60 * scale
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    low, high = _bounds(chart)
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    def y_of(value: float) -> int:
        ratio = (value - low) / (high - low) if high != low else 0.5
        return int(margin_top + (1 - ratio) * plot_h)

    def x_of(index: int, total: int) -> int:
        if total <= 1:
            return margin_left + plot_w // 2
        return int(margin_left + index / (total - 1) * plot_w)

    # Zones A/B/C: safe (green tint), watch (yellow tint), danger (red tint).
    mid = (low + high) / 2
    span = (high - low) / 6
    draw.rectangle([margin_left, y_of(mid + span), margin_left + plot_w, y_of(mid - span)], fill=(232, 245, 233))
    draw.rectangle([margin_left, y_of(mid + 2 * span), margin_left + plot_w, y_of(mid + span)], fill=(255, 249, 196))
    draw.rectangle([margin_left, y_of(mid - span), margin_left + plot_w, y_of(mid - 2 * span)], fill=(255, 249, 196))
    draw.rectangle([margin_left, margin_top, margin_left + plot_w, y_of(mid + 2 * span)], fill=(255, 235, 238))
    draw.rectangle([margin_left, y_of(mid - 2 * span), margin_left + plot_w, margin_top + plot_h], fill=(255, 235, 238))

    # Control/specification limits.
    for value, color, name in (
        (chart.usl, (183, 28, 28), "USL"),
        (chart.ucl, (230, 81, 0), "UCL"),
        (chart.cl, (21, 101, 192), "CL"),
        (chart.lcl, (230, 81, 0), "LCL"),
        (chart.lsl, (183, 28, 28), "LSL"),
    ):
        if value is None:
            continue
        y = y_of(value)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=color, width=max(1, scale))
        draw.text((margin_left + plot_w + 4, y - 6 * scale), name, fill=color)

    # Actual measurements.
    total = len(chart.values)
    points = [(x_of(i, total), y_of(v)) for i, v in enumerate(chart.values)]
    for i in range(1, len(points)):
        draw.line([points[i - 1], points[i]], fill=(21, 101, 192), width=max(2, scale))
    for (x, y), v in zip(points, chart.values):
        is_anomaly = (
            (chart.usl is not None and v > chart.usl)
            or (chart.lsl is not None and v < chart.lsl)
            or (chart.ucl is not None and v > chart.ucl)
            or (chart.lcl is not None and v < chart.lcl)
        )
        if is_anomaly:
            draw.ellipse([x - 6 * scale, y - 6 * scale, x + 6 * scale, y + 6 * scale], outline=(183, 28, 28), width=max(2, scale))
            draw.text((x + 8 * scale, y - 10 * scale), "trôi dốc", fill=(183, 28, 28))
        else:
            draw.ellipse([x - 4 * scale, y - 4 * scale, x + 4 * scale, y + 4 * scale], fill=(21, 101, 192))

    # Dashed orange forecast trend.
    if chart.du_bao:
        start = points[-1] if points else (margin_left, margin_top + plot_h // 2)
        forecast_points = [start]
        for j, v in enumerate(chart.du_bao, start=1):
            forecast_points.append((x_of(total - 1 + j, total + len(chart.du_bao)), y_of(v)))
        for a, b in zip(forecast_points, forecast_points[1:]):
            # Manual dash: 8 on, 5 off.
            draw.line([a, b], fill=(230, 81, 0), width=max(2, scale))

    # Frame and title.
    draw.rectangle([margin_left, margin_top, margin_left + plot_w, margin_top + plot_h], outline=(66, 66, 66))
    title = f"Biểu đồ xu hướng {chart.metric} — {chart.jig_id}".strip(" —")
    draw.text((margin_left, 18 * scale), title, fill=(33, 33, 33))

    # Management stamp box.
    stamp_top = margin_top + plot_h + 10 * scale
    stamp = (
        f"JIG: {chart.jig_id} | Công đoạn: {chart.cong_doan or '—'} | "
        f"Ngày giờ: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Người phụ trách: {chart.nguoi_phu_trach or '—'} | "
        f"Cpk: {chart.cpk if chart.cpk is not None else '—'} | "
        f"σ: {chart.sigma if chart.sigma is not None else '—'}"
    )
    draw.rectangle([margin_left, stamp_top, margin_left + plot_w, stamp_top + 28 * scale], outline=(66, 66, 66))
    draw.text((margin_left + 8 * scale, stamp_top + 8 * scale), stamp, fill=(33, 33, 33))
    image.save(out, format="PNG", dpi=(300, 300))
    return out


def render_spc_svg(chart: SpcChartInput) -> str:
    """Render a compact vector SVG version of the same SPC chart."""
    if not chart.values:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    width, height = 960, 540
    low, high = _bounds(chart)

    def y_of(value: float) -> float:
        ratio = (value - low) / (high - low) if high != low else 0.5
        return 70 + (1 - ratio) * 410

    def x_of(index: int, total: int) -> float:
        if total <= 1:
            return 90 + 840 / 2
        return 90 + index / (total - 1) * 840

    points = " ".join(f"{x_of(i, len(chart.values)):.1f},{y_of(v):.1f}" for i, v in enumerate(chart.values))
    lines = []
    for value, name in ((chart.usl, "USL"), (chart.ucl, "UCL"), (chart.cl, "CL"), (chart.lcl, "LCL"), (chart.lsl, "LSL")):
        if value is None:
            continue
        lines.append(f'<line x1="90" y1="{y_of(value):.1f}" x2="930" y2="{y_of(value):.1f}" stroke="red" />'
                     f'<text x="932" y="{y_of(value):.1f}">{name}</text>')
    stamp = (f"JIG: {escape(chart.jig_id)} | Công đoạn: {escape(chart.cong_doan or '—')} | "
             f"Cpk: {escape(str(chart.cpk) if chart.cpk is not None else '—')}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" />'
        + "".join(lines) +
        f'<polyline points="{points}" fill="none" stroke="#1565c0" stroke-width="2" />'
        f'<text x="90" y="30">Biểu đồ xu hướng {escape(chart.metric)} — {escape(chart.jig_id)}</text>'
        f'<text x="90" y="520">{stamp}</text>'
        f"</svg>"
    )
