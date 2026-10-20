# -*- coding: utf-8 -*-
"""Dac ta bieu do (ChartSpec) va co che sua doi qua chat (Conversational Refinement).

Nhiem vu:
- Luu dac ta bieu do dang du lieu: cot X, cot Y, cot nhom, loai bieu do, bo loc, options (SMA, UCL/LCL).
- Ham update_spec_from_text: nhan dien y dinh nguoi dung ("them duong SMA(20)", "chi xem line 2",
  "chi dong NG", "doi sang pareto", "doi truc X thanh thoi gian") de sua va ve lai bieu do cu.
"""

from __future__ import annotations

import copy
import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.log_chart.parser import (
    ParsedLogTable,
    ROLE_CATEGORICAL,
    ROLE_DATETIME,
    ROLE_NUMERIC,
    ROLE_RESULT,
)

# 10 kieu bieu do san xuat
CHART_PARETO = "pareto"
CHART_TREND = "trend"
CHART_SPC = "spc"
CHART_GROUPED_BAR = "grouped_bar"
CHART_DONUT = "donut"
CHART_HISTOGRAM = "histogram"
CHART_SCATTER = "scatter"
CHART_BOX_PLOT = "box_plot"
CHART_HEATMAP = "heatmap"
CHART_STACKED_BAR = "stacked_bar"

ALL_CHART_TYPES = (
    CHART_PARETO,
    CHART_TREND,
    CHART_SPC,
    CHART_GROUPED_BAR,
    CHART_DONUT,
    CHART_HISTOGRAM,
    CHART_SCATTER,
    CHART_BOX_PLOT,
    CHART_HEATMAP,
    CHART_STACKED_BAR,
)

CHART_TITLES_VI = {
    CHART_PARETO: "1. Biểu đồ Pareto (Cột + Lũy kế %)",
    CHART_TREND: "2. Xu hướng / Run chart (kèm SMA)",
    CHART_SPC: "3. Biểu đồ kiểm soát SPC (UCL / CL / LCL)",
    CHART_GROUPED_BAR: "4. Cột nhóm (So sánh Line / Ca / Máy)",
    CHART_DONUT: "5. Tròn / Donut (Tỷ trọng)",
    CHART_HISTOGRAM: "6. Phân bố Histogram (Giá trị đo)",
    CHART_SCATTER: "7. Phân tán Scatter (Tương quan 2 biến)",
    CHART_BOX_PLOT: "8. Biểu đồ hộp Box Plot (Biến động theo nhóm)",
    CHART_HEATMAP: "9. Bản đồ nhiệt Heatmap (Lỗi theo Giờ x Nhóm)",
    CHART_STACKED_BAR: "10. Cột chồng theo thời gian (Cơ cấu lỗi)",
}


@dataclass
class ChartSpec:
    """Dac ta chi tiet mot bieu do de co the tai tao, luu tru va sua doi."""
    spec_id: str = field(default_factory=lambda: f"SPEC-{uuid.uuid4().hex[:8].upper()}")
    file_id: str = ""
    file_name: str = ""
    chart_type: str = CHART_TREND
    x_col: str = ""
    y_col: str = ""
    group_col: Optional[str] = None
    filter_col: Optional[str] = None
    filter_val: Optional[str] = None
    filter_op: str = "eq"  # "eq", "neq", "contains", "only_ng", "all"
    row_start: int = 0
    row_end: Optional[int] = None
    row_limit: int = 2000
    options: Dict[str, Any] = field(default_factory=lambda: {
        "show_sma": True,
        "sma_window": 20,
        "ucl": None,
        "lcl": None,
        "cl": None,
        "bins": 15,
        "palette": "Monozukuri",
    })
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChartSpec":
        c = dict(data)
        return cls(**c)


def _khong_dau(text: str) -> str:
    """Chuyen chuoi thanh chu thuong va bo dau tieng Viet (bao gom chu d)."""
    text = (text or "").lower().replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.strip()


