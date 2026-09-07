"""Test suite for LSU Iris manual shadow experimentation and resilient case linking.

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md and
specs/008-evidence-case-loop/plan.md section 5.1 & Milestone 4.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import sqlite3

from aios_habit.production_prediction.evaluation import ReplayProtocol
from aios_habit.production_prediction.lsu_iris import (
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository
from aios_habit.production_prediction.shadow import (
    ManualShadowRunner,
    ShadowOutcomeRecord,
    ShadowRiskAssessment,
    ShadowRunProgress,
    link_shadow_risk_to_workspace_case,
    record_shadow_outcome,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import WorkspaceCaseService

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


def _load_ts_dataset():
    p_comp = FIXTURE_BASE / "time_series" / "component_lots.csv"
    p_unit = FIXTURE_BASE / "time_series" / "unit_lots.csv"
    p_jig = FIXTURE_BASE / "time_series" / "jig_outcomes.csv"
    snap = read_lsu_source(p_comp, p_unit, p_jig)
    norm = normalize_records(snap)
    traces = join_lsu_trace(norm)
    return snap, norm, traces


def test_manual_shadow_runner_progress_and_safe_stop(tmp_path):
    """Verify manual shadow runner processes units in small batches and respects cancellation."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    progress_events = []

    def on_progress(p: ShadowRunProgress):
        progress_events.append(p.processed_units)

    runner = ManualShadowRunner(protocol=protocol, batch_size=5)
    result = runner.run(norm, traces, on_progress=on_progress)

    assert result.status == "completed"
    assert result.total_units == 15
    assert len(progress_events) > 0
    assert len(result.risk_assessments) > 0

    # Test stop request mid-run
    runner_stop = ManualShadowRunner(protocol=protocol, batch_size=2)
    stopped_result = runner_stop.run(norm, traces, stop_after_units=3)
    assert stopped_result.status == "stopped"
    assert stopped_result.processed_units == 3


def test_shadow_risk_idempotency_key():
    """Verify idempotency key is invariant across runs and does not depend on system wall clock."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    runner = ManualShadowRunner(protocol=protocol)
    r1 = runner.run(norm, traces)
    r2 = runner.run(norm, traces)

    k1 = [a.idempotency_key for a in r1.risk_assessments]
    k2 = [a.idempotency_key for a in r2.risk_assessments]
    assert k1 == k2
    assert len(k1) > 0


def test_as_of_time_strictly_excludes_future_outcome():
    """Verify shadow assessment feature vectors only consider measurements strictly on or before as_of_time."""
    _, norm, traces = _load_ts_dataset()
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)

    runner = ManualShadowRunner(protocol=protocol)
    result = runner.run(norm, traces)

    for assessment in result.risk_assessments:
        assert assessment.future_leakage_detected is False
        for factor in assessment.factors:
            assert factor["z_score"] >= 1.0


def test_record_missed_ng_outcome_for_unalerted_unit(tmp_path):
    """Verify recording a missed NG outcome for a unit that never received a prior risk alert."""
    pred_db = tmp_path / "pred.sqlite"
    pred_repo = ProductionPredictionRepository(pred_db)

    outcome = record_shadow_outcome(
        repository=pred_repo,
        unit_serial="SYN_UNIT_UNALERTED_099",
        target_label="NG",
        failure_code="ERR_BOW_EXCEEDED",
        confirmed_by="operator_qa_01",
        rationale="Phát hiện lỗi quang học khi kiểm tra thủ công",
        is_missed_alert=True,
    )

    assert isinstance(outcome, ShadowOutcomeRecord)
    assert outcome.unit_serial == "SYN_UNIT_UNALERTED_099"
    assert outcome.target_label == "NG"
    assert outcome.is_missed_alert is True
    assert outcome.confirmed_by == "operator_qa_01"


def test_resilient_case_linking_and_deduplication(tmp_path):
    """Verify linking a shadow risk to workspace_cases is idempotent and fault-tolerant."""
    case_db = tmp_path / "workspace_cases.sqlite"
    case_repo = WorkspaceCaseRepository(case_db)
    case_service = WorkspaceCaseService(case_repo)

    assessment = ShadowRiskAssessment(
        idempotency_key="idemp_risk_syn_unit_002",
        snapshot_id="snap_test_001",
        unit_serial="SYN_UNIT_002",
        as_of_time="2026-03-01T09:15:00+07:00",
        risk_level="HIGH",
        factors=[{"component_lot_id": "LOT_LENS_02", "metric_name": "FOCAL_LENGTH", "z_score": 3.2}],
        reason="Độ lệch thông số tiêu cự thấu kính vượt 3.0 độ lệch chuẩn",
        link_status="pending_case_link",
    )

    # First link
    c1 = link_shadow_risk_to_workspace_case(assessment, case_service)
    assert c1 is not None
    assert assessment.link_status == "linked"
    assert assessment.case_id == c1.case_id

    # Second link (idempotency check)
    c2 = link_shadow_risk_to_workspace_case(assessment, case_service)
    assert c2.case_id == c1.case_id

    # Verify case was not duplicated in repository
    cases = case_service.store.list_cases()
    matching = [c for c in cases if assessment.unit_serial in c.title or assessment.idempotency_key == c.evidence_digest]
    assert len(matching) == 1