# -*- coding: utf-8 -*-
"""Plotly chart generator and static Kaleido renderer for bakeoff.

Renders high-fidelity, production-grade 1500x900 PNG charts with zero legend overlap.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def export_plotly_png(fig: go.Figure, width: int = 1500, height: int = 900) -> Tuple[bytes, float]:
    """Exports a Plotly figure to PNG using Kaleido and measures duration."""
    t0 = time.perf_counter()
    png_bytes = fig.to_image(format="png", width=width, height=height)
    duration = time.perf_counter() - t0
    return png_bytes, duration


def build_run_sma_plotly(
    times: List[str],
    raw_y: List[float],
    sma_y: List[Optional[float]],
    metric_name: str = "SKEW:BLACK",
    jig_id: str = "2ND-1002",
    unit: str = "µm",
) -> go.Figure:
    """Builds Plotly Figure for Run chart + SMA(20). Legend strictly outside plot area."""
    fig = go.Figure()

    # Raw measurement series
    fig.add_trace(
        go.Scatter(
            x=times,
            y=raw_y,
            mode="lines+markers",
            name=f"Giá trị đo ({metric_name})",
            line=dict(color="#1565c0", width=1.8),
            marker=dict(size=5, color="#1565c0"),
        )
    )

    # SMA(20) series
    sma_filtered_x = [t for t, s in zip(times, sma_y) if s is not None]
    sma_filtered_y = [s for s in sma_y if s is not None]

    fig.add_trace(
        go.Scatter(
            x=sma_filtered_x,
            y=sma_filtered_y,
            mode="lines",
            name="Đường SMA(20)",
            line=dict(color="#7b1fa2", width=2.6, dash="dash"),
        )
    )

    tick_interval = max(1, len(times) // 8)
    sampled_ticks = [times[i] for i in range(0, len(times), tick_interval)]

    fig.update_layout(
        width=1500,
        height=900,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Tahoma, Arial, sans-serif", size=12, color="#263238"),
        title=dict(
            text=f"<b>Biểu đồ xu hướng (Run Chart) — {metric_name} [{unit}] — JIG {jig_id}</b><br><span style='font-size:12px;color:#546e7a;'>N = {len(raw_y)} điểm đo thực tế | Phủ đường trung bình động SMA(20) nét đứt tím</span>",
            x=0.5,
            y=0.97,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="#1a237e"),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=13, color="#263238"),
        ),
        margin=dict(l=90, r=90, t=130, b=85),
        xaxis=dict(
            title=dict(text="<b>Thời gian đo lường</b>", font=dict(size=12, color="#263238")),
            tickmode="array",
            tickvals=sampled_ticks,
            tickangle=20,
            showgrid=True,
            gridcolor="#eceff1",
            gridwidth=1,
            griddash="dash",
            linecolor="#cfd8dc",
            ticks="outside",
        ),
        yaxis=dict(
            title=dict(text=f"<b>Độ lệch [{unit}]</b>", font=dict(size=12, color="#263238")),
            showgrid=True,
            gridcolor="#eceff1",
            gridwidth=1,
            griddash="dash",
            linecolor="#cfd8dc",
            ticks="outside",
        ),
    )
    return fig


def build_spc_plotly(
    times: List[str],
    vals: List[float],
    cl: float = 4.60,
    ucl: float = 4.85,
    lcl: float = 4.35,
    sigma: float = 0.08,
    jig_id: str = "JIG-1003_1",
    metric_name: str = "MeasureFieldCurvatureYellow",
    unit: str = "sec",
) -> go.Figure:
    """Builds Plotly Figure for SPC chart with CL/UCL/LCL, Zone A/B/C, and NG anomaly markers.
    Legend is positioned horizontally at top (y=1.05), strictly outside plot area,
    eliminating any occlusion of rising NG data points in top-right!
    """
    fig = go.Figure()

    # Zone rectangles (A, B, C)
    # Zone A (Safe ±1σ)
    fig.add_hrect(
        y0=cl - sigma,
        y1=cl + sigma,
        fillcolor="rgba(76, 175, 80, 0.16)",
        line_width=0,
        layer="below",
    )
    # Zone B (Warning 1σ-2σ)
    fig.add_hrect(
        y0=cl + sigma,
        y1=cl + 2 * sigma,
        fillcolor="rgba(255, 152, 0, 0.16)",
        line_width=0,
        layer="below",
    )
    fig.add_hrect(
        y0=cl - 2 * sigma,
        y1=cl - sigma,
        fillcolor="rgba(255, 152, 0, 0.16)",
        line_width=0,
        layer="below",
    )
    # Zone C (Danger 2σ-3σ)
    fig.add_hrect(
        y0=cl + 2 * sigma,
        y1=ucl,
        fillcolor="rgba(244, 67, 54, 0.16)",
        line_width=0,
        layer="below",
    )
    fig.add_hrect(
        y0=lcl,
        y1=cl - 2 * sigma,
        fillcolor="rgba(244, 67, 54, 0.16)",
        line_width=0,
        layer="below",
    )

    # Normal measurements line
    fig.add_trace(
        go.Scatter(
            x=times,
            y=vals,
            mode="lines+markers",
            name="Dữ liệu đo tuần",
            line=dict(color="#1565c0", width=2.2),
            marker=dict(size=7, color="#1565c0"),
        )
    )

    # NG Anomaly points
    ng_times = [t for t, v in zip(times, vals) if v > ucl or v < lcl]
    ng_vals = [v for v in vals if v > ucl or v < lcl]
    ng_count = len(ng_vals)

    fig.add_trace(
        go.Scatter(
            x=ng_times,
            y=ng_vals,
            mode="markers",
            name=f"Điểm vượt ngưỡng / NG ({ng_count})",
            marker=dict(size=13, color="#d50000", line=dict(color="#ffffff", width=2)),
        )
    )

    # Limit lines with annotations
    fig.add_hline(
        y=ucl,
        line=dict(color="#c62828", width=2.0, dash="dash"),
        annotation_text=f"UCL={ucl:.2f}",
        annotation_position="top right",
        annotation_font=dict(color="#c62828", size=11),
    )
    fig.add_hline(
        y=cl,
        line=dict(color="#2e7d32", width=2.0, dash="solid"),
        annotation_text=f"CL={cl:.2f}",
        annotation_position="top right",
        annotation_font=dict(color="#2e7d32", size=11),
    )
    fig.add_hline(
        y=lcl,
        line=dict(color="#c62828", width=2.0, dash="dash"),
        annotation_text=f"LCL={lcl:.2f}",
        annotation_position="bottom right",
        annotation_font=dict(color="#c62828", size=11),
    )

    # Dummy traces to include limit lines in legend
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            name=f"UCL (+3σ) = {ucl:.2f}",
            line=dict(color="#c62828", width=2.0, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            name=f"CL (Trung tâm) = {cl:.2f}",
            line=dict(color="#2e7d32", width=2.0, dash="solid"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            name=f"LCL (-3σ) = {lcl:.2f}",
            line=dict(color="#c62828", width=2.0, dash="dash"),
        )
    )

    fig.update_layout(
        width=1500,
        height=900,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Tahoma, Arial, sans-serif", size=12, color="#263238"),
        title=dict(
            text=f"<b>Biểu đồ kiểm soát SPC — {metric_name} — JIG {jig_id} [{unit}]</b><br><span style='font-size:12px;color:#546e7a;'>Đoạn trôi dốc tuần 21-28 ({ng_count} điểm NG liên tiếp vượt UCL) | CL={cl:.2f}, UCL={ucl:.2f}, LCL={lcl:.2f}, σ={sigma:.2f}</span>",
            x=0.5,
            y=0.97,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="#1a237e"),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=12.5, color="#263238"),
        ),
        margin=dict(l=90, r=90, t=130, b=85),
        xaxis=dict(
            title=dict(text="<b>Tuần sản xuất</b>", font=dict(size=12, color="#263238")),
            tickangle=25,
            showgrid=True,
            gridcolor="#eceff1",
            gridwidth=1,
            griddash="dash",
            linecolor="#cfd8dc",
            ticks="outside",
        ),
        yaxis=dict(
            title=dict(text=f"<b>Độ cong [{unit}]</b>", font=dict(size=12, color="#263238")),
            range=[4.25, 5.40],
            showgrid=True,
            gridcolor="#eceff1",
            gridwidth=1,
            griddash="dash",
            linecolor="#cfd8dc",
            ticks="outside",
        ),
    )
    return fig


def build_pareto_plotly(
    categories: List[str],
    frequencies: List[int],
    title_suffix: str = "JIG 2ND-1002",
) -> go.Figure:
    """Builds Plotly Figure for Pareto Chart (Frequency Bar + Cumulative % Line + 80% Cutoff)."""
    total = sum(frequencies)
    cum_pct = []
    run = 0.0
    for f in frequencies:
        run += f
        cum_pct.append(round((run / total) * 100.0, 2))

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Bar trace (Primary Y)
    fig.add_trace(
        go.Bar(
            x=categories,
            y=frequencies,
            name="Tần suất lỗi (Số lượng)",
            marker=dict(color="#1565c0", line=dict(color="#ffffff", width=1.5)),
            text=frequencies,
            textposition="outside",
            textfont=dict(size=11, color="#1565c0"),
        ),
        secondary_y=False,
    )

    # Cumulative line trace (Secondary Y)
    fig.add_trace(
        go.Scatter(
            x=categories,
            y=cum_pct,
            mode="lines+markers+text",
            name="Phần trăm lũy kế (%)",
            line=dict(color="#ef6c00", width=2.6),
            marker=dict(size=8, color="#ef6c00"),
            text=[f"{p}%" for p in cum_pct],
            textposition="top right",
            textfont=dict(size=10.5, color="#e65100"),
        ),
        secondary_y=True,
    )

    # 80% threshold line
    fig.add_trace(
        go.Scatter(
            x=categories,
            y=[80.0] * len(categories),
            mode="lines",
            name="Ngưỡng 80% Pareto",
            line=dict(color="#c62828", width=2.0, dash="dash"),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        width=1500,
        height=900,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Tahoma, Arial, sans-serif", size=12, color="#263238"),
        title=dict(
            text=f"<b>Biểu đồ Pareto phân tích lỗi kiểm tra — {title_suffix}</b><br><span style='font-size:12px;color:#546e7a;'>Tổng cộng {total:,} lượt lỗi ghi nhận | Quy tắc 80/20 xác định nguyên nhân cốt lõi</span>",
            x=0.5,
            y=0.97,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="#1a237e"),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=13, color="#263238"),
        ),
        margin=dict(l=90, r=90, t=130, b=85),
        xaxis=dict(
            title=dict(text="<b>Hạng mục kiểm tra / Mã lỗi</b>", font=dict(size=12, color="#263238")),
            tickangle=20,
            linecolor="#cfd8dc",
            ticks="outside",
        ),
    )

    fig.update_yaxes(
        title_text="<b>Tần suất [lần]</b>",
        secondary_y=False,
        title_font=dict(color="#1565c0", size=12),
        tickfont=dict(color="#1565c0", size=11),
        showgrid=True,
        gridcolor="#eceff1",
        griddash="dash",
        linecolor="#1565c0",
    )
    fig.update_yaxes(
        title_text="<b>Lũy kế [%]</b>",
        secondary_y=True,
        range=[0, 105],
        title_font=dict(color="#ef6c00", size=12),
        tickfont=dict(color="#ef6c00", size=11),
        ticksuffix="%",
        showgrid=False,
        linecolor="#ef6c00",
    )
    return fig


def build_histogram_plotly(
    bin_labels: List[str],
    counts: List[int],
    mean_val: float,
    metric_name: str = "SKEW:BLACK",
    unit: str = "µm",
) -> go.Figure:
    """Builds Plotly Figure for Histogram chart with vertical Mean line."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=bin_labels,
            y=counts,
            name="Tần suất (Số mẫu)",
            marker=dict(color="#1565c0", line=dict(color="#ffffff", width=1.5)),
            text=counts,
            textposition="outside",
            textfont=dict(size=10.5, color="#1565c0"),
        )
    )

    # Mean line trace for legend
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            name=f"Trung bình = {mean_val:.2f}",
            line=dict(color="#c62828", width=2.2, dash="dash"),
        )
    )

    fig.update_layout(
        width=1500,
        height=900,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Tahoma, Arial, sans-serif", size=12, color="#263238"),
        title=dict(
            text=f"<b>Histogram phân bố giá trị đo — {metric_name} [{unit}]</b><br><span style='font-size:12px;color:#546e7a;'>Phân bố tần suất qua các khoảng đo | Giá trị trung bình: {mean_val:.2f} {unit}</span>",
            x=0.5,
            y=0.97,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="#1a237e"),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=13, color="#263238"),
        ),
        margin=dict(l=90, r=90, t=130, b=85),
        xaxis=dict(
            title=dict(text=f"<b>Khoảng giá trị đo [{unit}]</b>", font=dict(size=12, color="#263238")),
            tickangle=20,
            showgrid=False,
            linecolor="#cfd8dc",
            ticks="outside",
        ),
        yaxis=dict(
            title=dict(text="<b>Tần suất xuất hiện [lần]</b>", font=dict(size=12, color="#263238")),
            showgrid=True,
            gridcolor="#eceff1",
            griddash="dash",
            linecolor="#cfd8dc",
            ticks="outside",
        ),
    )
    return fig


def build_large_n_plotly(
    x_data: List[int],
    y_data: List[float],
    use_webgl: bool = True,
    metric_name: str = "BOW:BLACK:-70",
    unit: str = "µm",
) -> go.Figure:
    """Builds Plotly Figure for performance testing with >= 10,000 points."""
    scatter_cls = go.Scattergl if use_webgl else go.Scatter
    renderer_name = "Scattergl (WebGL)" if use_webgl else "Scatter (SVG)"

    fig = go.Figure()
    fig.add_trace(
        scatter_cls(
            x=x_data,
            y=y_data,
            mode="lines",
            name="Chuỗi dữ liệu lớn",
            line=dict(color="#1565c0", width=1.0),
        )
    )

    fig.update_layout(
        width=1500,
        height=900,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        title=dict(
            text=f"<b>Plotly Benchmark (N = {len(y_data):,} điểm) — {metric_name} [{unit}]</b><br><span style='font-size:12px;color:#546e7a;'>Renderer: {renderer_name}</span>",
            x=0.5,
            y=0.97,
            xanchor="center",
            yanchor="top",
            font=dict(size=18, color="#1a237e"),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
        ),
        margin=dict(l=80, r=80, t=120, b=70),
    )
    return fig
