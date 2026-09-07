"""Test suite for LSU Iris replay reporting and Vietnamese presentation."""

from __future__ import annotations

from pathlib import Path
import pytest

from aios_habit.production_prediction.evaluation import ReplayProtocol
from aios_habit.production_prediction.lsu_iris import (
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.reporting import (
    generate_replay_comparison_report,
    render_report_markdown,
)

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


def test_generate_replay_comparison_report_and_deterministic_digest():
    """Verify comparison report produces deterministic digest and all Vietnamese sections."""
    p_comp = FIXTURE_BASE / "time_series" / "component_lots.csv"
    p_unit = FIXTURE_BASE / "time_series" / "unit_lots.csv"
    p_jig = FIXTURE_BASE / "time_series" / "jig_outcomes.csv"

    snap = read_lsu_source(p_comp, p_unit, p_jig)
    norm = normalize_records(snap)
    traces = join_lsu_trace(norm)

    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    report1 = generate_replay_comparison_report(norm, traces, protocol)
    report2 = generate_replay_comparison_report(norm, traces, protocol)

    assert report1["tong_so_unit"] == 15
    assert report1["so_unit_dat_ok"] == 9
    assert report1["so_unit_loi_ng"] == 6
    assert len(report1["so_sanh_phuong_an"]) == 3
    assert report1["che_do_khuyen_nghi"] in ("AUTO_SHADOW", "LEARNING_SHADOW")

    # Invariant digest check
    assert report1["bao_cao_digest"] == report2["bao_cao_digest"]
    assert len(report1["bao_cao_digest"]) == 64


def test_render_report_markdown_is_safe_vietnamese():
    """Verify markdown report contains no system paths, internal traceback, or unhandled errors."""
    p_comp = FIXTURE_BASE / "time_series" / "component_lots.csv"
    p_unit = FIXTURE_BASE / "time_series" / "unit_lots.csv"
    p_jig = FIXTURE_BASE / "time_series" / "jig_outcomes.csv"

    snap = read_lsu_source(p_comp, p_unit, p_jig)
    norm = normalize_records(snap)
    traces = join_lsu_trace(norm)

    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)
    report = generate_replay_comparison_report(norm, traces, protocol)
    md = render_report_markdown(report)

    assert "# Báo cáo phát lại lịch sử đánh giá cảnh báo sớm LSU Iris" in md
    assert "Không phát cảnh báo" in md
    assert "EWMA" in md
    assert "Mô hình học máy" in md

    # Safety checks
    assert "Traceback" not in md
    assert "Exception" not in md
    assert "D:\\" not in md
    assert "C:\\" not in md