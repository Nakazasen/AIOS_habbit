"""Monozukuri/SPC chart renderer for US12 (Moc 6) and 015-csv-chart-selector.

Server-side rendering with Pillow only (already a project dependency).
No matplotlib dependency is introduced to keep the laptop CPU footprint
small and the audit surface minimal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Union
from xml.sax.saxutils import escape

from aios_habit.chart_theme import (
    RGB_PRIMARY_BLUE,
    RGB_ACCENT_ORANGE,
    RGB_SMA_PURPLE,
    RGB_LIMIT_RED,
    RGB_WARN_ORANGE,
    RGB_CENTER_GREEN,
    RGB_ANOMALY_RED,
    RGB_GRID_GRAY,
    RGB_BORDER_GRAY,
    RGB_TEXT_TITLE,
    RGB_TEXT_LABEL,
    RGB_TEXT_MUTED,
    RGB_ZONE_SAFE_GREEN,
    RGB_ZONE_WARN_YELLOW,
    RGB_ZONE_DANGER_RED,
    RGB_PALETTE_DISTINCT,
    get_pillow_font,
    format_chart_title,
    format_chart_title_parts,
    format_axis_label,
    detect_unit_from_metric,
    format_time_range_from_sequence,
)


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - Pillow is a required dependency.
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


_FONT_CACHE: dict = {}


def _font(scale: int = 1, lon: bool = False, nho: bool = False):
    """Load a Vietnamese-capable system font using shared chart_theme font system."""
    co_chu = (20 if lon else (11 if nho else 14)) * max(1, int(scale))
    key = (co_chu, lon, nho)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    f_theme = get_pillow_font(size=co_chu, bold=bool(lon))
    if f_theme is not None:
        _FONT_CACHE[key] = f_theme
        return f_theme

    ket_qua = None
    if ImageFont is not None:
        import os

        ung_vien = [
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts", "segoeui.ttf"),
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts", "arial.ttf"),
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for duong_dan in ung_vien:
            try:
                ket_qua = ImageFont.truetype(duong_dan, co_chu)
                break
            except (OSError, ValueError):
                continue
    if ket_qua is None and ImageFont is not None:
        try:
            ket_qua = ImageFont.load_default()
        except Exception:
            ket_qua = None
    _FONT_CACHE[key] = ket_qua
    return ket_qua


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
    # True khi biểu đồ chưa có giới hạn thật và chỉ vẽ dải tham khảo.
    mo_phong: bool = False

    def ghi_chu_mo_phong(self) -> str:
        """Dòng ghi chú bắt buộc khi dải giới hạn là tham khảo (dữ liệu vẫn là thật)."""
        if not self.mo_phong:
            return ""
        return (
            "LƯU Ý: chỉ số này chưa có giới hạn trên/dưới thật nên dải giới hạn "
            "trên hình chỉ là tham khảo (trung bình ± 3 độ lệch chuẩn); "
            "đường dữ liệu là số liệu thật."
        )


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


def _co_chuoi_mo_phong(cac_chart: Sequence[SpcChartInput]) -> bool:
    """True khi **bất kỳ** chuỗi nào chưa có giới hạn thật.

    Biểu đồ so sánh nhiều màu là mô phỏng nếu còn một chuỗi thiếu giới hạn; chỉ
    xét chuỗi đầu tiên sẽ cho kết quả ngược nhau tuỳ thứ tự chuỗi.
    """
    return any(getattr(c, "mo_phong", False) for c in cac_chart)


def _svg_mo_phong(chart: SpcChartInput, *, ep_buoc: bool = False) -> str:
    """Dòng chữ cảnh báo cho bản SVG khi dải giới hạn chỉ là tham khảo."""
    if not (chart.mo_phong or ep_buoc):
        return ""
    return (
        '<text x="90" y="18" fill="#b71c1c" font-size="16" font-weight="bold">'
        "DẢI GIỚI HẠN LÀ THAM KHẢO — chưa có giới hạn thật (±3σ); dữ liệu là số liệu thật"
        "</text>"
    )


def _ve_bang_mo_phong(draw, chart: SpcChartInput, width: int, margin_left: int, plot_w: int,
                      scale: int, *, ep_buoc: bool = False) -> None:
    """Vẽ băng cảnh báo ngay dưới tiêu đề để không ai đọc nhầm dải tham khảo
    thành giới hạn kỹ thuật.

    Băng này là bắt buộc khi biểu đồ chưa có giới hạn thật: nếu chỉ ghi trong
    chú thích chat thì người nhận ảnh (hoặc email) vẫn có thể tưởng nhầm đường
    tham khảo là giới hạn kỹ thuật.
    """
    if not (chart.mo_phong or ep_buoc):
        return
    y = 46 * scale
    cao = 26 * scale
    draw.rectangle([margin_left, y, margin_left + plot_w, y + cao], fill=(255, 235, 238),
                   outline=(183, 28, 28))
    draw.text(
        (margin_left + 8 * scale, y + 6 * scale),
        "DẢI GIỚI HẠN LÀ THAM KHẢO — chưa có giới hạn thật (±3σ); dữ liệu là số liệu thật",
        fill=(183, 28, 28), font=_font(scale, lon=False),
    )


def _ve_tieu_de_pillow(
    draw,
    *,
    chart_kind: str,
    metric: str,
    jig_id: str = "",
    time_range: str = "",
    unit: str = "",
    margin_left: int,
    plot_w: int,
    scale: int,
) -> None:
    """Vẽ tiêu đề Pillow 1 hoặc 2 dòng tự động thích ứng nhằm chống cắt mép 100%."""
    main_title, subtitle = format_chart_title_parts(
        chart_kind=chart_kind,
        metric=metric,
        jig_id=jig_id,
        time_range=time_range,
        unit=unit,
    )
    font_main = _font(scale, lon=True)
    font_sub = _font(scale, lon=False, nho=False)

    if subtitle:
        full_line = f"{main_title} — {subtitle}"
        bbox = draw.textbbox((0, 0), full_line, font=font_main)
        # Nếu dòng đơn vừa vặn trong plot_w - 20*scale thì vẽ 1 dòng
        if (bbox[2] - bbox[0]) <= plot_w - 20 * scale:
            draw.text((margin_left, 16 * scale), full_line, fill=RGB_TEXT_TITLE, font=font_main)
            return

        # Nếu dài hơn thì tách 2 dòng phân tầng chuyên nghiệp
        bbox_m = draw.textbbox((0, 0), main_title, font=font_main)
        if (bbox_m[2] - bbox_m[0]) > plot_w - 10 * scale:
            font_main = _font(scale, lon=False, nho=False)
        draw.text((margin_left, 10 * scale), main_title, fill=RGB_TEXT_TITLE, font=font_main)
        draw.text((margin_left, 36 * scale), subtitle, fill=RGB_TEXT_LABEL, font=font_sub)
    else:
        draw.text((margin_left, 16 * scale), main_title, fill=RGB_TEXT_TITLE, font=font_main)


def _ve_tem_quan_ly(
    draw,
    chart: SpcChartInput,
    margin_left: int,
    plot_w: int,
    stamp_top: int,
    scale: int,
) -> None:
    """Vẽ tem quản lý / caption dưới cùng biểu đồ, tự động căn 1 hoặc 2 dòng chống cắt chữ."""
    stamp_font = _font(scale, nho=True)
    sigma_txt = f"{chart.sigma:.2f}" if chart.sigma is not None else "—"
    cpk_txt = f"{chart.cpk:.2f}" if isinstance(chart.cpk, (int, float)) else (str(chart.cpk) if chart.cpk is not None else "—")

    single_stamp = (
        f"JIG: {chart.jig_id} | Công đoạn: {chart.cong_doan or '—'} | "
        f"Ngày giờ: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Người phụ trách: {chart.nguoi_phu_trach or '—'} | "
        f"Cpk: {cpk_txt} | σ: {sigma_txt}"
    )
    bbox = draw.textbbox((0, 0), single_stamp, font=stamp_font)
    tw = bbox[2] - bbox[0]
    if tw <= plot_w - 16 * scale:
        draw.rectangle([margin_left, stamp_top, margin_left + plot_w, stamp_top + 28 * scale],
                       fill=(248, 249, 250), outline=RGB_BORDER_GRAY)
        draw.text((margin_left + 8 * scale, stamp_top + 6 * scale), single_stamp, fill=RGB_TEXT_MUTED, font=stamp_font)
    else:
        line1 = f"JIG: {chart.jig_id} | Công đoạn: {chart.cong_doan or '—'} | Ngày giờ: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        line2 = f"Người phụ trách: {chart.nguoi_phu_trach or '—'} | Cpk: {cpk_txt} | σ: {sigma_txt}"
        box_h = 32 * scale
        draw.rectangle([margin_left, stamp_top - 2 * scale, margin_left + plot_w, stamp_top - 2 * scale + box_h],
                       fill=(248, 249, 250), outline=RGB_BORDER_GRAY)
        draw.text((margin_left + 8 * scale, stamp_top + 1 * scale), line1, fill=RGB_TEXT_MUTED, font=stamp_font)
        draw.text((margin_left + 8 * scale, stamp_top + 15 * scale), line2, fill=RGB_TEXT_MUTED, font=stamp_font)


def _format_smart_x_ticks(
    nhan_thoi_gian: Sequence[str],
    indices: List[int],
) -> List[str]:
    """Smart tick sampling cho trục X: đảm bảo nhãn rõ nghĩa và KHÔNG BAO GIỜ bị lặp."""
    if not nhan_thoi_gian:
        return [str(i + 1) for i in indices]

    raw_sampled = [str(nhan_thoi_gian[i]).strip() if i < len(nhan_thoi_gian) else str(i + 1) for i in indices]

    # Kiểm tra nếu toàn bộ nhãn được lấy mẫu giống hệt nhau (ví dụ: toàn bộ đều là "2026.07.01")
    if len(set(raw_sampled)) == 1 and len(raw_sampled) > 1:
        return [f"#{i + 1}" for i in indices]

    # Nếu nhãn có khoảng trắng (Date Time), kiểm tra xem ngày có giống hệt nhau không
    has_datetime_space = all(" " in s for s in raw_sampled if s)
    if has_datetime_space:
        dates = [s.split(" ")[0] for s in raw_sampled]
        times = [s.split(" ")[1] for s in raw_sampled]
        if len(set(dates)) == 1 and len(set(times)) == len(times):
            return times

    # Khử lặp cục bộ nếu có các tick kế cận bị trùng nhãn
    result: List[str] = []
    seen_counts: Dict[str, int] = {}
    for i, lbl in zip(indices, raw_sampled):
        if lbl in seen_counts:
            seen_counts[lbl] += 1
            result.append(f"{lbl} (#{i + 1})")
        else:
            seen_counts[lbl] = 1
            result.append(lbl)
    return result


def _detect_x_axis_label(nhan_thoi_gian: Sequence[str]) -> str:
    """Tự động suy luận nhãn trục X khớp đúng loại tick hiển thị."""
    if not nhan_thoi_gian:
        return "Trục hoành: Thứ tự điểm đo"
    sample = " ".join(str(s) for s in nhan_thoi_gian[:25]).lower()
    if "tuần" in sample or "tuan" in sample or "week" in sample:
        return "Trục hoành: Tuần sản xuất"
    elif "tháng" in sample or "thang" in sample or "month" in sample:
        return "Trục hoành: Tháng sản xuất"
    elif "ca" in sample or "shift" in sample:
        return "Trục hoành: Ca sản xuất"
    elif any(sep in sample for sep in (":", "-", "/", ".")):
        return "Trục hoành: Mốc thời gian"
    return "Trục hoành: Thứ tự điểm đo"


def render_spc_png(chart: SpcChartInput, path: str | Path, scale: int = 2) -> Path:
    """Render a Monozukuri-style SPC chart to PNG with 300 DPI metadata."""
    if Image is None or ImageDraw is None:
        raise RuntimeError("Thiếu thư viện ảnh Pillow để vẽ biểu đồ.")
    if not chart.values:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1000 * scale, 560 * scale
    margin_left, margin_top = 110 * scale, 75 * scale
    margin_right, margin_bottom = 85 * scale, 80 * scale
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
    draw.rectangle([margin_left, y_of(mid + span), margin_left + plot_w, y_of(mid - span)], fill=RGB_ZONE_SAFE_GREEN)
    draw.rectangle([margin_left, y_of(mid + 2 * span), margin_left + plot_w, y_of(mid + span)], fill=RGB_ZONE_WARN_YELLOW)
    draw.rectangle([margin_left, y_of(mid - span), margin_left + plot_w, y_of(mid - 2 * span)], fill=RGB_ZONE_WARN_YELLOW)
    draw.rectangle([margin_left, margin_top, margin_left + plot_w, y_of(mid + 2 * span)], fill=RGB_ZONE_DANGER_RED)
    draw.rectangle([margin_left, y_of(mid - 2 * span), margin_left + plot_w, margin_top + plot_h], fill=RGB_ZONE_DANGER_RED)

    # Lưới mờ (Subtle Grid lines) ngang theo Y & số đo Y
    n_y_ticks = 5
    for yi in range(n_y_ticks + 1):
        v_tick = low + (high - low) * (yi / n_y_ticks)
        y_pos = y_of(v_tick)
        for gx in range(margin_left, margin_left + plot_w, 8 * scale):
            draw.line([(gx, y_pos), (min(gx + 4 * scale, margin_left + plot_w), y_pos)], fill=RGB_GRID_GRAY, width=max(1, scale // 2))
        tick_txt = f"{v_tick:.2f}"
        draw.text((margin_left - 65 * scale, y_pos - 7 * scale), tick_txt, fill=RGB_TEXT_LABEL, font=_font(scale, nho=True))

    # Lưới mờ dọc & Nhãn trục X
    total = len(chart.values)
    x_tick_count = min(7, total)
    if total > 0:
        step_x = max(1, (total - 1) // max(1, x_tick_count - 1)) if x_tick_count > 1 else 1
        x_indices_tick = list(range(0, total, step_x))
        if (total - 1) not in x_indices_tick:
            x_indices_tick.append(total - 1)
        sampled_x_labels = _format_smart_x_ticks(chart.nhan_thoi_gian, x_indices_tick)
        for xi, t_lbl in zip(x_indices_tick, sampled_x_labels):
            x_pos = x_of(xi, total)
            for gy in range(margin_top, margin_top + plot_h, 8 * scale):
                draw.line([(x_pos, gy), (x_pos, min(gy + 4 * scale, margin_top + plot_h))], fill=RGB_GRID_GRAY, width=max(1, scale // 2))
            bbox = draw.textbbox((0, 0), t_lbl, font=_font(scale, nho=True))
            tw = bbox[2] - bbox[0]
            draw.text((x_pos - tw // 2, margin_top + plot_h + 8 * scale), t_lbl, fill=RGB_TEXT_LABEL, font=_font(scale, nho=True))

    # Control/specification limits.
    for value, color, name in (
        (chart.usl, RGB_LIMIT_RED, "USL"),
        (chart.ucl, RGB_WARN_ORANGE, "UCL"),
        (chart.cl, RGB_CENTER_GREEN, "CL"),
        (chart.lcl, RGB_WARN_ORANGE, "LCL"),
        (chart.lsl, RGB_LIMIT_RED, "LSL"),
    ):
        if value is None:
            continue
        y = y_of(value)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=color, width=max(1, int(1.5 * scale)))
        draw.text((margin_left + plot_w + 4 * scale, y - 7 * scale), f"{name}={value:.2f}", fill=color, font=_font(scale, nho=True))

    # Actual measurements line & points.
    points = [(x_of(i, total), y_of(v)) for i, v in enumerate(chart.values)]
    for i in range(1, len(points)):
        draw.line([points[i - 1], points[i]], fill=RGB_PRIMARY_BLUE, width=max(2, int(2.2 * scale)))

    anomaly_indices: List[int] = []
    for idx, ((x, y), v) in enumerate(zip(points, chart.values)):
        is_anomaly = (
            (chart.usl is not None and v > chart.usl)
            or (chart.lsl is not None and v < chart.lsl)
            or (chart.ucl is not None and v > chart.ucl)
            or (chart.lcl is not None and v < chart.lcl)
        )
        if is_anomaly:
            anomaly_indices.append(idx)
            draw.ellipse([x - 7 * scale, y - 7 * scale, x + 7 * scale, y + 7 * scale], outline=RGB_ANOMALY_RED, width=max(2, 2 * scale), fill=RGB_ZONE_DANGER_RED)
        else:
            draw.ellipse([x - 4 * scale, y - 4 * scale, x + 4 * scale, y + 4 * scale], fill=RGB_PRIMARY_BLUE)

    anomaly_count = len(anomaly_indices)

    # Gom nhóm điểm NG liên tiếp để không bị đè nhãn thành vệt
    clusters: List[List[int]] = []
    if anomaly_indices:
        curr = [anomaly_indices[0]]
        for a_idx in anomaly_indices[1:]:
            if a_idx == curr[-1] + 1:
                curr.append(a_idx)
            else:
                clusters.append(curr)
                curr = [a_idx]
        clusters.append(curr)

    for c in clusters:
        if len(c) == 1:
            pt_idx = c[0]
            x, y = points[pt_idx]
            lbl = "trôi dốc / NG"
            bbox = draw.textbbox((0, 0), lbl, font=_font(scale, nho=True))
            tw = bbox[2] - bbox[0]
            if x + 8 * scale + tw > margin_left + plot_w:
                draw.text((x - tw - 8 * scale, y - 10 * scale), lbl, fill=RGB_ANOMALY_RED, font=_font(scale, nho=True))
            else:
                draw.text((x + 8 * scale, y - 10 * scale), lbl, fill=RGB_ANOMALY_RED, font=_font(scale, nho=True))
        else:
            # Nhóm nhiều điểm NG liên tiếp: gom thành một nhãn duy nhất có leader line
            c_xs = [points[i][0] for i in c]
            c_ys = [points[i][1] for i in c]
            mid_x = (min(c_xs) + max(c_xs)) // 2
            top_y = min(c_ys)
            lbl = f"{len(c)} điểm NG liên tiếp (trôi dốc)"
            lbl_font = _font(scale, nho=True)
            bbox = draw.textbbox((0, 0), lbl, font=lbl_font)
            bw = bbox[2] - bbox[0] + 12 * scale
            bh = bbox[3] - bbox[1] + 8 * scale
            badge_x0 = max(margin_left + 4 * scale, min(mid_x - bw // 2, margin_left + plot_w - bw - 4 * scale))
            badge_y0 = max(margin_top + 4 * scale, top_y - 28 * scale)
            # Đường dẫn leader line
            draw.line([(mid_x, badge_y0 + bh), (mid_x, top_y - 8 * scale)], fill=RGB_ANOMALY_RED, width=max(1, scale))
            # Khung badge nổi bật
            draw.rectangle([badge_x0, badge_y0, badge_x0 + bw, badge_y0 + bh], fill=(255, 235, 238), outline=RGB_ANOMALY_RED, width=max(1, scale))
            draw.text((badge_x0 + 6 * scale, badge_y0 + 3 * scale), lbl, fill=RGB_ANOMALY_RED, font=lbl_font)

    # Duong trung binh dong SMA(20)
    try:
        from aios_habit.production_prediction.trend_alerts import sma as _sma20
        _sma_vals = _sma20([float(v) for v in chart.values], 20)
    except Exception:
        _sma_vals = []
    _sma_points = [
        (x_of(i, total), y_of(v))
        for i, v in enumerate(_sma_vals)
        if v is not None
    ]
    for a, b in zip(_sma_points, _sma_points[1:]):
        _ax, _ay = a
        _bx, _by = b
        _dx, _dy = _bx - _ax, _by - _ay
        _seg = max(1, int((_dx ** 2 + _dy ** 2) ** 0.5 // (8 * scale)))
        for _s in range(_seg):
            if _s % 2 == 0:
                _t0, _t1 = _s / _seg, (_s + 1) / _seg
                draw.line(
                    [(_ax + _dx * _t0, _ay + _dy * _t0), (_ax + _dx * _t1, _ay + _dy * _t1)],
                    fill=RGB_SMA_PURPLE,
                    width=max(2, int(2.0 * scale)),
                )
    # Tránh vẽ chữ "SMA(20)" trôi nổi ở đuôi vì sẽ đè lên nhãn CL=-xxx trên trục phải;
    # SMA(20) đã có chú giải chuẩn mực và mẫu đường đứt nét tím trong hộp Legend góc trên.

    # Dashed orange forecast trend if any
    if chart.du_bao:
        start = points[-1] if points else (margin_left, margin_top + plot_h // 2)
        forecast_points = [start]
        for j, v in enumerate(chart.du_bao, start=1):
            forecast_points.append((x_of(total - 1 + j, total + len(chart.du_bao)), y_of(v)))
        for a, b in zip(forecast_points, forecast_points[1:]):
            draw.line([a, b], fill=RGB_ACCENT_ORANGE, width=max(2, scale))

    # Frame viền
    draw.rectangle([margin_left, margin_top, margin_left + plot_w, margin_top + plot_h], outline=RGB_BORDER_GRAY, width=max(1, scale))

    # Tiêu đề đầy đủ chuẩn Production: Thiết bị/JIG + Thông số + Đơn vị + Khoảng thời gian (chống cắt mép 100%)
    unit_str = chart.unit or detect_unit_from_metric(chart.metric)
    time_range = format_time_range_from_sequence(chart.nhan_thoi_gian)
    _ve_tieu_de_pillow(
        draw,
        chart_kind="Biểu đồ kiểm soát SPC",
        metric=chart.metric,
        jig_id=chart.jig_id,
        time_range=time_range,
        unit=unit_str,
        margin_left=margin_left,
        plot_w=plot_w,
        scale=scale,
    )

    # Nhãn trục Y kèm đơn vị
    y_unit_label = format_axis_label(chart.metric, unit=unit_str, axis_role="y")
    draw.text((margin_left, margin_top - 22 * scale), y_unit_label, fill=RGB_TEXT_LABEL, font=_font(scale))

    # Nhãn trục X tự động suy luận khớp đúng kiểu tick
    x_title = _detect_x_axis_label(chart.nhan_thoi_gian)
    bbox_xt = draw.textbbox((0, 0), x_title, font=_font(scale))
    tw_xt = bbox_xt[2] - bbox_xt[0]
    draw.text((margin_left + (plot_w - tw_xt) // 2, margin_top + plot_h + 26 * scale), x_title, fill=RGB_TEXT_LABEL, font=_font(scale))

    # Hộp chú giải (Legend) góc trên trong plot
    leg_x = margin_left + plot_w - 220 * scale
    leg_y = margin_top + 10 * scale
    draw.rectangle([leg_x, leg_y, leg_x + 210 * scale, leg_y + 44 * scale], fill=(255, 255, 255), outline=RGB_BORDER_GRAY)
    draw.line([(leg_x + 8 * scale, leg_y + 12 * scale), (leg_x + 32 * scale, leg_y + 12 * scale)], fill=RGB_PRIMARY_BLUE, width=max(2, scale))
    draw.text((leg_x + 38 * scale, leg_y + 6 * scale), f"Số đo ({unit_str or 'đv'})", fill=RGB_TEXT_LABEL, font=_font(scale, nho=True))
    draw.line([(leg_x + 8 * scale, leg_y + 28 * scale), (leg_x + 32 * scale, leg_y + 28 * scale)], fill=RGB_SMA_PURPLE, width=max(2, scale))
    draw.text((leg_x + 38 * scale, leg_y + 22 * scale), "SMA(20)", fill=RGB_SMA_PURPLE, font=_font(scale, nho=True))
    if anomaly_count > 0:
        draw.ellipse([leg_x + 120 * scale, leg_y + 22 * scale, leg_x + 130 * scale, leg_y + 32 * scale], outline=RGB_ANOMALY_RED, fill=RGB_ZONE_DANGER_RED)
        draw.text((leg_x + 135 * scale, leg_y + 20 * scale), f"NG ({anomaly_count})", fill=RGB_ANOMALY_RED, font=_font(scale, nho=True))

    _ve_bang_mo_phong(draw, chart, width, margin_left, plot_w, scale)

    # Management stamp box (tem quản lý) chống cắt chữ
    stamp_top = margin_top + plot_h + 46 * scale
    _ve_tem_quan_ly(draw, chart, margin_left, plot_w, stamp_top, scale)
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
    try:
        from aios_habit.production_prediction.trend_alerts import sma as _sma20
        _sma_vals = _sma20([float(v) for v in chart.values], 20)
    except Exception:
        _sma_vals = []
    _sma_points = " ".join(
        f"{x_of(i, len(chart.values)):.1f},{y_of(v):.1f}"
        for i, v in enumerate(_sma_vals)
        if v is not None
    )
    _sma_polyline = (
        f'<polyline points="{_sma_points}" fill="none" stroke="#7b1fa2" '
        f'stroke-width="2" stroke-dasharray="10,6" />'
        f'<text x="934" y="60" fill="#7b1fa2">SMA(20)</text>'
        if _sma_points
        else ""
    )
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
        + _sma_polyline +
        f'<text x="90" y="30">Biểu đồ xu hướng {escape(chart.metric)} — {escape(chart.jig_id)}</text>'
        + _svg_mo_phong(chart)
        + f'<text x="90" y="520">{stamp}</text>'
        f"</svg>"
    )


MAU_SERIES = (
    (33, 33, 33),
    (197, 17, 98),
    (0, 151, 167),
    (194, 154, 0),
)

TEN_LOAI_BIEU_DO = {
    "xu_huong": "Xu hướng theo thời gian",
    "phan_bo": "Phân bố giá trị",
    "so_sanh_mau": "So sánh theo màu",
}


def _tem_chung(chart: SpcChartInput) -> str:
    sigma_txt = f"{chart.sigma:.2f}" if chart.sigma is not None else "—"
    return (
        f"JIG: {chart.jig_id} | Công đoạn: {chart.cong_doan or '—'} | "
        f"Ngày giờ: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Người phụ trách: {chart.nguoi_phu_trach or '—'} | "
        f"Cpk: {chart.cpk if chart.cpk is not None else '—'} | "
        f"σ: {sigma_txt}"
    )


def render_phan_bo_png(chart: SpcChartInput, path: str | Path, scale: int = 2, bins: int = 12) -> Path:
    """Render a value-distribution (histogram) chart with limit markers."""
    if Image is None or ImageDraw is None:
        raise RuntimeError("Thiếu thư viện ảnh Pillow để vẽ biểu đồ.")
    if not chart.values:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1000 * scale, 560 * scale
    margin_left, margin_top = 110 * scale, 75 * scale
    margin_right, margin_bottom = 85 * scale, 80 * scale
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    low, high = _bounds(chart)
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    bins = max(4, min(24, int(bins)))
    counts = [0] * bins
    for v in chart.values:
        ratio = (v - low) / (high - low) if high != low else 0.5
        idx = min(bins - 1, max(0, int(ratio * bins)))
        counts[idx] += 1
    peak = max(counts) or 1

    # Subtle grid lines
    for i_g in range(5):
        gy = margin_top + int(plot_h * i_g / 4)
        for gx in range(margin_left, margin_left + plot_w, 8 * scale):
            draw.line([(gx, gy), (min(gx + 4 * scale, margin_left + plot_w), gy)], fill=RGB_GRID_GRAY, width=max(1, scale // 2))

    bar_w = plot_w / bins
    for i, count in enumerate(counts):
        x0 = margin_left + i * bar_w + 2 * scale
        x1 = margin_left + (i + 1) * bar_w - 2 * scale
        h = (count / peak) * plot_h
        y0 = margin_top + plot_h - h
        y1 = margin_top + plot_h
        draw.rectangle([x0, y0, x1, y1], fill=RGB_PRIMARY_BLUE, outline=RGB_BORDER_GRAY)
        if count > 0:
            draw.text((x0 + (x1 - x0) // 2 - 6 * scale, y0 - 14 * scale), str(count), fill=RGB_TEXT_LABEL, font=_font(scale, nho=True))

    for value, color, name in (
        (chart.usl, RGB_LIMIT_RED, "USL"),
        (chart.ucl, RGB_WARN_ORANGE, "UCL"),
        (chart.cl, RGB_CENTER_GREEN, "CL"),
        (chart.lcl, RGB_WARN_ORANGE, "LCL"),
        (chart.lsl, RGB_LIMIT_RED, "LSL"),
    ):
        if value is None:
            continue
        ratio = (value - low) / (high - low) if high != low else 0.5
        x = margin_left + ratio * plot_w
        draw.line([(x, margin_top), (x, margin_top + plot_h)], fill=color, width=max(1, int(1.5 * scale)))
        draw.text((x + 4 * scale, margin_top + 2 * scale), f"{name}={value:.2f}", fill=color, font=_font(scale, nho=True))

    draw.rectangle([margin_left, margin_top, margin_left + plot_w, margin_top + plot_h], outline=RGB_BORDER_GRAY, width=max(1, scale))
    unit_str = chart.unit or detect_unit_from_metric(chart.metric)
    time_range = format_time_range_from_sequence(chart.nhan_thoi_gian)
    _ve_tieu_de_pillow(
        draw,
        chart_kind="Phân bố giá trị (Histogram)",
        metric=chart.metric,
        jig_id=chart.jig_id,
        time_range=time_range,
        unit=unit_str,
        margin_left=margin_left,
        plot_w=plot_w,
        scale=scale,
    )

    draw.text((margin_left, margin_top - 22 * scale), "Tần suất xuất hiện (lần)", fill=RGB_TEXT_LABEL, font=_font(scale))
    draw.text((margin_left + plot_w // 2 - 60 * scale, margin_top + plot_h + 10 * scale), format_axis_label(chart.metric, unit=unit_str, axis_role="x"), fill=RGB_TEXT_LABEL, font=_font(scale))

    _ve_bang_mo_phong(draw, chart, width, margin_left, plot_w, scale)
    stamp_top = margin_top + plot_h + 38 * scale
    _ve_tem_quan_ly(draw, chart, margin_left, plot_w, stamp_top, scale)
    image.save(out, format="PNG", dpi=(300, 300))
    return out

def render_phan_bo_svg(chart: SpcChartInput, bins: int = 12) -> str:
    """Render a compact vector SVG version of the distribution chart."""
    if not chart.values:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    width, height = 960, 540
    low, high = _bounds(chart)
    bins = max(4, min(24, int(bins)))
    counts = [0] * bins
    for v in chart.values:
        ratio = (v - low) / (high - low) if high != low else 0.5
        idx = min(bins - 1, max(0, int(ratio * bins)))
        counts[idx] += 1
    peak = max(counts) or 1
    bars = []
    for i, count in enumerate(counts):
        x = 90 + i * 840 / bins
        h = (count / peak) * 410
        bars.append(f'<rect x="{x:.1f}" y="{480 - h:.1f}" width="{840 / bins - 4:.1f}" height="{h:.1f}" fill="#1565c0" />')
    lines = []
    for value, name in ((chart.usl, "USL"), (chart.ucl, "UCL"), (chart.cl, "CL"), (chart.lcl, "LCL"), (chart.lsl, "LSL")):
        if value is None:
            continue
        ratio = (value - low) / (high - low) if high != low else 0.5
        x = 90 + ratio * 840
        lines.append(f'<line x1="{x:.1f}" y1="70" x2="{x:.1f}" y2="480" stroke="red" />'
                     f'<text x="{x + 4:.1f}" y="80">{name}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" />'
        + "".join(bars) + "".join(lines) +
        f'<text x="90" y="30">Phân bố {escape(chart.metric)} — {escape(chart.jig_id)}</text>'
        + _svg_mo_phong(chart)
        + f'<text x="90" y="520">{escape(_tem_chung(chart))}</text>'
        f"</svg>"
    )


def _bounds_nhieu_chuoi(charts: Sequence[SpcChartInput]) -> tuple[float, float]:
    candidates: List[float] = []
    for chart in charts:
        candidates += list(chart.values) + list(chart.du_bao)
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


def render_so_sanh_png(charts: Sequence[SpcChartInput], path: str | Path, scale: int = 2) -> Path:
    """Render a multi-series color-comparison trend chart."""
    danh_sach = list(charts)
    if Image is None or ImageDraw is None:
        raise RuntimeError("Thiếu thư viện ảnh Pillow để vẽ biểu đồ.")
    if not danh_sach or not any(c.values for c in danh_sach):
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1000 * scale, 560 * scale
    margin_left, margin_top = 110 * scale, 75 * scale
    margin_right, margin_bottom = 85 * scale, 80 * scale
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    low, high = _bounds_nhieu_chuoi(danh_sach)
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    def y_of(value: float) -> int:
        ratio = (value - low) / (high - low) if high != low else 0.5
        return int(margin_top + (1 - ratio) * plot_h)

    # Subtle grid lines
    for i_g in range(5):
        gy = margin_top + int(plot_h * i_g / 4)
        for gx in range(margin_left, margin_left + plot_w, 8 * scale):
            draw.line([(gx, gy), (min(gx + 4 * scale, margin_left + plot_w), gy)], fill=RGB_GRID_GRAY, width=max(1, scale // 2))

    goc = danh_sach[0]
    for value, color, name in (
        (goc.usl, RGB_LIMIT_RED, "USL"),
        (goc.ucl, RGB_WARN_ORANGE, "UCL"),
        (goc.cl, RGB_CENTER_GREEN, "CL"),
        (goc.lcl, RGB_WARN_ORANGE, "LCL"),
        (goc.lsl, RGB_LIMIT_RED, "LSL"),
    ):
        if value is None:
            continue
        y = y_of(value)
        draw.line([(margin_left, y), (margin_left + plot_w, y)], fill=color, width=max(1, int(1.5 * scale)))
        draw.text((margin_left + plot_w + 4 * scale, y - 6 * scale), f"{name}={value:.2f}", fill=color, font=_font(scale, nho=True))

    for idx, chart in enumerate(danh_sach):
        if not chart.values:
            continue
        mau = RGB_PALETTE_DISTINCT[idx % len(RGB_PALETTE_DISTINCT)]
        total = len(chart.values)

        def x_of(i: int) -> int:
            if total <= 1:
                return margin_left + plot_w // 2
            return int(margin_left + i / (total - 1) * plot_w)

        points = [(x_of(i), y_of(v)) for i, v in enumerate(chart.values)]
        for a, b in zip(points, points[1:]):
            draw.line([a, b], fill=mau, width=max(2, int(2.2 * scale)))
        nhan = (chart.metric or chart.jig_id)
        upper_nhan = nhan.upper()
        for ma_mau, ten_mau in (("BLACK", "Đen"), ("MAGENTA", "Hồng"),
                                ("CYAN", "Xanh"), ("YELLOW", "Vàng")):
            if ma_mau in upper_nhan:
                nhan = ten_mau
                break
        nhan = nhan[:28]
        hang_chu_thich = margin_top + 10 * scale + (idx * 22 * scale)
        leg_box_x = margin_left + 15 * scale
        draw.rectangle([leg_box_x, hang_chu_thich, leg_box_x + 18 * scale, hang_chu_thich + 12 * scale], fill=mau)
        draw.text((leg_box_x + 24 * scale, hang_chu_thich - 2 * scale), nhan, fill=RGB_TEXT_LABEL, font=_font(scale))

    draw.rectangle([margin_left, margin_top, margin_left + plot_w, margin_top + plot_h], outline=RGB_BORDER_GRAY, width=max(1, scale))
    unit_str = goc.unit or detect_unit_from_metric(goc.metric)
    _ve_tieu_de_pillow(
        draw,
        chart_kind="So sánh theo màu",
        metric=goc.metric or "Chỉ số",
        jig_id=goc.jig_id,
        unit=unit_str,
        margin_left=margin_left,
        plot_w=plot_w,
        scale=scale,
    )
    draw.text((margin_left, margin_top - 22 * scale), format_axis_label("Giá trị đo", unit=unit_str, axis_role="y"), fill=RGB_TEXT_LABEL, font=_font(scale))

    _ve_bang_mo_phong(draw, goc, width, margin_left, plot_w, scale,
                      ep_buoc=_co_chuoi_mo_phong(danh_sach))
    stamp_top = margin_top + plot_h + 38 * scale
    _ve_tem_quan_ly(draw, goc, margin_left, plot_w, stamp_top, scale)
    image.save(out, format="PNG", dpi=(300, 300))
    return out

def render_so_sanh_svg(charts: Sequence[SpcChartInput]) -> str:
    """Render a compact vector SVG version of the color-comparison chart."""
    danh_sach = [c for c in charts if c.values]
    if not danh_sach:
        raise ValueError("Thiếu chuỗi giá trị đo để vẽ biểu đồ.")
    width, height = 960, 540
    low, high = _bounds_nhieu_chuoi(danh_sach)

    def y_of(value: float) -> float:
        ratio = (value - low) / (high - low) if high != low else 0.5
        return 70 + (1 - ratio) * 410

    mau_hex = ("#212121", "#c51162", "#0097a7", "#c29a00")
    duong = []
    for idx, chart in enumerate(danh_sach):
        total = len(chart.values)
        pts = []
        for i, v in enumerate(chart.values):
            x = 90 + 420 if total <= 1 else 90 + i / (total - 1) * 840
            pts.append(f"{x:.1f},{y_of(v):.1f}")
        duong.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{mau_hex[idx % len(mau_hex)]}" stroke-width="2" />')
    goc = danh_sach[0]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" />'
        + "".join(duong) +
        f'<text x="90" y="30">So sánh theo màu — {escape(goc.jig_id)}</text>'
        + _svg_mo_phong(goc, ep_buoc=_co_chuoi_mo_phong(danh_sach))
        + f'<text x="90" y="520">{escape(_tem_chung(goc))}</text>'
        f"</svg>"
    )


def render_chart_png(
    du_lieu: Union[SpcChartInput, Sequence[SpcChartInput]],
    loai_bieu_do: str,
    path: str | Path,
    scale: int = 2,
) -> Path:
    """Dispatch to the requested chart kind so UI and email share one entry."""
    if loai_bieu_do == "phan_bo":
        if isinstance(du_lieu, (list, tuple)):
            raise ValueError("Biểu đồ phân bố chỉ vẽ một chỉ số mỗi lần. Vui lòng chọn một chỉ số.")
        assert isinstance(du_lieu, SpcChartInput)
        return render_phan_bo_png(du_lieu, path, scale=scale)
    if loai_bieu_do == "so_sanh_mau":
        danh_sach = list(du_lieu) if isinstance(du_lieu, (list, tuple)) else [du_lieu]
        return render_so_sanh_png(danh_sach, path, scale=scale)
    if isinstance(du_lieu, (list, tuple)):
        raise ValueError("Biểu đồ xu hướng chỉ vẽ một chỉ số mỗi lần. Vui lòng chọn một chỉ số.")
    assert isinstance(du_lieu, SpcChartInput)
    return render_spc_png(du_lieu, path, scale=scale)


def render_chart_svg(
    du_lieu: Union[SpcChartInput, Sequence[SpcChartInput]],
    loai_bieu_do: str,
) -> str:
    """Dispatch to the requested SVG chart kind."""
    if loai_bieu_do == "phan_bo":
        if isinstance(du_lieu, (list, tuple)):
            raise ValueError("Biểu đồ phân bố chỉ vẽ một chỉ số mỗi lần. Vui lòng chọn một chỉ số.")
        assert isinstance(du_lieu, SpcChartInput)
        return render_phan_bo_svg(du_lieu)
    if loai_bieu_do == "so_sanh_mau":
        danh_sach = list(du_lieu) if isinstance(du_lieu, (list, tuple)) else [du_lieu]
        return render_so_sanh_svg(danh_sach)
    if isinstance(du_lieu, (list, tuple)):
        raise ValueError("Biểu đồ xu hướng chỉ vẽ một chỉ số mỗi lần. Vui lòng chọn một chỉ số.")
    assert isinstance(du_lieu, SpcChartInput)
    return render_spc_svg(du_lieu)
