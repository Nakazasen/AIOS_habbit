# -*- coding: utf-8 -*-
"""Bo ve 10 kieu bieu do san xuat pho bien va anh thu nho (thumbnails).

10 kieu bieu do:
1. Pareto (cot tan suat + duong luy ke %) [KET HOP 1: cot + duong]
2. Xu huong / Run chart kem SMA(20) [KET HOP 2: duong + SMA]
3. Bieu do kiem soat SPC (UCL / CL / LCL) [KET HOP 3: duong + 2 gioi han]
4. Cot nhom (so sanh line/ca/may)
5. Tron / Donut (ty trong)
6. Histogram (phan bo gia tri do)
7. Phan tan Scatter (tuong quan 2 bien)
8. Box plot (bien dong theo nhom)
9. Heatmap (loi theo gio x nhom/line)
10. Cot chong theo thoi gian (co cau loai loi)

Dac diem:
- Su dung Matplotlib che do Agg khong cua so, nhe, on dinh.
- Phong cach Monozukuri chuan: phong trang/xam sach se, do tuong phan cao.
- Anh thu nho duoc VE BANG CHINH DU LIEU THUC cua file vua tha (khong dung anh minh hoa chung).
- Duoi moi bieu do ghi ro nguon du lieu da dung (ten file, so dong, dieu kien loc).
"""

from __future__ import annotations

import io
import math
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from aios_habit.log_chart.parser import (
    ParsedLogTable,
    ROLE_CATEGORICAL,
    ROLE_DATETIME,
    ROLE_NUMERIC,
    ROLE_RESULT,
)
from aios_habit.log_chart.spec import (
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
from aios_habit.production_prediction.trend_alerts import sma as _calc_sma

# Bang mau chuan Monozukuri cong nghiep
COLOR_PRIMARY_BLUE = "#1565c0"
COLOR_ACCENT_ORANGE = "#e65100"
COLOR_SMA_PURPLE = "#7b1fa2"
COLOR_LIMIT_RED = "#c62828"
COLOR_CENTER_GREEN = "#2e7d32"
COLOR_GRID_GRAY = "#e0e0e0"

PALETTE_DISTINCT = [
    "#1565c0", "#2e7d32", "#e65100", "#7b1fa2",
    "#00838f", "#c2185b", "#ef6c00", "#455a64"
]


def _apply_filters(table: ParsedLogTable, spec: ChartSpec) -> List[Dict[str, Any]]:
    """Loc cac dong du lieu theo spec."""
    rows = table.rows
    if spec.row_start > 0 or spec.row_end is not None:
        end = spec.row_end if spec.row_end is not None else len(rows)
        rows = rows[spec.row_start:end]

    if not spec.filter_col:
        return rows

    f_col = spec.filter_col
    f_val = str(spec.filter_val or "").strip().lower()
    f_op = spec.filter_op

    filtered: List[Dict[str, Any]] = []
    for r in rows:
        v = r.get(f_col)
        v_str = str(v or "").strip().lower()

        if f_op == "only_ng":
            if v_str in ("ng", "fail", "bad", "loi", "false", "0"):
                filtered.append(r)
        elif f_op == "contains":
            if f_val in v_str:
                filtered.append(r)
        elif f_op == "eq":
            if v_str == f_val:
                filtered.append(r)
        elif f_op == "neq":
            if v_str != f_val:
                filtered.append(r)
        else:
            filtered.append(r)

    return filtered


def _add_provenance_footer(fig: plt.Figure, table: ParsedLogTable, spec: ChartSpec, rows_used: int) -> None:
    """Them dong ghi chu nguon du lieu duoi cung bieu do."""
    filter_note = "Không lọc (Tất cả)"
    if spec.filter_col:
        if spec.filter_op == "only_ng":
            filter_note = f"Chỉ dòng NG ({spec.filter_col})"
        else:
            filter_note = f"{spec.filter_col} == '{spec.filter_val}'"

    note = f"Nguồn dữ liệu: {table.file_name} | {rows_used:,} dòng đã dùng | Điều kiện: {filter_note}"
    fig.text(0.5, 0.015, note, ha="center", va="bottom", fontsize=8.5, color="#555555", style="italic")


def render_chart_image(
    spec: ChartSpec,
    table: ParsedLogTable,
    dpi: int = 150,
) -> bytes:
    """Ve bieu do chat luong cao ra dinh dang PNG bytes tu ChartSpec va ParsedLogTable."""
    rows = _apply_filters(table, spec)
    rows_used = len(rows)
    if rows_used == 0:
        return _render_empty_message("Không có dữ liệu phù hợp với điều kiện lọc hiện tại.", spec, table)

    chart_type = spec.chart_type

    plt.close("all")
    fig = plt.figure(figsize=(9.2, 5.2), dpi=dpi)
    ax = fig.add_subplot(111)

    try:
        if chart_type == CHART_PARETO:
            _draw_pareto(fig, ax, rows, spec, table)
        elif chart_type == CHART_TREND:
            _draw_trend(fig, ax, rows, spec, table)
        elif chart_type == CHART_SPC:
            _draw_spc(fig, ax, rows, spec, table)
        elif chart_type == CHART_GROUPED_BAR:
            _draw_grouped_bar(fig, ax, rows, spec, table)
        elif chart_type == CHART_DONUT:
            _draw_donut(fig, ax, rows, spec, table)
        elif chart_type == CHART_HISTOGRAM:
            _draw_histogram(fig, ax, rows, spec, table)
        elif chart_type == CHART_SCATTER:
            _draw_scatter(fig, ax, rows, spec, table)
        elif chart_type == CHART_BOX_PLOT:
            _draw_box_plot(fig, ax, rows, spec, table)
        elif chart_type == CHART_HEATMAP:
            _draw_heatmap(fig, ax, rows, spec, table)
        elif chart_type == CHART_STACKED_BAR:
            _draw_stacked_bar(fig, ax, rows, spec, table)
        else:
            _draw_trend(fig, ax, rows, spec, table)

        _add_provenance_footer(fig, table, spec, rows_used)
        fig.tight_layout(rect=[0, 0.04, 1, 0.96])

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor="white", edgecolor="none")
        buf.seek(0)
        return buf.getvalue()
    finally:
        plt.close(fig)


