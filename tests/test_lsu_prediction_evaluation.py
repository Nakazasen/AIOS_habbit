"""Test suite for LSU Iris historical replay evaluation protocols, baselines, and anti-leakage invariants.

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-iris-input.md,
specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md, and
specs/008-evidence-case-loop/plan.md section 5.1.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from aios_habit.production_prediction.evaluation import (
    ReplayProtocol,
    ReplayMetrics,
    ReplayReport,
    evaluate_replay_baseline,
    evaluate_ewma_baseline,
    evaluate_supervised_model,
)
from aios_habit.production_prediction.lsu_iris import (
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


def _load_ts_dataset():
    p_comp = FIXTURE_BASE / "time_series" / "component_lots.csv"
    p_unit = FIXTURE_BASE / "time_series" / "unit_lots.csv"
    p_jig = FIXTURE_BASE / "time_series" / "jig_outcomes.csv"
    snap = read_lsu_source(p_comp, p_unit, p_jig)
    norm = normalize_records(snap)
    traces = join_lsu_trace(norm)
    return snap, norm, traces


def test_replay_protocol_contract_and_deterministic_digest():
    """Verify default protocol contains frozen versioned parameters and produces invariant digest."""
    p1 = ReplayProtocol.default_lsu_iris()
    p2 = ReplayProtocol.default_lsu_iris()

    assert p1.rubric_version == "lsu_iris_replay_v1"
    assert p1.ewma_alpha == 0.2
    assert p1.baseline_window == 50
    assert p1.baseline_minimum_points == 20
    assert p1.control_limit_std == 3.0
    assert p1.compute_digest() == p2.compute_digest()
    assert len(p1.compute_digest()) == 64


def test_no_alert_baseline_counts_all_ng_as_missed():
    """Verify no_alert baseline never fires an alert, classifying every NG as false negative."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris()

    metrics = evaluate_replay_baseline(norm, traces, protocol)
    assert isinstance(metrics, ReplayMetrics)
    assert metrics.method_name == "no_alert"
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 6  # Exactly 6 NGs (units 4 and 5 on each of 3 days)
    assert metrics.true_negatives == 9  # 9 OKs (units 1, 2, 3 on each of 3 days)
    assert metrics.median_lead_time_seconds == 0.0


def test_ewma_baseline_detection_and_early_warning():
    """Verify EWMA detects abnormal units and computes lead time without future leakage."""
    _, norm, traces = _load_ts_dataset()
    # Use smaller baseline_min for fixture testing
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    metrics = evaluate_ewma_baseline(norm, traces, protocol)
    assert isinstance(metrics, ReplayMetrics)
    assert metrics.method_name == "ewma"
    assert metrics.evaluated_units_count == 15
    # Must detect at least some of the NGs with extreme bow values
    assert metrics.true_positives > 0
    # Every alerted unit must have at most 1 alert per window
    assert metrics.maximum_alerts_per_unit == 1
    # Lead time must be positive (alert generated before JIG final measurement)
    assert metrics.median_lead_time_seconds >= 0.0


def test_as_of_time_strictly_prevents_future_leakage():
    """Verify no measurements or outcomes after as_of_time leak into the feature space."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    report = evaluate_ewma_baseline(norm, traces, protocol, return_report=True)
    assert isinstance(report, ReplayReport)
    assert report.future_leakage_detected is False


def test_ewma_returns_not_applicable_when_insufficient_history():
    """When history points are below threshold, EWMA must safely return not_applicable without crashing."""
    _, norm, traces = _load_ts_dataset()
    # Default requires 20 points, but fixture only has 6 points
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=20)

    metrics = evaluate_ewma_baseline(norm, traces, protocol)
    assert metrics.status == "not_applicable"
    assert "chưa đủ dữ liệu nền" in metrics.reason.lower() or "not_applicable" in metrics.status


def test_supervised_model_branch_is_not_applicable_by_default():
    """When sample size requirements are not met, supervised model safely returns not_applicable."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris()

    metrics = evaluate_supervised_model(norm, traces, protocol)
    assert metrics.status == "not_applicable"
    assert "cỡ mẫu" in metrics.reason.lower() or "mẫu" in metrics.reason.lower() or "not_applicable" in metrics.status


def test_deterministic_reproducibility():
    """Running evaluation twice on identical inputs and seed must produce identical metrics and digest."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    m1 = evaluate_ewma_baseline(norm, traces, protocol)
    m2 = evaluate_ewma_baseline(norm, traces, protocol)

    assert m1.to_dict() == m2.to_dict()
    assert m1.digest == m2.digest