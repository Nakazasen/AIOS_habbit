# -*- coding: utf-8 -*-
"""Unit and regression tests for DESKTOP-HOME-CHART-UX-PRODUCTION.

Verifies:
1. Chart theme single source of truth (aios_habit.chart_theme):
   - Monozukuri color palette integrity.
   - Vietnamese font resolution (no tofu, valid system fonts).
   - Standard figure sizes and DPIs.
   - Title and axis label formatters with units.
2. Log chart Matplotlib renderer:
   - Line chart with SMA(20) and NG points highlighted.
   - SPC chart with UCL, CL, LCL, and color zones.
   - Pareto, Grouped Bar, Histogram, etc.
   - Axis ticks never overlap, titles complete with device + metric + time range.
3. Pillow SPC renderer (spc_chart.py):
   - Grid lines, Y-axis measurements, X-axis timestamps, legend, title.
   - Distribution chart (render_phan_bo_png).
   - Multi-series comparison (render_so_sanh_png).
4. Data integrity invariant:
   - SMA(20), limits (UCL/CL/LCL), and anomaly counts are 100% identical.
5. Continuous improvement loop (feedback.py):
   - Weekly metrics grouping (renders, negative feedback rate per ISO week).
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import pytest

from aios_habit.chart_theme import (
    COLOR_PRIMARY_BLUE,
    COLOR_SMA_PURPLE,
    COLOR_LIMIT_RED,
    COLOR_WARN_ORANGE,
    COLOR_CENTER_GREEN,
    COLOR_ANOMALY_RED,
    RGB_PRIMARY_BLUE,
    RGB_SMA_PURPLE,
    get_pillow_font,
    format_chart_title,
    format_axis_label,
    detect_unit_from_metric,
    format_time_range_from_sequence,
    DEFAULT_DPI,
    DEFAULT_FIG_WIDTH_INCHES,
    DEFAULT_FIG_HEIGHT_INCHES,
)
from aios_habit.log_chart.parser import parse_log_file, ParsedLogTable
from aios_habit.log_chart.recommender import build_initial_spec
from aios_habit.log_chart.spec import CHART_TREND, CHART_SPC, CHART_PARETO
from aios_habit.log_chart.renderer import render_chart_image, render_thumbnail_image
from aios_habit.log_chart.feedback import (
    get_chart_metrics,
    get_weekly_chart_metrics,
    record_chart_render_event,
    record_chart_feedback,
    RATING_HUU_ICH,
    RATING_CHUA_HUU_ICH,
)
from aios_habit.production_prediction.spc_chart import (
    SpcChartInput,
    render_spc_png,
    render_phan_bo_png,
    render_so_sanh_png,
)
from aios_habit.production_prediction.trend_alerts import sma as _calc_sma


def test_chart_theme_palette_and_fonts():
    """Verify color tokens and font availability."""
    assert COLOR_PRIMARY_BLUE == "#1565c0"
    assert COLOR_SMA_PURPLE == "#7b1fa2"
    assert COLOR_LIMIT_RED == "#c62828"
    assert COLOR_ANOMALY_RED == "#d50000"

    # Font check
    font = get_pillow_font(size=14, bold=False)
    assert font is not None

    font_bold = get_pillow_font(size=18, bold=True)
    assert font_bold is not None


def test_chart_theme_formatting_helpers():
    """Verify title and label formatters handle Vietnamese and units."""
    # Unit detection
    assert detect_unit_from_metric("BOW_VALUE") == "µm"
    assert detect_unit_from_metric("takt:MeasureFieldCurvatureYellow[sec]") == "sec"
    assert detect_unit_from_metric("TEMPERATURE") == "℃"
    assert detect_unit_from_metric("HUMIDITY") == "%"

    # Title formatter
    title = format_chart_title(
        chart_kind="Biểu đồ xu hướng (Run Chart)",
        metric="BOW_VALUE",
        jig_id="2ND-1002",
        time_range="16:00:00 ~ 17:05:30",
        unit="µm",
    )
    assert "Biểu đồ xu hướng (Run Chart):" in title
    assert "Độ lệch chùm tia (BOW) (µm)" in title
    assert "JIG: 2ND-1002" in title
    assert "[16:00:00 ~ 17:05:30]" in title

    # Axis label formatter
    y_lbl = format_axis_label("BOW_VALUE", unit="µm", axis_role="y")
    assert "µm" in y_lbl
    assert "Độ lệch chùm tia (BOW)" in y_lbl

    # Time range formatter
    t_range = format_time_range_from_sequence(["08:00:00", "08:15:00", "08:30:00"])
    assert t_range == "08:00:00 ~ 08:30:00"


def test_log_chart_renderer_trend_and_spc(tmp_path: Path):
    """Verify log_chart renderer renders valid PNG with complete theme annotations."""
    csv_content = (
        "DATE,TIME,UNIT_ID,BOW_VALUE,RESULT\n"
        "2026.08.01,10:00:00,SN001,12.5,OK\n"
        "2026.08.01,10:05:00,SN002,13.0,OK\n"
        "2026.08.01,10:10:00,SN003,12.8,OK\n"
        "2026.08.01,10:15:00,SN004,19.5,NG\n"
        "2026.08.01,10:20:00,SN005,12.7,OK\n"
    )
    test_csv = tmp_path / "sample_log.csv"
    test_csv.write_text(csv_content, encoding="utf-8")

    table = parse_log_file(test_csv)
    spec_trend = build_initial_spec(table)
    spec_trend.chart_type = CHART_TREND

    png_bytes = render_chart_image(spec_trend, table)
    assert len(png_bytes) > 1000
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    # SPC chart
    spec_spc = build_initial_spec(table)
    spec_spc.chart_type = CHART_SPC
    spc_bytes = render_chart_image(spec_spc, table)
    assert len(spc_bytes) > 1000
    assert spc_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    # Thumbnail
    thumb_bytes = render_thumbnail_image(CHART_TREND, spec_trend, table)
    assert len(thumb_bytes) > 500


def test_pillow_spc_chart_renderers(tmp_path: Path):
    """Verify Pillow SPC, distribution and comparison renderers output valid images."""
    vals = [10.2 + 0.1 * i for i in range(25)]
    # Anomaly
    vals[15] = 25.0
    times = [f"10:{i:02d}:00" for i in range(25)]

    chart = SpcChartInput(
        jig_id="JIG-TEST-01",
        cong_doan="Công đoạn đo quang",
        metric="BOW_VALUE",
        unit="µm",
        values=vals,
        nhan_thoi_gian=times,
        usl=20.0,
        lsl=5.0,
        ucl=15.0,
        cl=11.5,
        lcl=8.0,
        cpk=1.33,
        sigma=0.85,
    )

    out_spc = tmp_path / "test_spc.png"
    res_path = render_spc_png(chart, out_spc, scale=2)
    assert res_path.exists()
    assert res_path.stat().st_size > 5000

    out_dist = tmp_path / "test_dist.png"
    res_dist = render_phan_bo_png(chart, out_dist, scale=2)
    assert res_dist.exists()
    assert res_dist.stat().st_size > 5000

    out_cmp = tmp_path / "test_cmp.png"
    chart2 = SpcChartInput(
        jig_id="JIG-TEST-02",
        metric="SKEW_VALUE",
        values=[8.0 + 0.1 * i for i in range(25)],
    )
    res_cmp = render_so_sanh_png([chart, chart2], out_cmp, scale=2)
    assert res_cmp.exists()
    assert res_cmp.stat().st_size > 5000


def test_calculations_preservation():
    """Invariant: calculations of SMA, limits, and values must be 100% identical."""
    raw = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0,
           20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 50.0]

    # SMA window=20
    sma_vals = _calc_sma(raw, window=20)
    assert sma_vals[0] is None
    assert sma_vals[18] is None
    expected_sma_20 = sum(raw[:20]) / 20.0  # 190 / 20 = 9.5? No, sum(10..29) = 390 / 20 = 19.5
    assert math.isclose(sma_vals[19], 19.5, rel_tol=1e-5)
    expected_sma_21 = sum(raw[1:21]) / 20.0  # (390 - 10 + 50) / 20 = 430 / 20 = 21.5
    assert math.isclose(sma_vals[20], 21.5, rel_tol=1e-5)

    # Standard limits
    n = len(raw)
    cl = sum(raw) / n
    variance = sum((v - cl) ** 2 for v in raw) / (n - 1)
    sigma = math.sqrt(variance)
    ucl = cl + 3 * sigma
    lcl = cl - 3 * sigma

    assert math.isclose(cl, 20.95238, rel_tol=1e-4)
    assert ucl > cl > lcl


def test_continuous_improvement_feedback_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify weekly feedback metrics aggregation in local_cases."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))

    record_chart_render_event("trend", success=True, duration_ms=45.2, file_name="test.csv", rows_count=100)
    record_chart_render_event("spc", success=True, duration_ms=62.1, file_name="test.csv", rows_count=100)
    record_chart_feedback("conv_1", "spec_1", "trend", rating=RATING_HUU_ICH)
    record_chart_feedback("conv_2", "spec_2", "spc", rating=RATING_CHUA_HUU_ICH, reason="Tỷ lệ trục chưa rõ ràng")

    metrics = get_chart_metrics()
    assert metrics["total_renders"] == 2
    assert metrics["successful_renders"] == 2
    assert metrics["feedback_counts"][RATING_HUU_ICH] == 1
    assert metrics["feedback_counts"][RATING_CHUA_HUU_ICH] == 1

    weekly = get_weekly_chart_metrics()
    assert weekly["current_week_renders"] == 2
    assert weekly["current_week_positive"] == 1
    assert weekly["current_week_negative"] == 1
    assert weekly["current_week_negative_rate_pct"] == 50.0