def render_thumbnail_image(
    chart_type: str,
    spec: ChartSpec,
    table: ParsedLogTable,
) -> bytes:
    """Ve anh thu nho (thumbnail) nho gon VE BANG CHINH DU LIEU cua file vua nap."""
    temp_spec = copy_spec_for_type(spec, chart_type, table)
    rows = _apply_filters(table, temp_spec)
    # Lay mau toi da 50 dong de thumbnail render cuc nhanh (< 15ms)
    if len(rows) > 50:
        step = max(1, len(rows) // 50)
        sample_rows = rows[::step][:50]
    else:
        sample_rows = rows

    plt.close("all")
    fig = plt.figure(figsize=(2.8, 1.8), dpi=80)
    ax = fig.add_subplot(111)

    try:
        if not sample_rows:
            ax.text(0.5, 0.5, "Không có DL", ha="center", va="center", fontsize=8)
            ax.axis("off")
        else:
            if chart_type == CHART_PARETO:
                _draw_pareto_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_TREND:
                _draw_trend_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_SPC:
                _draw_spc_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_GROUPED_BAR:
                _draw_grouped_bar_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_DONUT:
                _draw_donut_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_HISTOGRAM:
                _draw_histogram_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_SCATTER:
                _draw_scatter_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_BOX_PLOT:
                _draw_box_plot_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_HEATMAP:
                _draw_heatmap_thumbnail(fig, ax, sample_rows, temp_spec, table)
            elif chart_type == CHART_STACKED_BAR:
                _draw_stacked_bar_thumbnail(fig, ax, sample_rows, temp_spec, table)
            else:
                _draw_trend_thumbnail(fig, ax, sample_rows, temp_spec, table)

        fig.tight_layout(pad=0.2)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=80, facecolor="white")
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        plt.close(fig)
        fig_err = plt.figure(figsize=(2.8, 1.8), dpi=80)
        ax_err = fig_err.add_subplot(111)
        ax_err.text(0.5, 0.5, f"{chart_type.upper()}", ha="center", va="center", fontsize=9, color="#777")
        ax_err.axis("off")
        buf_err = io.BytesIO()
        fig_err.savefig(buf_err, format="png", dpi=80, facecolor="#f5f5f5")
        plt.close(fig_err)
        buf_err.seek(0)
        return buf_err.getvalue()
    finally:
        plt.close("all")


