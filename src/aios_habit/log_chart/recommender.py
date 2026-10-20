# -*- coding: utf-8 -*-
"""Dong co goi y xep hang thong minh cac kieu bieu do san xuat (Smart Recommendation Engine).

Quy tac goi y:
1. Co cot thoi gian (datetime) -> day Xu huong (Run chart) + SPC len dau.
2. Co cot ma loi / ket qua NG (categorical / result) -> day Pareto len dau.
3. Co hai cot so do (numeric x numeric) -> day Scatter (phan tan) va Box plot len dau.
4. Co cot phan nhom (line/ca/may/tram) -> day Cot nhom (grouped bar) va Heatmap len dau.
5. So luong nhom nho (<= 8) -> Donut (ty trong).
6. So do don le -> Histogram (phan bo gia tri).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aios_habit.log_chart.parser import (
    ParsedLogTable,
    ROLE_CATEGORICAL,
    ROLE_DATETIME,
    ROLE_NUMERIC,
    ROLE_RESULT,
)
from aios_habit.log_chart.spec import (
    ALL_CHART_TYPES,
    CHART_BOX_PLOT,
    CHART_DONUT,
    CHART_GROUPED_BAR,
    CHART_HEATMAP,
    CHART_HISTOGRAM,
    CHART_PARETO,
    CHART_SCATTER,
    CHART_SPC,
    CHART_STACKED_BAR,
    CHART_TREND,
    ChartSpec,
)


def recommend_chart_types(
    table: ParsedLogTable,
    selected_x: Optional[str] = None,
    selected_y: Optional[str] = None,
    selected_group: Optional[str] = None,
) -> List[Tuple[str, float, str]]:
    """Xep hang thong minh cac kieu bieu do dua tren kieu cot thuc te cua file.

    Tra ve danh sach Tuple: (ma_kieu_bieu_do, diem_uu_tien, ly_do_tieng_viet).
    Sap xep tu diem cao nhat den thap nhat.
    """
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)
    res_cols = table.get_columns_by_role(ROLE_RESULT)
    cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL)
    num_cols = table.get_columns_by_role(ROLE_NUMERIC)

    scores: Dict[str, float] = {ct: 5.0 for ct in ALL_CHART_TYPES}
    reasons: Dict[str, str] = {
        ct: "Kiểu biểu đồ sản xuất tiêu chuẩn." for ct in ALL_CHART_TYPES
    }

    # 1. Kiem tra cot ket qua hoac ma loi -> PARETO
    error_col = None
    if res_cols:
        error_col = res_cols[0].name
    else:
        for c in cat_cols:
            if any(w in c.name.lower() for w in ("loi", "error", "defect", "fail", "code", "ma")):
                error_col = c.name
                break
    if error_col or res_cols:
        col_repr = error_col or res_cols[0].name
        scores[CHART_PARETO] += 12.0
        reasons[CHART_PARETO] = (
            f"Tệp có cột lỗi/kết quả '{col_repr}', Pareto là lựa chọn hàng đầu (Quy tắc 80/20) để tập trung giải quyết nguyên nhân gốc lớn nhất."
        )

    # 2. Kiem tra cot thoi gian -> TREND & SPC
    if dt_cols:
        dt_repr = dt_cols[0].name
        scores[CHART_TREND] += 11.0
        reasons[CHART_TREND] = (
            f"Tệp có cột thời gian '{dt_repr}', Run chart kèm SMA(20) giúp theo dõi biến động và xu hướng suy giảm chất lượng theo chuỗi thời gian."
        )
        scores[CHART_SPC] += 10.0
        reasons[CHART_SPC] = (
            f"Có mốc thời gian '{dt_repr}' và thông số đo, biểu đồ kiểm soát SPC cho phép giám sát giới hạn dung sai ±3σ (UCL/LCL)."
        )
        scores[CHART_STACKED_BAR] += 7.0
        reasons[CHART_STACKED_BAR] = (
            f"Theo dõi cơ cấu thành phần lỗi biến chuyển qua các mốc thời gian '{dt_repr}'."
        )

    # 3. Kiem tra so luong cot do luong so (Numeric)
    if len(num_cols) >= 2:
        c1, c2 = num_cols[0].name, num_cols[1].name
        scores[CHART_SCATTER] += 9.5
        reasons[CHART_SCATTER] = (
            f"Tệp có từ 2 cột số đo ('{c1}', '{c2}'), biểu đồ phân tán giúp tìm tương quan nhân quả giữa hai thông số."
        )
        scores[CHART_BOX_PLOT] += 8.5
        reasons[CHART_BOX_PLOT] = (
            f"Biểu đồ hộp (Box Plot) giúp nhìn rõ phân tán số liệu và các điểm dị biệt (outliers) giữa các lô/nhóm."
        )
    elif len(num_cols) == 1:
        c1 = num_cols[0].name
        scores[CHART_HISTOGRAM] += 9.0
        reasons[CHART_HISTOGRAM] = (
            f"Có thông số đo '{c1}', Histogram giúp đánh giá dạng phân bố chuẩn (Gaussian) và năng lực quá trình (Cp/Cpk)."
        )

    # 4. Kiem tra cot phan nhom (Line, May, Ca, Tram)
    group_col = None
    for c in cat_cols:
        if any(w in c.name.lower() for w in ("line", "chuyen", "station", "tram", "machine", "may", "ca", "shift", "jig")):
            group_col = c.name
            break
    if group_col:
        scores[CHART_GROUPED_BAR] += 8.5
        reasons[CHART_GROUPED_BAR] = (
            f"Có cột phân nhóm '{group_col}', thích hợp so sánh năng suất/thông số giữa các bộ phận."
        )
        scores[CHART_HEATMAP] += 8.0
        reasons[CHART_HEATMAP] = (
            f"Bản đồ nhiệt ma trận xác định điểm nóng lỗi (hotspots) tập trung ở '{group_col}'."
        )

    # 5. Kiem tra so luong nhom nho -> Donut
    for c in cat_cols:
        if 2 <= c.unique_count <= 8:
            scores[CHART_DONUT] += 7.5
            reasons[CHART_DONUT] = (
                f"Cột '{c.name}' có {c.unique_count} nhóm rõ rệt, thích hợp biểu diễn tỷ trọng dạng Donut."
            )
            break

    # Sap xep theo diem giam dan
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(chart_type, score, reasons[chart_type]) for chart_type, score in ranked]


def build_initial_spec(table: ParsedLogTable) -> ChartSpec:
    """Xay dung ChartSpec khoi tao toi uu nhat dua tren dac diem cua file log."""
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)
    res_cols = table.get_columns_by_role(ROLE_RESULT)
    cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL)
    num_cols = table.get_columns_by_role(ROLE_NUMERIC)

    ranked = recommend_chart_types(table)
    top_chart_type = ranked[0][0] if ranked else CHART_TREND

    x_col = ""
    y_col = ""
    group_col = None

    if top_chart_type == CHART_PARETO:
        x_col = res_cols[0].name if res_cols else (cat_cols[0].name if cat_cols else table.columns[0].name)
        y_col = num_cols[0].name if num_cols else ""
    elif top_chart_type in (CHART_TREND, CHART_SPC):
        x_col = dt_cols[0].name if dt_cols else table.columns[0].name
        y_col = num_cols[0].name if num_cols else (table.columns[1].name if len(table.columns) > 1 else x_col)
    elif top_chart_type == CHART_SCATTER:
        if len(num_cols) >= 2:
            x_col = num_cols[0].name
            y_col = num_cols[1].name
        else:
            x_col = table.columns[0].name
            y_col = num_cols[0].name if num_cols else table.columns[-1].name
    elif top_chart_type == CHART_HISTOGRAM:
        y_col = num_cols[0].name if num_cols else table.columns[0].name
        x_col = y_col
    else:
        x_col = (dt_cols or cat_cols or table.columns)[0].name
        y_col = (num_cols or table.columns)[0].name
        if cat_cols:
            group_col = cat_cols[0].name

    return ChartSpec(
        file_name=table.file_name,
        chart_type=top_chart_type,
        x_col=x_col,
        y_col=y_col,
        group_col=group_col,
        options={
            "show_sma": True,
            "sma_window": 20,
            "ucl": None,
            "lcl": None,
            "cl": None,
            "bins": 15,
        },
    )
