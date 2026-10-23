# -*- coding: utf-8 -*-
"""Mô-đun theme biểu đồ dùng chung (Single Source of Truth) cho toàn bộ hệ thống AIOS.

Áp dụng đồng bộ cho cả hai luồng:
1. `log_chart`: Biểu đồ từ log người dùng nạp qua khung chat (Matplotlib Agg).
2. `production_prediction`: Biểu đồ từ log sản xuất / JIG (Pillow SPC, SVG, Periodic Trend Report).

Nguyên tắc thiết kế UX/UI Production (Monozukuri High-End):
- Bảng màu hiện đại, tương phản cao, chuyên nghiệp chuẩn công nghiệp.
- Lưới mờ (subtle grid, alpha 0.5-0.6), nền trắng sạch sẽ.
- Font tiếng Việt có dấu chuẩn xác (Segoe UI, Arial, Tahoma, DejaVu Sans), chống tofu và vỡ dấu 100%.
- Cỡ chữ, Figure size và DPI chuẩn hóa để đọc rõ ràng cả trong giao diện app lẫn ảnh cẩm nang/báo cáo.
- Đầy đủ tiêu đề (Thiết bị/JIG + Thông số + Khoảng thời gian), nhãn trục kèm đơn vị, chú giải (legend),
  đường SMA(20), đường giới hạn và điểm bất thường/NG nổi bật.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# =============================================================================
# 1. BẢNG MÀU CHUẨN MONOZUKURI PRODUCTION
# =============================================================================

# Màu nền & Khung viền
COLOR_BG_WHITE = "#ffffff"
COLOR_BG_CARD = "#f8f9fa"
COLOR_GRID_GRAY = "#e2e8f0"      # Lưới mờ tinh tế
COLOR_BORDER_GRAY = "#cbd5e1"    # Viền trục nhẹ
COLOR_TEXT_TITLE = "#0f172a"     # Chữ tiêu đề đậm nét (Slate 900)
COLOR_TEXT_LABEL = "#1e293b"     # Chữ nhãn trục (Slate 800)
COLOR_TEXT_MUTED = "#64748b"     # Chữ chú thích phụ/footer (Slate 500)

# Màu đường đo lường & Dòng dữ liệu
COLOR_PRIMARY_BLUE = "#1565c0"   # Đường dữ liệu đo chính (Cobalt Blue)
COLOR_ACCENT_ORANGE = "#e65100"  # Đường phụ / Hồi quy / Dự báo (Deep Orange)
COLOR_SMA_PURPLE = "#7b1fa2"     # Đường trung bình động SMA(20) (Deep Purple)

# Màu kiểm soát chất lượng & Cảnh báo SPC
COLOR_LIMIT_RED = "#c62828"      # Giới hạn tới hạn USL / LSL (Red 800)
COLOR_WARN_ORANGE = "#ef6c00"    # Giới hạn kiểm soát UCL / LCL (Orange 800)
COLOR_CENTER_GREEN = "#2e7d32"   # Đường trung tâm CL / Mục tiêu (Green 800)
COLOR_ANOMALY_RED = "#d50000"    # Điểm bất thường / NG (Crimson Accent)

# Dải màu phân vùng SPC Zone A/B/C
COLOR_ZONE_SAFE_GREEN = "#e8f5e9"   # Vùng C - An toàn
COLOR_ZONE_WARN_YELLOW = "#fffde7"  # Vùng B - Cần chú ý
COLOR_ZONE_DANGER_RED = "#ffebee"   # Vùng A - Nguy cơ

# Bảng màu phân biệt chuỗi (10 màu phân biệt cao)
PALETTE_DISTINCT = [
    "#1565c0",  # Xanh dương đậm
    "#2e7d32",  # Xanh lá cây
    "#e65100",  # Cam đậm
    "#7b1fa2",  # Tím đậm
    "#00838f",  # Xanh mòng két
    "#c2185b",  # Hồng sẫm
    "#ef6c00",  # Cam hổ phách
    "#455a64",  # Xám xanh công nghiệp
    "#0288d1",  # Xanh da trời sáng
    "#689f38",  # Xanh lục ô liu
]

# Phiên bản màu RGB Tuple cho Pillow
RGB_PRIMARY_BLUE = (21, 101, 192)
RGB_ACCENT_ORANGE = (230, 81, 0)
RGB_SMA_PURPLE = (123, 31, 162)
RGB_LIMIT_RED = (198, 40, 40)
RGB_WARN_ORANGE = (239, 108, 0)
RGB_CENTER_GREEN = (46, 125, 50)
RGB_ANOMALY_RED = (213, 0, 0)
RGB_GRID_GRAY = (226, 232, 240)
RGB_BORDER_GRAY = (203, 213, 225)
RGB_TEXT_TITLE = (15, 23, 42)
RGB_TEXT_LABEL = (30, 41, 59)
RGB_TEXT_MUTED = (100, 116, 139)

RGB_ZONE_SAFE_GREEN = (232, 245, 233)
RGB_ZONE_WARN_YELLOW = (255, 253, 231)
RGB_ZONE_DANGER_RED = (255, 235, 238)

RGB_PALETTE_DISTINCT = [
    (21, 101, 192),
    (46, 125, 50),
    (230, 81, 0),
    (123, 31, 162),
    (0, 131, 143),
    (194, 24, 91),
    (239, 108, 0),
    (69, 90, 100),
    (2, 136, 209),
    (104, 159, 56),
]


# =============================================================================
# 2. CẤU HÌNH KÍCH THƯỚC & DPI CHUẨN
# =============================================================================

# Biểu đồ đầy đủ (Full-res)
DEFAULT_FIG_WIDTH_INCHES: float = 10.0
DEFAULT_FIG_HEIGHT_INCHES: float = 5.6
DEFAULT_DPI: int = 150
HIGH_RES_DPI: int = 200

# Kích thước Pillow Pixel chuẩn
PILLOW_STD_WIDTH: int = 1000
PILLOW_STD_HEIGHT: int = 560

# Ảnh thu nhỏ (Thumbnail)
THUMBNAIL_WIDTH_INCHES: float = 3.2
THUMBNAIL_HEIGHT_INCHES: float = 2.0
THUMBNAIL_DPI: int = 90


# =============================================================================
# 3. HỆ THỐNG FONT TIẾNG VIỆT CHỐNG TOFU & VỠ DẤU
# =============================================================================

_PILLOW_FONT_CACHE: Dict[Tuple[int, bool], Any] = {}


def configure_matplotlib_fonts() -> None:
    """Cấu hình Matplotlib sử dụng danh sách font ưu tiên tiếng Việt."""
    try:
        import matplotlib
        import matplotlib.pyplot as plt

        # Danh sách font có độ phủ tiếng Việt hoàn hảo trên Windows/Linux/macOS
        vietnamese_fonts = [
            "Segoe UI",
            "Arial",
            "Tahoma",
            "Calibri",
            "DejaVu Sans",
            "Liberation Sans",
            "sans-serif",
        ]
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = vietnamese_fonts
        matplotlib.rcParams["axes.unicode_minus"] = False  # Tránh lỗi dấu âm (-)
        matplotlib.rcParams["figure.titlesize"] = 12
        matplotlib.rcParams["axes.titlesize"] = 12
        matplotlib.rcParams["axes.labelsize"] = 10
        matplotlib.rcParams["xtick.labelsize"] = 9
        matplotlib.rcParams["ytick.labelsize"] = 9
        matplotlib.rcParams["legend.fontsize"] = 9
    except Exception:
        pass


def get_pillow_font(size: int = 14, bold: bool = False) -> Any:
    """Tải font TrueType tiếng Việt cho Pillow với bộ đệm (cache)."""
    key = (size, bold)
    if key in _PILLOW_FONT_CACHE:
        return _PILLOW_FONT_CACHE[key]

    try:
        from PIL import ImageFont
    except ImportError:
        return None

    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    fonts_dir = os.path.join(system_root, "Fonts")

    candidates: List[str] = []
    if bold:
        candidates.extend([
            os.path.join(fonts_dir, "segoeuib.ttf"),
            os.path.join(fonts_dir, "arialbd.ttf"),
            os.path.join(fonts_dir, "tahomabd.ttf"),
            os.path.join(fonts_dir, "calibrib.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ])
    candidates.extend([
        os.path.join(fonts_dir, "segoeui.ttf"),
        os.path.join(fonts_dir, "arial.ttf"),
        os.path.join(fonts_dir, "tahoma.ttf"),
        os.path.join(fonts_dir, "calibri.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ])

    loaded_font = None
    for path in candidates:
        if os.path.exists(path):
            try:
                loaded_font = ImageFont.truetype(path, size=size)
                break
            except Exception:
                continue

    if loaded_font is None:
        try:
            loaded_font = ImageFont.load_default()
        except Exception:
            loaded_font = None

    _PILLOW_FONT_CACHE[key] = loaded_font
    return loaded_font


# =============================================================================
# 4. TRÍCH XUẤT ĐƠN VỊ & NHÃN THÔNG SỐ TỰ ĐỘNG
# =============================================================================

KNOWN_METRIC_UNITS: Dict[str, str] = {
    "BOW": "µm",
    "SKEW": "µm",
    "BOW_VALUE": "µm",
    "SKEW_VALUE": "µm",
    "BOW_B": "µm",
    "BOW_Y": "µm",
    "BOW_M": "µm",
    "BOW_C": "µm",
    "SKEW_B": "µm",
    "SKEW_Y": "µm",
    "SKEW_M": "µm",
    "SKEW_C": "µm",
    "DEPTH": "mm",
    "TAKT": "sec",
    "TAKTTIME": "sec",
    "CYCLETIME": "sec",
    "TOTALTACT": "sec",
    "HUMIDITY": "%",
    "TEMPERATURE": "℃",
    "TEMP": "℃",
    "BEAMDIAMETER": "µm",
    "BEAM_POS": "µm",
    "LIGHTPATH": "µm",
    "DPPM": "ppm",
    "VOLTAGE": "V",
    "CURRENT": "mA",
}

FRIENDLY_METRIC_NAMES_VI: Dict[str, str] = {
    "BOW": "Độ lệch chùm tia (BOW)",
    "SKEW": "Độ nghiêng chùm tia (SKEW)",
    "BOW_VALUE": "Độ lệch chùm tia (BOW)",
    "SKEW_VALUE": "Độ nghiêng chùm tia (SKEW)",
    "BOW_B": "Độ lệch chùm tia màu Đen (BOW_B)",
    "BOW_Y": "Độ lệch chùm tia màu Vàng (BOW_Y)",
    "BOW_M": "Độ lệch chùm tia màu Hồng (BOW_M)",
    "BOW_C": "Độ lệch chùm tia màu Xanh (BOW_C)",
    "SKEW_B": "Độ nghiêng chùm tia màu Đen (SKEW_B)",
    "DEPTH": "Độ sâu tiêu cự (Depth)",
    "TAKT": "Thời gian chu kỳ (Takt Time)",
    "TAKTTIME": "Thời gian chu kỳ (Takt Time)",
    "HUMIDITY": "Độ ẩm môi trường (Humidity)",
    "TEMPERATURE": "Nhiệt độ môi trường (Temperature)",
    "TEMP": "Nhiệt độ môi trường (Temp)",
    "BEAMDIAMETER": "Đường kính chùm tia (Beam Diameter)",
    "LIGHTPATH": "Quang trình chùm tia (Light Path)",
}


def detect_unit_from_metric(metric_name: str, fallback_unit: str = "") -> str:
    """Tự động nhận diện đơn vị đo từ tên thông số hoặc mã cột."""
    if fallback_unit:
        return fallback_unit.strip()

    name = str(metric_name or "").strip()
    if not name:
        return ""

    # 1. Tìm đơn vị trong ngoặc vuông hoặc tròn, ví dụ: "takt[sec]", "BOW (µm)"
    bracket_match = re.search(r"[\[\(]([a-zA-Zµ℃%°C\s/]+)[\]\)]", name)
    if bracket_match:
        u = bracket_match.group(1).strip()
        if u:
            return u

    # 2. Tra cứu bảng đơn vị chuẩn Monozukuri
    upper = name.upper()
    for k, unit in KNOWN_METRIC_UNITS.items():
        if k in upper:
            return unit

    return ""


def get_friendly_metric_name(metric_name: str) -> str:
    """Trả về tên thông số tiếng Việt kèm mã kỹ thuật."""
    name = str(metric_name or "").strip()
    if not name:
        return "Thông số đo"

    upper = name.upper()
    if name in FRIENDLY_METRIC_NAMES_VI:
        return FRIENDLY_METRIC_NAMES_VI[name]

    for k, friendly in FRIENDLY_METRIC_NAMES_VI.items():
        if k in upper:
            return friendly

    return name


def format_chart_title(
    *,
    chart_kind: str,
    metric: str,
    jig_id: str = "",
    time_range: str = "",
    unit: str = "",
) -> str:
    """Định dạng tiêu đề biểu đồ hoàn chỉnh chuẩn production:
    [Loại biểu đồ] — [Thông số] (đơn vị) — JIG: [Mã] [Khoảng thời gian]
    """
    friendly_metric = get_friendly_metric_name(metric)
    effective_unit = unit or detect_unit_from_metric(metric)
    unit_part = f" ({effective_unit})" if effective_unit else ""

    parts = [f"{chart_kind}: {friendly_metric}{unit_part}"]

    if jig_id and jig_id != "—" and jig_id != "Chung":
        parts.append(f"JIG: {jig_id}")

    if time_range:
        parts.append(f"[{time_range}]")

    return " — ".join(parts)


def format_axis_label(name: str, unit: str = "", axis_role: str = "") -> str:
    """Tạo nhãn trục chuẩn xác kèm đơn vị."""
    raw_name = str(name or "").strip()
    effective_unit = unit or detect_unit_from_metric(raw_name)
    friendly = get_friendly_metric_name(raw_name)

    if axis_role == "y":
        if effective_unit:
            return f"{friendly} [{effective_unit}]"
        return friendly
    elif axis_role == "x":
        if effective_unit:
            return f"{raw_name} [{effective_unit}]"
        return raw_name

    return f"{raw_name} [{effective_unit}]" if effective_unit else raw_name


def format_time_range_from_sequence(time_seq: Sequence[str]) -> str:
    """Trích xuất khoảng thời gian (từ ~ đến) từ chuỗi thời gian."""
    valid_times = [str(t).strip() for t in time_seq if str(t).strip() and str(t).strip() not in ("—", "None")]
    if not valid_times:
        return ""
    if len(valid_times) == 1:
        return valid_times[0]
    return f"{valid_times[0]} ~ {valid_times[-1]}"


# =============================================================================
# 5. MATPLOTLIB THEME HELPER
# =============================================================================

def apply_matplotlib_theme(
    ax: Any,
    fig: Optional[Any] = None,
    *,
    grid_axis: str = "both",
) -> None:
    """Áp dụng theme Monozukuri production cho trục và khung hình Matplotlib."""
    configure_matplotlib_fonts()

    # Nền trắng tinh khiết
    ax.set_facecolor(COLOR_BG_WHITE)
    if fig is not None:
        fig.patch.set_facecolor(COLOR_BG_WHITE)

    # Lưới mờ tinh tế
    ax.grid(
        True,
        which="major",
        axis=grid_axis,
        linestyle="--",
        linewidth=0.75,
        color=COLOR_GRID_GRAY,
        alpha=0.8,
    )
    ax.set_axisbelow(True)

    # Khung viền (spines) thanh mảnh
    for spine_name in ("top", "right"):
        if spine_name in ax.spines:
            ax.spines[spine_name].set_visible(False)

    for spine_name in ("bottom", "left"):
        if spine_name in ax.spines:
            ax.spines[spine_name].set_color(COLOR_BORDER_GRAY)
            ax.spines[spine_name].set_linewidth(1.0)

    # Ticks & Labels
    ax.tick_params(colors=COLOR_TEXT_LABEL, width=0.8, length=4)