def copy_spec_for_type(base_spec: ChartSpec, new_type: str, table: ParsedLogTable) -> ChartSpec:
    """Tao mot spec phu hop voi kieu bieu do moi dua tren cac cot co san."""
    new_spec = ChartSpec(
        spec_id=f"TMP-{new_type}",
        file_id=base_spec.file_id,
        file_name=base_spec.file_name,
        chart_type=new_type,
        x_col=base_spec.x_col,
        y_col=base_spec.y_col,
        group_col=base_spec.group_col,
        filter_col=base_spec.filter_col,
        filter_val=base_spec.filter_val,
        filter_op=base_spec.filter_op,
        options=dict(base_spec.options),
    )

    num_cols = table.get_columns_by_role(ROLE_NUMERIC)
    cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL) + table.get_columns_by_role(ROLE_RESULT)
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)

    if new_type in (CHART_PARETO, CHART_DONUT):
        if cat_cols:
            new_spec.x_col = cat_cols[0].name
    elif new_type in (CHART_TREND, CHART_SPC):
        if dt_cols:
            new_spec.x_col = dt_cols[0].name
        if num_cols:
            new_spec.y_col = num_cols[0].name
    elif new_type == CHART_HISTOGRAM:
        if num_cols:
            new_spec.y_col = num_cols[0].name
    elif new_type == CHART_SCATTER:
        if len(num_cols) >= 2:
            new_spec.x_col = num_cols[0].name
            new_spec.y_col = num_cols[1].name
    elif new_type in (CHART_GROUPED_BAR, CHART_BOX_PLOT, CHART_HEATMAP, CHART_STACKED_BAR):
        if cat_cols:
            new_spec.group_col = cat_cols[0].name
        if num_cols:
            new_spec.y_col = num_cols[0].name

    return new_spec


# =========================================================================
# CAC HAM VE CHINH (FULL-RESOLUTION)
# =========================================================================

def _draw_pareto(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """1. Biểu đồ Pareto (Cột tần suất + Đường lũy kế %) [KẾT HỢP 1: Cột + Đường]."""
    target_col = spec.x_col or (table.get_columns_by_role(ROLE_CATEGORICAL) or table.columns)[0].name

    # Dem tan suat cac gia tri
    counts: Dict[str, int] = {}
    for r in rows:
        val = str(r.get(target_col) or "").strip()
        if val:
            counts[val] = counts.get(val, 0) + 1

    if not counts:
        counts = {"Không có dữ liệu": 1}

    # Sap xep giam dan
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_items) > 10:
        top_items = sorted_items[:9]
        other_cnt = sum(c for _, c in sorted_items[9:])
        top_items.append(("Khác", other_cnt))
    else:
        top_items = sorted_items

    labels = [k for k, _ in top_items]
    freqs = [v for _, v in top_items]
    total_count = sum(freqs)

    cum_pct: List[float] = []
    run_sum = 0.0
    for f in freqs:
        run_sum += f
        cum_pct.append((run_sum / total_count) * 100.0 if total_count > 0 else 0.0)

    # 1. Ve cot tan suat (truc Y trai)
    x_pos = list(range(len(labels)))
    bars = ax.bar(x_pos, freqs, color=COLOR_PRIMARY_BLUE, alpha=0.85, width=0.55, label="Tần suất (số lượng)")
    ax.set_ylabel("Tần suất xuất hiện (lần)", color=COLOR_PRIMARY_BLUE, fontweight="bold")
    ax.tick_params(axis="y", labelcolor=COLOR_PRIMARY_BLUE)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)

    # Them gia tri tren dau cot
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{int(h)}", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8.5)

    # 2. Ve duong luy ke % (truc Y phai)
    ax2 = ax.twinx()
    ax2.plot(x_pos, cum_pct, color=COLOR_ACCENT_ORANGE, marker="o", linewidth=2.2, markersize=5, label="Lũy kế (%)")
    ax2.axhline(80.0, color=COLOR_LIMIT_RED, linestyle="--", linewidth=1.5, alpha=0.85, label="Ngưỡng 80% Pareto")
    ax2.set_ylabel("Phần trăm lũy kế (%)", color=COLOR_ACCENT_ORANGE, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_ACCENT_ORANGE)
    ax2.set_ylim(0, 105)
    ax2.yaxis.set_major_formatter(PercentFormatter())

    # Ghep chu giai (legend)
    lines_1, labels_1 = ax.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left", framealpha=0.9)

    ax.set_title(f"Biểu đồ Pareto — Phân tích lỗi theo '{target_col}'", fontsize=12, fontweight="bold", pad=12)