def _tim_cot_phu_hop(ten_tim_kiem: str, table: ParsedLogTable) -> Optional[str]:
    """Tim cot trong bang khop nhat voi tu khoa nguoi dung nhap."""
    target = _khong_dau(ten_tim_kiem)
    if not target:
        return None

    # Khop chinh xac
    for col in table.columns:
        if _khong_dau(col.name) == target:
            return col.name

    # Khop chuoi con
    for col in table.columns:
        c_norm = _khong_dau(col.name)
        if target in c_norm or c_norm in target:
            return col.name

    return None


def update_spec_from_text(
    current_spec: ChartSpec,
    user_query: str,
    table: ParsedLogTable,
) -> Tuple[ChartSpec, str]:
    """Phan tich cau chat cua nguoi dung va cap nhat ChartSpec."""
    spec = copy.deepcopy(current_spec)
    norm = _khong_dau(user_query)
    changes: List[str] = []

    # 1. Dieu chinh SMA (duong trung binh dong)
    if any(k in norm for k in ("them duong sma", "bat sma", "them sma", "hien thi sma", "kem sma")):
        spec.options["show_sma"] = True
        # Tim cua so SMA neu co chi dinh so (vi du SMA(10), SMA 15)
        m_win = re.search(r"sma\s*\(?\s*(\d+)\s*\)?", norm)
        if m_win:
            w = int(m_win.group(1))
            if 2 <= w <= 200:
                spec.options["sma_window"] = w
        changes.append(f"bật đường trung bình động SMA({spec.options.get('sma_window', 20)})")
    elif any(k in norm for k in ("bo sma", "tat sma", "an sma", "khong dung sma", "xoa sma")):
        spec.options["show_sma"] = False
        changes.append("tắt đường trung bình động SMA")

    # 2. Thay doi loai bieu do
    if any(k in norm for k in ("pareto", "bieu do pareto")):
        spec.chart_type = CHART_PARETO
        # Uu tien cot loi/nhom cho Pareto
        cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL) + table.get_columns_by_role(ROLE_RESULT)
        if cat_cols and spec.x_col not in [c.name for c in cat_cols]:
            spec.x_col = cat_cols[0].name
        changes.append("chuyển sang biểu đồ Pareto (cột lỗi + lũy kế %)")
    elif any(k in norm for k in ("xu huong", "run chart", "bieu do duong", "line chart")):
        spec.chart_type = CHART_TREND
        # Uu tien cot datetime cho X va numeric cho Y
        dt_cols = table.get_columns_by_role(ROLE_DATETIME)
        num_cols = table.get_columns_by_role(ROLE_NUMERIC)
        if dt_cols:
            spec.x_col = dt_cols[0].name
        if num_cols:
            spec.y_col = num_cols[0].name
        changes.append("chuyển sang biểu đồ xu hướng / Run chart")
    elif any(k in norm for k in ("kiem soat", "spc", "control chart", "p-chart", "p chart")):
        spec.chart_type = CHART_SPC
        changes.append("chuyển sang biểu đồ kiểm soát SPC (UCL / CL / LCL)")
    elif any(k in norm for k in ("cot nhom", "grouped bar", "so sanh nhom")):
        spec.chart_type = CHART_GROUPED_BAR
        changes.append("chuyển sang biểu đồ cột nhóm")
    elif any(k in norm for k in ("tron", "donut", "ty trong", "pie chart")):
        spec.chart_type = CHART_DONUT
        changes.append("chuyển sang biểu đồ tròn / Donut (tỷ trọng)")
    elif any(k in norm for k in ("histogram", "phan bo", "tan suat")):
        spec.chart_type = CHART_HISTOGRAM
        changes.append("chuyển sang biểu đồ phân bố Histogram")
    elif any(k in norm for k in ("phan tan", "scatter", "tuong quan")):
        spec.chart_type = CHART_SCATTER
        num_cols = table.get_columns_by_role(ROLE_NUMERIC)
        if len(num_cols) >= 2:
            spec.x_col = num_cols[0].name
            spec.y_col = num_cols[1].name
        changes.append("chuyển sang biểu đồ phân tán Scatter")
    elif any(k in norm for k in ("box plot", "hop", "bien dong theo nhom")):
        spec.chart_type = CHART_BOX_PLOT
        changes.append("chuyển sang biểu đồ hộp Box Plot")
    elif any(k in norm for k in ("heatmap", "ban do nhiet")):
        spec.chart_type = CHART_HEATMAP
        changes.append("chuyển sang bản đồ nhiệt Heatmap")
    elif any(k in norm for k in ("cot chong", "stacked bar", "co cau loi")):
        spec.chart_type = CHART_STACKED_BAR
        changes.append("chuyển sang biểu đồ cột chồng theo thời gian")

    # 3. Loc dong (chi xem dong NG, chi xem line X, xem tat ca)
    if any(k in norm for k in ("chi xem dong ng", "chi dong ng", "loc ng", "chi xem ng", "lay ng")):
        res_cols = table.get_columns_by_role(ROLE_RESULT)
        if res_cols:
            spec.filter_col = res_cols[0].name
            spec.filter_val = "NG"
            spec.filter_op = "only_ng"
            changes.append(f"lọc chỉ các dòng có kết quả NG theo cột \"{res_cols[0].name}\"")
        else:
            # Thu tim cot co chu "result" hoac "status"
            matched = _tim_cot_phu_hop("result", table) or _tim_cot_phu_hop("status", table)
            if matched:
                spec.filter_col = matched
                spec.filter_val = "NG"
                spec.filter_op = "only_ng"
                changes.append(f"lọc chỉ các dòng có kết quả NG theo cột \"{matched}\"")
    elif any(k in norm for k in ("xem tat ca", "tat ca dong", "bo loc", "xoa loc", "huy loc")):
        spec.filter_col = None
        spec.filter_val = None
        spec.filter_op = "all"
        changes.append("xóa bộ lọc, hiển thị toàn bộ dữ liệu")
    else:
        # Kiem tra loc theo gia tri cu the: "chi xem line 2", "loc line 1", "chi xem ca A"
        m_filter = re.search(r"(?:chi xem|loc|xem|chon)\s+([a-zA-Z0-9_\s]+?)\s*(\d+|[a-zA-Z]+)$", norm)
        if m_filter:
            target_kw = m_filter.group(1).strip()
            target_val = m_filter.group(2).strip()
            matched_col = _tim_cot_phu_hop(target_kw, table)
            if matched_col:
                spec.filter_col = matched_col
                spec.filter_val = target_val
                spec.filter_op = "contains"
                changes.append(f"lọc cột \"{matched_col}\" theo giá trị \"{target_val}\"")

    # 4. Doi truc X hoac Y theo ten cot
    m_x = re.search(r"(?:doi truc x thanh|truc x la|truc hoanh la)\s+([a-zA-Z0-9_\[\]\:\-\s]+)", norm)
    if m_x:
        x_target = m_x.group(1).strip()
        matched_x = _tim_cot_phu_hop(x_target, table)
        if matched_x:
            spec.x_col = matched_x
            changes.append(f"đổi trục X thành \"{matched_x}\"")

    m_y = re.search(r"(?:doi truc y thanh|truc y la|gia tri la|doi gia tri thanh)\s+([a-zA-Z0-9_\[\]\:\-\s]+)", norm)
    if m_y:
        y_target = m_y.group(1).strip()
        matched_y = _tim_cot_phu_hop(y_target, table)
        if matched_y:
            spec.y_col = matched_y
            changes.append(f"đổi giá trị đo (trục Y) thành \"{matched_y}\"")

    spec.updated_at = datetime.now(timezone.utc).isoformat()

    if not changes:
        return spec, "Không tìm thấy yêu cầu thay đổi phù hợp trong câu hỏi. Biểu đồ được giữ nguyên cấu hình hiện tại."

    msg = f"Đã cập nhật biểu đồ theo yêu cầu: {', '.join(changes)}."
    return spec, msg