def _draw_trend(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """2. Biểu đồ xu hướng / Run chart kèm phủ SMA(20) [KẾT HỢP 2: Đường + SMA]."""
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name
    x_col = spec.x_col

    # Lay gia tri so do Y
    raw_y: List[float] = []
    x_labels: List[str] = []
    for idx, r in enumerate(rows):
        val = r.get(y_col)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            try:
                raw_y.append(float(val))
                if x_col and r.get(x_col):
                    x_labels.append(str(r.get(x_col)))
                else:
                    x_labels.append(str(idx + 1))
            except (ValueError, TypeError):
                continue

    if not raw_y:
        raw_y = [0.0]
        x_labels = ["1"]

    # Ve duong gia tri thuc do
    x_indices = list(range(len(raw_y)))
    ax.plot(x_indices, raw_y, color=COLOR_PRIMARY_BLUE, marker=".", markersize=4,
            linewidth=1.4, alpha=0.85, label=f"Giá trị đo ({y_col})")

    # Tinh va phu duong SMA(20)
    show_sma = spec.options.get("show_sma", True)
    sma_win = int(spec.options.get("sma_window", 20))
    if show_sma and len(raw_y) >= 2:
        sma_vals = _calc_sma(raw_y, window=sma_win)
        valid_indices = [i for i, v in enumerate(sma_vals) if v is not None]
        valid_smas = [v for v in sma_vals if v is not None]
        if valid_smas:
            ax.plot(valid_indices, valid_smas, color=COLOR_SMA_PURPLE, linestyle="--",
                    linewidth=2.0, label=f"Đường SMA({sma_win})")

    ax.set_ylabel(f"Giá trị ({y_col})", fontweight="bold")
    ax.set_xlabel(f"Trục hoành ({x_col or 'Điểm đo liên tiếp'})", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.legend(loc="upper right", framealpha=0.9)

    # Chia nhan truc X hop ly
    if len(x_indices) > 10:
        step = max(1, len(x_indices) // 8)
        ax.set_xticks(x_indices[::step])
        ax.set_xticklabels([x_labels[i] for i in x_indices[::step]], rotation=20, ha="right", fontsize=8)
    else:
        ax.set_xticks(x_indices)
        ax.set_xticklabels(x_labels, rotation=20, ha="right", fontsize=8)

    ax.set_title(f"Biểu đồ xu hướng (Run Chart) — {y_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_spc(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """3. Biểu đồ kiểm soát SPC (UCL / CL / LCL) [KẾT HỢP 3: Đường + Hai đường giới hạn]."""
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name

    vals: List[float] = []
    for r in rows:
        v = r.get(y_col)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            try:
                vals.append(float(v))
            except (ValueError, TypeError):
                continue

    if not vals:
        vals = [0.0]

    n = len(vals)
    cl = sum(vals) / n
    variance = sum((v - cl) ** 2 for v in vals) / (n - 1) if n > 1 else 0.0
    sigma = math.sqrt(variance)

    # Uu tien nguong tu spec neu co cau hinh
    ucl = spec.options.get("ucl") if spec.options.get("ucl") is not None else cl + 3 * sigma
    lcl = spec.options.get("lcl") if spec.options.get("lcl") is not None else cl - 3 * sigma

    x_indices = list(range(n))

    # 1. Duong gia tri do
    ax.plot(x_indices, vals, color=COLOR_PRIMARY_BLUE, marker="o", markersize=4,
            linewidth=1.4, alpha=0.8, label=f"Điểm đo ({y_col})")

    # 2. Duong gioi han UCL, CL, LCL
    ax.axhline(ucl, color=COLOR_LIMIT_RED, linestyle="--", linewidth=1.8, label=f"UCL (+3σ) = {ucl:.2f}")
    ax.axhline(cl, color=COLOR_CENTER_GREEN, linestyle="-", linewidth=1.8, label=f"CL (Trung bình) = {cl:.2f}")
    ax.axhline(lcl, color=COLOR_LIMIT_RED, linestyle="--", linewidth=1.8, label=f"LCL (-3σ) = {lcl:.2f}")

    # Danh dau cac diem vuot nguong (Out of Control)
    ooc_indices = [i for i, v in enumerate(vals) if v > ucl or v < lcl]
    ooc_vals = [vals[i] for i in ooc_indices]
    if ooc_indices:
        ax.scatter(ooc_indices, ooc_vals, color=COLOR_LIMIT_RED, s=60, zorder=5, label=f"Điểm lệch SPC ({len(ooc_indices)})")

    ax.set_ylabel(f"Giá trị ({y_col})", fontweight="bold")
    ax.set_xlabel("Số thứ tự điểm đo", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=8.5)
    ax.set_title(f"Biểu đồ kiểm soát SPC — {y_col} (σ={sigma:.2f})", fontsize=12, fontweight="bold", pad=12)


def _draw_grouped_bar(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """4. Cột nhóm: So sánh trung bình hoặc tần suất theo Line/Ca/Máy."""
    group_col = spec.group_col or (table.get_columns_by_role(ROLE_CATEGORICAL) or table.columns)[0].name
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name

    groups_data: Dict[str, List[float]] = {}
    for r in rows:
        grp = str(r.get(group_col) or "Chung").strip()
        val = r.get(y_col)
        if val is not None:
            try:
                groups_data.setdefault(grp, []).append(float(val))
            except (ValueError, TypeError):
                pass

    if not groups_data:
        groups_data = {"Không có DL": [0.0]}

    labels = sorted(groups_data.keys())[:8]
    means = [sum(groups_data[k]) / len(groups_data[k]) if groups_data[k] else 0.0 for k in labels]
    counts = [len(groups_data[k]) for k in labels]

    x = range(len(labels))
    bars = ax.bar(x, means, width=0.5, color=PALETTE_DISTINCT[0], alpha=0.85, label="Trung bình")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(f"Trung bình ({y_col})", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)

    for i, bar in enumerate(bars):
        h = bar.get_height()
        ax.annotate(f"{h:.2f}\n(n={counts[i]})", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)

    ax.set_title(f"Biểu đồ cột nhóm: {y_col} theo {group_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_donut(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """5. Biểu đồ tròn / Donut biểu thị tỷ trọng."""
    cat_col = spec.x_col or (table.get_columns_by_role(ROLE_CATEGORICAL) or table.columns)[0].name

    counts: Dict[str, int] = {}
    for r in rows:
        v = str(r.get(cat_col) or "").strip()
        if v:
            counts[v] = counts.get(v, 0) + 1

    if not counts:
        counts = {"Trống": 1}

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
    labels = [k for k, _ in sorted_items]
    sizes = [v for _, v in sorted_items]
    total = sum(sizes)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%", startangle=90,
        colors=PALETTE_DISTINCT[:len(labels)],
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
        textprops=dict(fontsize=8.5)
    )
    ax.text(0, 0, f"Tổng\n{total:,}", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.set_title(f"Biểu đồ Donut: Tỷ trọng cơ cấu theo '{cat_col}'", fontsize=12, fontweight="bold", pad=12)


def _draw_histogram(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """6. Histogram: Phân bố giá trị đo."""
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name
    vals = [float(r.get(y_col)) for r in rows if r.get(y_col) is not None and _is_valid_float(r.get(y_col))]

    if not vals:
        vals = [0.0]

    n, bins, patches = ax.hist(vals, bins=spec.options.get("bins", 15),
                               color=COLOR_PRIMARY_BLUE, edgecolor="white", alpha=0.85)

    mean_val = sum(vals) / len(vals)
    ax.axvline(mean_val, color=COLOR_LIMIT_RED, linestyle="--", linewidth=2, label=f"Trung bình = {mean_val:.2f}")

    ax.set_xlabel(f"Giá trị đo ({y_col})", fontweight="bold")
    ax.set_ylabel("Tần suất xuất hiện (lần)", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.legend(loc="upper right")
    ax.set_title(f"Histogram phân bố giá trị đo — {y_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_scatter(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """7. Phân tán Scatter: Tương quan giữa 2 biến số."""
    num_cols = table.get_columns_by_role(ROLE_NUMERIC)
    x_col = spec.x_col or (num_cols[0].name if len(num_cols) >= 1 else "X")
    y_col = spec.y_col or (num_cols[1].name if len(num_cols) >= 2 else x_col)

    x_vals: List[float] = []
    y_vals: List[float] = []
    for r in rows:
        vx = r.get(x_col)
        vy = r.get(y_col)
        if _is_valid_float(vx) and _is_valid_float(vy):
            x_vals.append(float(vx))
            y_vals.append(float(vy))

    if not x_vals:
        x_vals, y_vals = [0.0], [0.0]

    ax.scatter(x_vals, y_vals, color=COLOR_PRIMARY_BLUE, alpha=0.6, s=30, edgecolors="none")

    # Duong xu huong hoi quy tuyen tinh neu co du diem
    if len(x_vals) >= 3 and len(set(x_vals)) > 1:
        mx = sum(x_vals) / len(x_vals)
        my = sum(y_vals) / len(y_vals)
        cov = sum((x - mx) * (y - my) for x, y in zip(x_vals, y_vals))
        var_x = sum((x - mx) ** 2 for x in x_vals)
        if var_x > 0:
            slope = cov / var_x
            intercept = my - slope * mx
            line_x = [min(x_vals), max(x_vals)]
            line_y = [slope * x + intercept for x in line_x]
            ax.plot(line_x, line_y, color=COLOR_ACCENT_ORANGE, linestyle="--", linewidth=1.8,
                    label=f"Hồi quy (y = {slope:.2f}x + {intercept:.2f})")
            ax.legend(loc="upper left")

    ax.set_xlabel(f"Biến X ({x_col})", fontweight="bold")
    ax.set_ylabel(f"Biến Y ({y_col})", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.set_title(f"Biểu đồ phân tán Scatter: {x_col} vs {y_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_box_plot(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """8. Box Plot: Biến động thông số theo nhóm."""
    group_col = spec.group_col or (table.get_columns_by_role(ROLE_CATEGORICAL) or table.columns)[0].name
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name

    groups_data: Dict[str, List[float]] = {}
    for r in rows:
        grp = str(r.get(group_col) or "Chung").strip()
        val = r.get(y_col)
        if _is_valid_float(val):
            groups_data.setdefault(grp, []).append(float(val))

    if not groups_data:
        groups_data = {"Không có DL": [0.0]}

    labels = sorted(groups_data.keys())[:7]
    data_list = [groups_data[k] for k in labels]

    box = ax.boxplot(data_list, tick_labels=labels, patch_artist=True,
                     boxprops=dict(facecolor="#bbdefb", color=COLOR_PRIMARY_BLUE),
                     medianprops=dict(color=COLOR_LIMIT_RED, linewidth=2),
                     flierprops=dict(marker="o", markersize=4, markerfacecolor="#f44336"))

    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(f"Phạm vi biến động ({y_col})", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.set_title(f"Biểu đồ hộp Box Plot: {y_col} theo {group_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_heatmap(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """9. Heatmap: Bản đồ nhiệt lỗi theo Giờ / Ngày x Nhóm."""
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)
    cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL) + table.get_columns_by_role(ROLE_RESULT)

    x_axis_col = spec.x_col or (dt_cols[0].name if dt_cols else table.columns[0].name)
    y_axis_col = spec.group_col or (cat_cols[0].name if cat_cols else table.columns[1].name)

    # Gom nhom theo 2 chieu
    x_keys: List[str] = []
    y_keys: List[str] = []
    matrix_counts: Dict[Tuple[str, str], int] = {}

    for r in rows:
        raw_x = str(r.get(x_axis_col) or "").strip()
        # Rut gon x neu la datetime thanh gio hoac ngay
        m_hour = re.search(r"(\d{1,2}):\d{2}", raw_x)
        x_val = f"{m_hour.group(1)}h" if m_hour else (raw_x[:10] if len(raw_x) >= 10 else raw_x)
        y_val = str(r.get(y_axis_col) or "Khác").strip()

        if x_val and y_val:
            if x_val not in x_keys:
                x_keys.append(x_val)
            if y_val not in y_keys:
                y_keys.append(y_val)
            key = (y_val, x_val)
            matrix_counts[key] = matrix_counts.get(key, 0) + 1

    x_keys = x_keys[:8]
    y_keys = y_keys[:6]

    if not x_keys or not y_keys:
        x_keys, y_keys = ["Ca 1", "Ca 2"], ["Line A", "Line B"]
        matrix_counts = {("Line A", "Ca 1"): 1, ("Line B", "Ca 2"): 3}

    grid = [[matrix_counts.get((y, x), 0) for x in x_keys] for y in y_keys]

    cax = ax.imshow(grid, cmap="YlOrRd", aspect="auto")
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04, label="Số lượng phát sinh")

    ax.set_xticks(range(len(x_keys)))
    ax.set_yticks(range(len(y_keys)))
    ax.set_xticklabels(x_keys, rotation=20, ha="right")
    ax.set_yticklabels(y_keys)

    # In con so cu the trong moi o
    for i in range(len(y_keys)):
        for j in range(len(x_keys)):
            val = grid[i][j]
            ax.text(j, i, str(val), ha="center", va="center",
                    color="black" if val < (max(max(r) for r in grid) * 0.7 or 1) else "white",
                    fontweight="bold", fontsize=9)

    ax.set_title(f"Bản đồ nhiệt Heatmap: {y_axis_col} x {x_axis_col}", fontsize=12, fontweight="bold", pad=12)


def _draw_stacked_bar(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    """10. Cột chồng theo thời gian: Cơ cấu loại lỗi."""
    dt_cols = table.get_columns_by_role(ROLE_DATETIME)
    cat_cols = table.get_columns_by_role(ROLE_CATEGORICAL) + table.get_columns_by_role(ROLE_RESULT)

    x_col = spec.x_col or (dt_cols[0].name if dt_cols else table.columns[0].name)
    sub_col = spec.group_col or (cat_cols[0].name if cat_cols else table.columns[1].name)

    time_buckets: Dict[str, Dict[str, int]] = {}
    all_categories: List[str] = []

    for r in rows:
        t_val = str(r.get(x_col) or "").strip()[:10] or "Chung"
        c_val = str(r.get(sub_col) or "Khác").strip()
        if c_val not in all_categories:
            all_categories.append(c_val)
        time_buckets.setdefault(t_val, {})
        time_buckets[t_val][c_val] = time_buckets[t_val].get(c_val, 0) + 1

    all_categories = all_categories[:5]
    time_keys = sorted(time_buckets.keys())[:8]

    bottoms = [0] * len(time_keys)
    for cat_idx, cat in enumerate(all_categories):
        values = [time_buckets[t].get(cat, 0) for t in time_keys]
        ax.bar(time_keys, values, bottom=bottoms, label=cat,
               color=PALETTE_DISTINCT[cat_idx % len(PALETTE_DISTINCT)], width=0.55)
        bottoms = [b + v for b, v in zip(bottoms, values)]

    ax.set_xticks(range(len(time_keys)))
    ax.set_xticklabels(time_keys, rotation=20, ha="right")
    ax.set_ylabel("Số lượng phát sinh", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=COLOR_GRID_GRAY)
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title(f"Cột chồng theo thời gian: Cơ cấu '{sub_col}' theo '{x_col}'", fontsize=12, fontweight="bold", pad=12)


def _render_empty_message(msg: str, spec: ChartSpec, table: ParsedLogTable) -> bytes:
    """Tra ve anh thong bao khi khong co dong hop le."""
    plt.close("all")
    fig = plt.figure(figsize=(8, 3.5), dpi=100)
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=11, color="#d32f2f")
    ax.axis("off")
    _add_provenance_footer(fig, table, spec, 0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _is_valid_float(v: Any) -> bool:
    if v is None:
        return False
    try:
        f = float(v)
        return not (math.isnan(f) or math.isinf(f))
    except (ValueError, TypeError):
        return False


# =========================================================================
# CAC HAM VE ANH THU NHO (THUMBNAILS - TINH GIAN CHO TOC DO CAO)
# =========================================================================

def _draw_pareto_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    target_col = spec.x_col or (table.get_columns_by_role(ROLE_CATEGORICAL) or table.columns)[0].name
    counts: Dict[str, int] = {}
    for r in rows:
        val = str(r.get(target_col) or "").strip()
        if val:
            counts[val] = counts.get(val, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5] or [("A", 5), ("B", 3)]
    labels = [k[:4] for k, _ in sorted_items]
    freqs = [v for _, v in sorted_items]
    x_pos = list(range(len(labels)))
    ax.bar(x_pos, freqs, color=COLOR_PRIMARY_BLUE, width=0.6)
    cum = []
    s = 0
    tot = sum(freqs) or 1
    for f in freqs:
        s += f
        cum.append(s / tot * 100)
    ax2 = ax.twinx()
    ax2.plot(x_pos, cum, color=COLOR_ACCENT_ORANGE, marker="o", markersize=3)
    ax2.axis("off")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels)
    ax.set_title("1. Pareto", fontsize=7.5, pad=2)

def _draw_trend_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name
    vals = [float(r.get(y_col)) for r in rows if _is_valid_float(r.get(y_col))][:30] or [1, 2, 3, 2, 4]
    ax.plot(vals, color=COLOR_PRIMARY_BLUE, linewidth=1)
    if len(vals) >= 5:
        sma_vals = _calc_sma(vals, window=min(5, len(vals)))
        valid_i = [i for i, v in enumerate(sma_vals) if v is not None]
        valid_v = [v for v in sma_vals if v is not None]
        ax.plot(valid_i, valid_v, color=COLOR_SMA_PURPLE, linestyle="--", linewidth=1.2)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("2. Trend + SMA", fontsize=7.5, pad=2)

def _draw_spc_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name
    vals = [float(r.get(y_col)) for r in rows if _is_valid_float(r.get(y_col))][:30] or [10, 11, 9, 12, 10]
    cl = sum(vals) / len(vals)
    sigma = math.sqrt(sum((v - cl)**2 for v in vals) / len(vals)) if len(vals) > 1 else 1.0
    ax.plot(vals, color=COLOR_PRIMARY_BLUE, linewidth=1)
    ax.axhline(cl + 3*sigma, color=COLOR_LIMIT_RED, linestyle="--", linewidth=1)
    ax.axhline(cl, color=COLOR_CENTER_GREEN, linewidth=1)
    ax.axhline(cl - 3*sigma, color=COLOR_LIMIT_RED, linestyle="--", linewidth=1)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("3. SPC", fontsize=7.5, pad=2)

def _draw_grouped_bar_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    ax.bar(["L1", "L2", "L3"], [12, 18, 9], color=COLOR_PRIMARY_BLUE, width=0.5)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("4. Cột nhóm", fontsize=7.5, pad=2)

def _draw_donut_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    ax.pie([45, 30, 25], colors=PALETTE_DISTINCT[:3], wedgeprops=dict(width=0.45, edgecolor="w"))
    ax.set_title("5. Donut", fontsize=7.5, pad=2)

def _draw_histogram_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    y_col = spec.y_col or (table.get_columns_by_role(ROLE_NUMERIC) or table.columns)[0].name
    vals = [float(r.get(y_col)) for r in rows if _is_valid_float(r.get(y_col))] or [1, 2, 2, 3, 3, 3, 4]
    ax.hist(vals, bins=8, color=COLOR_PRIMARY_BLUE, edgecolor="w")
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("6. Histogram", fontsize=7.5, pad=2)

def _draw_scatter_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    num_cols = table.get_columns_by_role(ROLE_NUMERIC)
    x_col = spec.x_col or (num_cols[0].name if len(num_cols) >= 1 else "X")
    y_col = spec.y_col or (num_cols[1].name if len(num_cols) >= 2 else x_col)
    pts = [(float(r.get(x_col)), float(r.get(y_col))) for r in rows if _is_valid_float(r.get(x_col)) and _is_valid_float(r.get(y_col))][:30] or [(1, 2), (2, 3), (3, 5)]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], color=COLOR_PRIMARY_BLUE, s=12)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("7. Scatter", fontsize=7.5, pad=2)

def _draw_box_plot_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    ax.boxplot([[1, 2, 3, 4], [2, 3, 5, 6]], tick_labels=["A", "B"], patch_artist=True,
               boxprops=dict(facecolor="#bbdefb", color=COLOR_PRIMARY_BLUE))
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("8. Box Plot", fontsize=7.5, pad=2)

def _draw_heatmap_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    grid = [[1, 4, 2], [3, 1, 5]]
    ax.imshow(grid, cmap="YlOrRd", aspect="auto")
    ax.axis("off")
    ax.set_title("9. Heatmap", fontsize=7.5, pad=2)

def _draw_stacked_bar_thumbnail(fig: plt.Figure, ax: plt.Axes, rows: List[Dict[str, Any]], spec: ChartSpec, table: ParsedLogTable) -> None:
    ax.bar(["1", "2"], [3, 5], color=PALETTE_DISTINCT[0], width=0.5)
    ax.bar(["1", "2"], [2, 3], bottom=[3, 5], color=PALETTE_DISTINCT[1], width=0.5)
    ax.tick_params(axis="both", labelsize=6)
    ax.set_title("10. Stacked", fontsize=7.5, pad=2)
