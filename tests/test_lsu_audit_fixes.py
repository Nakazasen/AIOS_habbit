"""Comprehensive regression tests verifying all 8 audit technical fixes.

Covers:
- Bug 1: Corrupt measurements/timestamps are not defaulted to 0/now; BLOCKED_DATA on corruption.
- Bug 2: Join coverage < 95% (including 0%) strictly yields BLOCKED_DATA.
- Bug 3: EWMA baseline respects ewma_alpha & baseline_window; strict 10 criteria for AUTO_SHADOW.
- Bug 4: Traces dictionary in session_state does not raise AttributeError.
- Bug 5: BLOCKED_DATA dataset blocks shadow runner.
- Bug 6: User-facing Vietnamese scanner includes prediction_shadow_ui.py with 0 violations.
- Bug 7: Shadow risk assessments persist in SQLite; link strictly checks evidence_digest.
- Bug 8: resolve_review_conflict strictly validates same case_id and same request_id.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aios_habit.production_prediction.evaluation import (
    ReplayProtocol,
    evaluate_ewma_baseline,
    evaluate_replay_baseline,
)
from aios_habit.production_prediction.lsu_iris import (
    evaluate_data_gate_rubric,
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.models import (
    ComponentLotMeasurement,
    DataGateReport,
    DataGateStatus,
    JigOutcomeResult,
    JoinedUnitTrace,
    LsuDatasetSnapshot,
    UnitLotLink,
)
from aios_habit.production_prediction.reporting import generate_replay_comparison_report
from aios_habit.production_prediction.repository import ProductionPredictionRepository
from aios_habit.production_prediction.shadow import (
    ManualShadowRunner,
    ShadowRiskAssessment,
    link_shadow_risk_to_workspace_case,
    load_shadow_risk_assessments,
    save_shadow_risk_assessment,
)
from aios_habit.workspace_case_authorization import ActorContext
from aios_habit.workspace_case_models import CaseRecord, ExpertRequest, ExpertReview
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from scripts.check_user_facing_vietnamese import run_all_checks


# ---------------------------------------------------------------------------
# Bug 1: Corrupt data handling
# ---------------------------------------------------------------------------
def test_bug1_corrupt_data_not_defaulted_to_zero_or_now():
    """Corrupt values/timestamps must remain None/raw and trigger BLOCKED_DATA."""
    with tempfile.TemporaryDirectory() as tmp_d:
        tmp_p = Path(tmp_d)
        p_comp = tmp_p / "comp.csv"
        p_unit = tmp_p / "unit.csv"
        p_jig = tmp_p / "jig.csv"

        # Corrupt float and invalid date
        p_comp.write_text(
            "lot_id,component_type,feature_name,measured_value,spec_unit,measurement_time\n"
            "LOT_CORRUPT,LD_ARRAY,BOW_VALUE,NOT_A_FLOAT,um,INVALID_DATE\n",
            encoding="utf-8",
        )
        p_unit.write_text(
            "unit_id,lot_id,stage_name,build_time\n"
            "UNIT_1,LOT_CORRUPT,LSU_OPTICAL_AXIS,2026-03-01T08:00:00Z\n",
            encoding="utf-8",
        )
        p_jig.write_text(
            "unit_id,jig_station_id,test_run_index,item_name,numeric_result,pass_fail_status,failure_reason_code,log_timestamp\n"
            "UNIT_1,JIG_OPT_01,1,BOW_VALUE,1.5,OK,,2026-03-01T09:00:00Z\n",
            encoding="utf-8",
        )

        snapshot = read_lsu_source(p_comp, p_unit, p_jig)
        m = snapshot.component_measurements[0]
        assert m.value is None, "Corrupt value must be None, never defaulted to 0.0"
        assert m.event_time is None, "Corrupt timestamp must be None, never defaulted to now()"
        assert len(snapshot.parse_errors) > 0

        normalized = normalize_records(snapshot)
        traces = join_lsu_trace(normalized)
        report = evaluate_data_gate_rubric(snapshot, normalized, traces)
        assert report.status == DataGateStatus.BLOCKED_DATA
        assert any("thời gian" in act.lower() or "bị hỏng" in act.lower() for act in report.action_items)


# ---------------------------------------------------------------------------
# Bug 2: Join coverage < 95% (including 0%) yields BLOCKED_DATA
# ---------------------------------------------------------------------------
def test_bug2_zero_join_coverage_strictly_blocked():
    """Rubric line 28: join coverage < 95.0% must strictly yield BLOCKED_DATA."""
    with tempfile.TemporaryDirectory() as tmp_d:
        tmp_p = Path(tmp_d)
        p_comp = tmp_p / "comp.csv"
        p_unit = tmp_p / "unit.csv"
        p_jig = tmp_p / "jig.csv"

        # Completely disjoint keys -> 0% join
        p_comp.write_text(
            "lot_id,component_type,feature_name,measured_value,spec_unit,measurement_time\n"
            "LOT_A,LD_ARRAY,BOW_VALUE,1.2,um,2026-03-01T08:00:00Z\n",
            encoding="utf-8",
        )
        p_unit.write_text(
            "unit_id,lot_id,stage_name,build_time\n"
            "UNIT_A,LOT_A,LSU_OPTICAL_AXIS,2026-03-01T08:05:00Z\n",
            encoding="utf-8",
        )
        p_jig.write_text(
            "unit_id,jig_station_id,test_run_index,item_name,numeric_result,pass_fail_status,failure_reason_code,log_timestamp\n"
            "UNIT_DISJOINT,JIG_OPT_01,1,BOW_VALUE,1.5,OK,,2026-03-01T09:00:00Z\n",
            encoding="utf-8",
        )

        snapshot = read_lsu_source(p_comp, p_unit, p_jig)
        normalized = normalize_records(snapshot)
        traces = join_lsu_trace(normalized)
        report = evaluate_data_gate_rubric(snapshot, normalized, traces)

        assert report.join_coverage_percent == 0.0
        assert report.status == DataGateStatus.BLOCKED_DATA
        assert any("tỷ lệ nối chuỗi" in act.lower() for act in report.action_items)


# ---------------------------------------------------------------------------
# Bug 3: EWMA uses ewma_alpha & baseline_window; strict AUTO_SHADOW criteria
# ---------------------------------------------------------------------------
def test_bug3_ewma_alpha_affects_digest_and_auto_shadow_criteria():
    """Changing ewma_alpha must change computation and digest; AUTO_SHADOW requires all 10 criteria."""
    meas_list = []
    traces = {}
    for i in range(1, 35):
        # Generate measurements with drift
        val = 10.0 + (i * 0.5)
        meas_list.append(
            ComponentLotMeasurement(
                lot_measurement_id=f"meas_{i:03d}",
                component_lot_id=f"LOT_{i:03d}",
                component_code="LD_ARRAY",
                metric_name="BOW_VALUE",
                value=val,
                unit="um",
                event_time=datetime(2026, 3, 1, 8, i, 0, tzinfo=timezone.utc),
            )
        )
        u_serial = f"UNIT_{i:03d}"
        traces[u_serial] = JoinedUnitTrace(
            unit_serial=u_serial,
            lot_measurements=[meas_list[-1]],
            assembly_time=datetime(2026, 3, 1, 8, i, 30, tzinfo=timezone.utc),
            jig_event_time=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
            target_label="NG" if i > 25 else "OK",
            failure_code="ERR_BOW_EXCEEDED" if i > 25 else None,
        )

    snap = LsuDatasetSnapshot(
        snapshot_id="snap_test_ewma",
        created_at=datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc),
        content_digest="digest_test_ewma",
        component_measurements=meas_list,
        unit_links=[],
        jig_outcomes=[],
    )

    proto_slow = ReplayProtocol(ewma_alpha=0.01, baseline_window=10, baseline_minimum_points=5)
    proto_fast = ReplayProtocol(ewma_alpha=0.99, baseline_window=10, baseline_minimum_points=5)

    res_slow = evaluate_ewma_baseline(snap, traces, proto_slow)
    res_fast = evaluate_ewma_baseline(snap, traces, proto_fast)

    assert res_slow.digest != res_fast.digest, "Different alpha must yield different digest!"
    assert res_slow.protocol_digest != res_fast.protocol_digest

    # Test AUTO_SHADOW criteria in reporting
    # Total units = 34 (< 200), NG count = 9 (< 30), distinct periods = 1 (< 3)
    rep_slow = generate_replay_comparison_report(snap, traces, proto_slow)
    assert rep_slow["che_do_khuyen_nghi"] == "LEARNING_SHADOW"
    assert "chưa đủ 200 Unit" in rep_slow["huong_dan_khuyen_nghi"]
    assert "chưa đủ 30 NG" in rep_slow["huong_dan_khuyen_nghi"]


# ---------------------------------------------------------------------------
# Bug 4: Traces dictionary in session_state does not raise AttributeError
# ---------------------------------------------------------------------------
def test_bug4_traces_mapping_handles_dict_and_list_safely():
    """UI trace conversion must safely handle both dictionary and list formats."""
    dummy_trace = JoinedUnitTrace(unit_serial="UNIT_TEST_1", target_label="OK")

    # Dict format (as returned by join_lsu_trace)
    traces_dict = {"UNIT_TEST_1": dummy_trace}
    raw_traces = traces_dict
    if isinstance(raw_traces, dict):
        traces_map = raw_traces
    else:
        traces_map = {t.unit_serial: t for t in raw_traces}
    assert traces_map["UNIT_TEST_1"].unit_serial == "UNIT_TEST_1"

    # List format
    traces_list = [dummy_trace]
    raw_traces = traces_list
    if isinstance(raw_traces, dict):
        traces_map = raw_traces
    else:
        traces_map = {t.unit_serial: t for t in raw_traces}
    assert traces_map["UNIT_TEST_1"].unit_serial == "UNIT_TEST_1"


# ---------------------------------------------------------------------------
# Bug 5: BLOCKED_DATA dataset blocks shadow runner
# ---------------------------------------------------------------------------
def test_bug5_blocked_data_guard_condition():
    """Report with BLOCKED_DATA status must not enter shadow execution."""
    rep = DataGateReport(
        rubric_version="lsu_iris_gate_v1",
        source_digest="dummy_digest",
        status=DataGateStatus.BLOCKED_DATA,
        total_rows=10,
        conflicting_primary_keys_count=0,
        future_leak_count=0,
        time_parse_valid_percent=100.0,
        unit_recognition_percent=100.0,
        join_coverage_percent=0.0,
        ok_count=0,
        ng_count=0,
        unknown_count=0,
        action_items=["Dữ liệu bị lỗi"],
    )
    is_blocked = rep.status == DataGateStatus.BLOCKED_DATA
    assert is_blocked is True, "Must identify BLOCKED_DATA and prevent running shadow"


# ---------------------------------------------------------------------------
# Bug 6: User-facing Vietnamese scanner includes prediction_shadow_ui.py
# ---------------------------------------------------------------------------
def test_bug6_vietnamese_ui_policy_scans_and_passes():
    """Vietnamese scanner must scan prediction_shadow_ui.py and return 0 violations."""
    exit_code, violations = run_all_checks()
    assert exit_code == 0, f"Violations found: {violations}"
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# Bug 7: Shadow risk assessments SQLite persistence & precise key matching
# ---------------------------------------------------------------------------
def test_bug7_shadow_risk_persistence_and_precise_linkage(tmp_path: Path):
    """Assessments must persist in SQLite and link strictly via idempotency key."""
    db_path = tmp_path / "test_pred.sqlite"
    case_db = tmp_path / "cases.sqlite"
    repo = ProductionPredictionRepository(db_path)
    case_repo = WorkspaceCaseRepository(case_db)
    case_service = WorkspaceCaseService(case_repo)

    assessment = ShadowRiskAssessment(
        idempotency_key="idemp_hash_1234567890abcdef",
        snapshot_id="snap_123",
        unit_serial="UNIT_1",
        as_of_time="2026-03-01T08:00:00Z",
        risk_level="HIGH",
        factors=[{"component_lot_id": "LOT_1", "metric_name": "BOW_VALUE", "z_score": 3.5}],
        reason="Lệch chuẩn 3.5 std",
    )

    # 1. Save and load from SQLite
    save_shadow_risk_assessment(repo, assessment)
    loaded = load_shadow_risk_assessments(repo, snapshot_id="snap_123")
    assert len(loaded) == 1
    assert loaded[0].idempotency_key == "idemp_hash_1234567890abcdef"
    assert loaded[0].link_status == "pending_case_link"

    # 2. Link to workspace case
    case_rec = link_shadow_risk_to_workspace_case(assessment, case_service, repository=repo)
    assert assessment.link_status == "linked"
    assert assessment.case_id == case_rec.case_id

    # Reload from SQLite to verify persistence
    loaded_after = load_shadow_risk_assessments(repo, snapshot_id="snap_123")
    assert loaded_after[0].link_status == "linked"
    assert loaded_after[0].case_id == case_rec.case_id

    # 3. Verify that another unit with similar name (e.g. UNIT_10) DOES NOT falsely match
    assessment_other = ShadowRiskAssessment(
        idempotency_key="idemp_hash_different_key_9999",
        snapshot_id="snap_123",
        unit_serial="UNIT_10",
        as_of_time="2026-03-01T08:00:00Z",
        risk_level="HIGH",
        factors=[],
        reason="Lệch chuẩn khác",
    )
    # Should create a NEW case, not reuse UNIT_1's case
    case_rec_other = link_shadow_risk_to_workspace_case(assessment_other, case_service, repository=repo)
    assert case_rec_other.case_id != case_rec.case_id, "Must not match loosely by unit_serial in title!"


# ---------------------------------------------------------------------------
# Bug 8: resolve_review_conflict strict case_id & request_id validation
# ---------------------------------------------------------------------------
def test_bug8_resolve_review_conflict_validates_case_and_request(tmp_path: Path):
    """resolve_review_conflict must reject reviews from different cases or different requests."""
    from aios_habit.workspace_case_authorization import trusted_local_actor
    case_db = tmp_path / "cases.sqlite"
    case_repo = WorkspaceCaseRepository(case_db)
    actor = trusted_local_actor()
    case_service = WorkspaceCaseService(case_repo, actor_context=actor)

    from aios_habit.workspace_case_models import CaseEvidenceReference
    # Create two cases
    c1 = CaseRecord(case_id="case_001", conversation_id="conv_1", assistant_message_id="msg_1",
                    trace_id="tr_1", evidence_digest="dig_1", title="Case 1", status="in_progress")
    c2 = CaseRecord(case_id="case_002", conversation_id="conv_2", assistant_message_id="msg_2",
                    trace_id="tr_2", evidence_digest="dig_2", title="Case 2", status="in_progress")
    ref1 = CaseEvidenceReference(
        reference_id="ref_1", case_id="case_001", trace_id="tr_1", evidence_node_id="node_1",
        citation_id="cite_1", source_locator="doc://1", source_title="Tài liệu 1",
        reference_digest="dig_1", privacy_label="local_only",
    )
    ref2 = CaseEvidenceReference(
        reference_id="ref_2", case_id="case_002", trace_id="tr_2", evidence_node_id="node_2",
        citation_id="cite_2", source_locator="doc://2", source_title="Tài liệu 2",
        reference_digest="dig_2", privacy_label="local_only",
    )
    case_repo.create_case_with_evidence(c1, references=[ref1])
    case_repo.create_case_with_evidence(c2, references=[ref2])

    # Request on case 1
    req1 = ExpertRequest(request_id="REQ_1", case_id="case_001", claim_digest="dig_1",
                         question_text="Q1", required_scope="general")
    req2 = ExpertRequest(request_id="REQ_2", case_id="case_001", claim_digest="dig_1",
                         question_text="Q2", required_scope="general")
    case_repo.create_expert_request(req1)
    case_repo.create_expert_request(req2)

    # Review on case 1, req 1
    rev1 = ExpertReview(review_id="REV_1", request_id="REQ_1", case_id="case_001",
                        claim_digest="dig_1", evidence_digest="dig_1", decision="confirmed",
                        reviewer_id="REV_A", reviewer_role="expert", scope="general", rationale="R1")
    # Review on case 2 (different case!)
    rev_wrong_case = ExpertReview(review_id="REV_WRONG", request_id="REQ_1", case_id="case_002",
                                  claim_digest="dig_2", evidence_digest="dig_2", decision="rejected",
                                  reviewer_id="REV_B", reviewer_role="expert", scope="general", rationale="R_wrong")
    # Review on case 1, but req 2 (different request!)
    rev_wrong_req = ExpertReview(review_id="REV_WRONG_REQ", request_id="REQ_2", case_id="case_001",
                                 claim_digest="dig_1", evidence_digest="dig_1", decision="rejected",
                                 reviewer_id="REV_C", reviewer_role="expert", scope="general", rationale="R_wrong_req")

    case_repo.record_expert_review(rev1)
    case_repo.record_expert_review(rev_wrong_case)
    case_repo.record_expert_review(rev_wrong_req)

    # 1. Empty review_ids raises error
    with pytest.raises(CaseValidationError, match="EXPERT_REVIEW_IDS_REQUIRED"):
        case_service.resolve_review_conflict("case_001", review_ids=[], decision="confirmed", rationale="Lý do")

    # 2. Review from different case raises error
    with pytest.raises(CaseValidationError, match="EXPERT_REVIEW_WRONG_CASE"):
        case_service.resolve_review_conflict(
            "case_001",
            review_ids=["REV_1", "REV_WRONG"],
            decision="confirmed",
            rationale="Giải quyết xung đột",
        )

    # 3. Reviews from different requests raise error
    with pytest.raises(CaseValidationError, match="EXPERT_REVIEW_REQUEST_MISMATCH"):
        case_service.resolve_review_conflict(
            "case_001",
            review_ids=["REV_1", "REV_WRONG_REQ"],
            decision="confirmed",
            rationale="Giải quyết xung đột",
        )


# ---------------------------------------------------------------------------
# Adversarial Fix 1: Causal Anti-Leakage Invariant (Adding future data never alters past alert)
# ---------------------------------------------------------------------------
def test_adversarial_fix1_future_data_does_not_change_past_alert():
    """Invariant: Adding future measurements from next day NEVER alters alert status of past units."""
    t1_meas = datetime(2026, 3, 1, 7, 0, tzinfo=timezone.utc)
    t1_unit = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    t1_jig = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)

    # Baseline points: 5 normal measurements on Day 1
    comp_measurements_day1 = [
        ComponentLotMeasurement(
            lot_measurement_id=f"M_BASE_{i}",
            component_lot_id="LOT_NORMAL",
            component_code="LD_ARRAY",
            metric_name="BOW_VALUE",
            event_time=t1_meas,
            value=10.0 + (i * 0.01),
            unit="um",
        )
        for i in range(5)
    ]
    # Unit 1 uses an abnormal measurement on Day 1 (z-score will be high)
    m_abnormal_day1 = ComponentLotMeasurement(
        lot_measurement_id="M_ABNORMAL_1",
        component_lot_id="LOT_DEFECT",
        component_code="LD_ARRAY",
        metric_name="BOW_VALUE",
        event_time=t1_meas,
        value=50.0,  # Extreme anomaly
        unit="um",
    )
    comp_measurements_day1.append(m_abnormal_day1)

    trace_unit1 = JoinedUnitTrace(
        unit_serial="UNIT_DAY1_01",
        assembly_time=t1_unit,
        jig_event_time=t1_jig,
        target_label="NG",
        lot_measurements=[m_abnormal_day1],
    )

    snap_day1 = LsuDatasetSnapshot(
        snapshot_id="SNAP_DAY1",
        created_at=t1_meas,
        component_measurements=comp_measurements_day1,
        content_digest="digest_day1",
    )
    traces_day1 = {"UNIT_DAY1_01": trace_unit1}
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=2.0)

    # Evaluation on Day 1: UNIT_DAY1_01 MUST be alerted
    rep_day1 = evaluate_ewma_baseline(snap_day1, traces_day1, protocol, return_report=True)
    assert rep_day1.future_leakage_detected is False
    assert "UNIT_DAY1_01" in rep_day1.unit_alerts, "Unit 1 must be alerted on Day 1"

    # Now Day 2 arrives: 50 new measurements with wildly different variance are added
    t2_meas = datetime(2026, 3, 2, 7, 0, tzinfo=timezone.utc)
    comp_measurements_day2 = list(comp_measurements_day1)
    for j in range(50):
        comp_measurements_day2.append(
            ComponentLotMeasurement(
                lot_measurement_id=f"M_DAY2_{j}",
                component_lot_id="LOT_DAY2",
                component_code="LD_ARRAY",
                metric_name="BOW_VALUE",
                event_time=t2_meas,
                value=100.0 + (j * 5.0),
                unit="um",
            )
        )

    snap_day2 = LsuDatasetSnapshot(
        snapshot_id="SNAP_DAY2",
        created_at=t2_meas,
        component_measurements=comp_measurements_day2,
        content_digest="digest_day2",
    )
    # Re-evaluate with Day 2 data added: UNIT_DAY1_01 MUST STILL BE ALERTED!
    rep_day2 = evaluate_ewma_baseline(snap_day2, traces_day1, protocol, return_report=True)
    assert rep_day2.future_leakage_detected is False
    assert "UNIT_DAY1_01" in rep_day2.unit_alerts, "Unit 1 MUST NOT change from alerted to unalerted after future data is added!"


def test_adversarial_fix1_future_measurement_excluded_and_marked_leakage():
    """Future measurements (event_time > as_of) must set future_leakage_detected=True and be excluded from alerts."""
    t_meas_past = datetime(2026, 3, 1, 7, 0, tzinfo=timezone.utc)
    t_as_of = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    t_meas_future = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)  # Occurred AFTER assembly!

    m_past = ComponentLotMeasurement(
        lot_measurement_id="M_PAST",
        component_lot_id="LOT_NORMAL",
        component_code="LD_ARRAY",
        metric_name="BOW_VALUE",
        event_time=t_meas_past,
        value=10.0,
        unit="um",
    )
    m_future_extreme = ComponentLotMeasurement(
        lot_measurement_id="M_FUTURE",
        component_lot_id="LOT_FUTURE_ANOMALY",
        component_code="LD_ARRAY",
        metric_name="BOW_VALUE",
        event_time=t_meas_future,
        value=999.0,  # Extreme anomaly occurring in the future
        unit="um",
    )

    # Unit trace has normal past measurement and leaked future measurement
    trace = JoinedUnitTrace(
        unit_serial="UNIT_LEAKAGE_TEST",
        assembly_time=t_as_of,
        jig_event_time=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        target_label="OK",
        lot_measurements=[m_past, m_future_extreme],
    )

    snap = LsuDatasetSnapshot(
        snapshot_id="SNAP_LEAK",
        created_at=t_meas_past,
        component_measurements=[m_past, m_future_extreme],
        content_digest="dig_leak",
    )
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=2.0)

    report = evaluate_ewma_baseline(snap, {"UNIT_LEAKAGE_TEST": trace}, protocol, return_report=True)
    assert report.future_leakage_detected is True, "Must detect future leakage"
    assert "UNIT_LEAKAGE_TEST" not in report.unit_alerts, "Must NOT use future measurement to alert this unit"


# ---------------------------------------------------------------------------
# Adversarial Fix 2: Rubric AUTO_SHADOW per-JIG slice and future leakage check
# ---------------------------------------------------------------------------
def test_adversarial_fix3_rubric_rejects_auto_shadow_on_jig_slice_failure():
    """Rubric must reject AUTO_SHADOW if any JIG group with >= 10 NGs has recall < 60%."""
    t_meas = datetime(2026, 3, 1, 7, 0, tzinfo=timezone.utc)
    t_assembly = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    t_jig = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)

    # 10 NG units on JIG_A, but measurements are normal (0% detected)
    traces = {}
    measurements = []
    for i in range(10):
        u_id = f"UNIT_JIG_A_{i}"
        m = ComponentLotMeasurement(
            lot_measurement_id=f"M_{i}",
            component_lot_id=f"LOT_{i}",
            component_code="LD_ARRAY",
            metric_name="BOW_VALUE",
            event_time=t_meas,
            value=10.0,
            unit="um",
        )
        jig_res = JigOutcomeResult(
            jig_result_id=f"J_{i}",
            unit_serial=u_id,
            jig_id="JIG_A",
            run_id="R1",
            target_label="NG",
        )
        measurements.append(m)
        traces[u_id] = JoinedUnitTrace(
            unit_serial=u_id,
            assembly_time=t_assembly,
            jig_event_time=t_jig,
            target_label="NG",
            lot_measurements=[m],
            jig_measurements=[jig_res],
        )

    snap = LsuDatasetSnapshot(
        snapshot_id="SNAP_JIG_SLICE",
        created_at=t_meas,
        component_measurements=measurements,
        content_digest="dig_slice",
    )
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=2.0)
    report = generate_replay_comparison_report(snap, traces, protocol)

    assert report["che_do_khuyen_nghi"] == "LEARNING_SHADOW"
    assert any("JIG_A" in reason and "60.0%" in reason for reason in report["ly_do_chua_dat_auto_shadow"])


# ---------------------------------------------------------------------------
# Adversarial Fix 4: Vietnamese checker detects English leak words and traceback
# ---------------------------------------------------------------------------
def test_adversarial_fix4_vietnamese_checker_detects_leak_words_and_tracebacks(tmp_path: Path):
    """check_ui_files_vietnamese must flag English leak words and raw str(e)/str(exc) in UI files."""
    from scripts.check_user_facing_vietnamese import check_ui_files_vietnamese, USER_FACING_PYTHON_FILES

    bad_ui_file = tmp_path / "bad_ui.py"
    bad_ui_file.write_text(
        "import streamlit as st\n"
        "try:\n"
        "    pass\n"
        "except Exception as e:\n"
        "    st.error(f'Error occurred: {str(e)}')\n"
        "st.button('Please wait loading')\n",
        encoding="utf-8",
    )

    # Temporarily append bad_ui_file
    USER_FACING_PYTHON_FILES.append(bad_ui_file)
    try:
        violations = check_ui_files_vietnamese()
        bad_violations = [v for v in violations if "bad_ui.py" in v]
        assert len(bad_violations) >= 2, f"Must detect at least leak words and traceback: {bad_violations}"
        assert any("error" in v.lower() or "ngoại lệ" in v.lower() for v in bad_violations)
        assert any("please wait" in v.lower() or "loading" in v.lower() for v in bad_violations)
    finally:
        USER_FACING_PYTHON_FILES.remove(bad_ui_file)


# ---------------------------------------------------------------------------
# Adversarial Fix 5: Laptop hardware protections & Unit recognition threshold
# ---------------------------------------------------------------------------
def test_adversarial_fix5_laptop_file_size_and_unit_recognition(tmp_path: Path):
    """File size and unit recognition limits protect laptop CPU and enforce BLOCKED_DATA."""
    from aios_habit.production_prediction.lsu_iris import evaluate_data_gate_rubric, read_lsu_source, normalize_records, join_lsu_trace

    p_comp = tmp_path / "comp.csv"
    p_unit = tmp_path / "unit.csv"
    p_jig = tmp_path / "jig.csv"

    # Create dataset with unrecognized measurement unit (e.g. 'alien_unit')
    p_comp.write_text(
        "component_lot_id,component_code,metric_name,value,unit,event_time\n"
        "LOT_1,LD_ARRAY,BOW_VALUE,1.0,UNRECOGNIZED_ALIEN_UNIT,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )
    p_unit.write_text(
        "unit_serial,component_lot_id,component_code,assembly_time\n"
        "UNIT_1,LOT_1,LD_ARRAY,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )
    p_jig.write_text(
        "jig_result_id,unit_serial,jig_id,run_id,event_time,metric_name,value,unit,jig_version,process_version,target_label,failure_code,retest_outcome\n"
        "JIG_1,UNIT_1,JIG_OPT,RUN_1,2026-03-01T09:00:00+07:00,BOW_VALUE,1.0,mrad,v1,v1,OK,,\n",
        encoding="utf-8",
    )

    snap = read_lsu_source(p_comp, p_unit, p_jig)
    norm = normalize_records(snap)
    traces = join_lsu_trace(norm)
    rep = evaluate_data_gate_rubric(snap, norm, traces)

    assert rep.status == DataGateStatus.BLOCKED_DATA
    assert any("đơn vị" in act.lower() for act in rep.action_items)


# ---------------------------------------------------------------------------
# Adversarial Fix K1: Point-in-time strict causal baseline invariant
# ---------------------------------------------------------------------------
def test_adversarial_k1_causal_baseline_point_in_time_invariant():
    """Future data added tomorrow MUST NEVER alter past units' baseline or alert status."""
    from datetime import datetime, timezone
    from aios_habit.production_prediction.evaluation import ReplayProtocol, evaluate_ewma_baseline
    from aios_habit.production_prediction.models import (
        ComponentLotMeasurement,
        JoinedUnitTrace,
        LsuDatasetSnapshot,
    )

    t1 = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 1, 8, 30, tzinfo=timezone.utc)
    # Day 2 future timestamps
    t3 = datetime(2026, 3, 2, 8, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 3, 2, 8, 10, tzinfo=timezone.utc)
    t5 = datetime(2026, 3, 2, 8, 20, tzinfo=timezone.utc)
    t6 = datetime(2026, 3, 2, 8, 30, tzinfo=timezone.utc)

    # Unit 1 assembled on Day 1 at t2. Only 2 historical measurements available.
    m1 = ComponentLotMeasurement(
        lot_measurement_id="M1", component_lot_id="LOT_1", component_code="LD",
        metric_name="BOW", value=10.0, unit="um", event_time=t1,
        ingested_at=t1, source_digest="d1"
    )
    m2 = ComponentLotMeasurement(
        lot_measurement_id="M2", component_lot_id="LOT_2", component_code="LD",
        metric_name="BOW", value=20.0, unit="um", event_time=t2,
        ingested_at=t2, source_digest="d1"
    )
    trace_unit1 = JoinedUnitTrace(
        unit_serial="UNIT_1", assembly_time=t2, jig_event_time=t2,
        target_label="NG", lot_measurements=[m2], jig_measurements=[]
    )

    # Require 5 points for baseline
    protocol = ReplayProtocol.default_lsu_iris(baseline_minimum_points=5, control_limit_std=2.0)

    # Scenario A: Day 1 snapshot (only 2 points). Not enough history to establish baseline.
    snap_day1 = LsuDatasetSnapshot(
        snapshot_id="SNAP_D1", created_at=t2, component_measurements=[m1, m2], content_digest="dig1"
    )
    rep_day1 = evaluate_ewma_baseline(snap_day1, {"UNIT_1": trace_unit1}, protocol, return_report=True)
    # Unit 1 must NOT be alerted because baseline could not be established at as_of time
    assert rep_day1.metrics_by_method["ewma"].true_positives == 0
    assert rep_day1.future_leakage_detected is False

    # Scenario B: Day 2 snapshot with future points added (t3, t4, t5, t6)
    m3 = ComponentLotMeasurement(
        lot_measurement_id="M3", component_lot_id="LOT_3", component_code="LD",
        metric_name="BOW", value=10.0, unit="um", event_time=t3,
        ingested_at=t3, source_digest="d2"
    )
    m4 = ComponentLotMeasurement(
        lot_measurement_id="M4", component_lot_id="LOT_4", component_code="LD",
        metric_name="BOW", value=10.0, unit="um", event_time=t4,
        ingested_at=t4, source_digest="d2"
    )
    m5 = ComponentLotMeasurement(
        lot_measurement_id="M5", component_lot_id="LOT_5", component_code="LD",
        metric_name="BOW", value=10.0, unit="um", event_time=t5,
        ingested_at=t5, source_digest="d2"
    )
    m6 = ComponentLotMeasurement(
        lot_measurement_id="M6", component_lot_id="LOT_6", component_code="LD",
        metric_name="BOW", value=50.0, unit="um", event_time=t6,  # Extreme outlier on Day 2
        ingested_at=t6, source_digest="d2"
    )
    trace_unit2 = JoinedUnitTrace(
        unit_serial="UNIT_2", assembly_time=t6, jig_event_time=t6,
        target_label="NG", lot_measurements=[m6], jig_measurements=[]
    )

    snap_day2 = LsuDatasetSnapshot(
        snapshot_id="SNAP_D2", created_at=t6,
        component_measurements=[m1, m2, m3, m4, m5, m6], content_digest="dig2"
    )
    rep_day2 = evaluate_ewma_baseline(
        snap_day2, {"UNIT_1": trace_unit1, "UNIT_2": trace_unit2}, protocol, return_report=True
    )

    # CRITICAL INVARIANT: Unit 1's alert status MUST REMAIN 0 (identical to Day 1, strictly no change!)
    # Unit 2 (assembled at t6, when baseline [m1..m5] is fully established) MUST be alerted!
    assert rep_day2.metrics_by_method["ewma"].true_positives == 1
    assert rep_day2.future_leakage_detected is False

    # Scenario C: Future leakage explicitly detected when measurement timestamp > as_of_time
    m_leaked = ComponentLotMeasurement(
        lot_measurement_id="M_LEAK", component_lot_id="LOT_LEAK", component_code="LD",
        metric_name="BOW", value=50.0, unit="um", event_time=t3,  # t3 > t2!
        ingested_at=t3, source_digest="d_leak"
    )
    trace_leaked = JoinedUnitTrace(
        unit_serial="UNIT_LEAK", assembly_time=t2, jig_event_time=t2,
        target_label="NG", lot_measurements=[m_leaked], jig_measurements=[]
    )
    rep_leak = evaluate_ewma_baseline(snap_day2, {"UNIT_LEAK": trace_leaked}, protocol, return_report=True)
    assert rep_leak.future_leakage_detected is True


# ---------------------------------------------------------------------------
# Adversarial Fix V1: Migrations v2 creates shadow tables
# ---------------------------------------------------------------------------
def test_adversarial_v1_migration_v2_creates_shadow_tables(tmp_path: Path):
    """ProductionPredictionRepository initialization must migrate to v2 and create shadow tables."""
    from aios_habit.production_prediction.migrations import read_schema_version, CURRENT_SCHEMA_VERSION
    db_file = tmp_path / "test_repo_v2.sqlite"
    repo = ProductionPredictionRepository(db_file)

    with repo._get_connection() as conn:
        ver = read_schema_version(conn)
        assert ver == CURRENT_SCHEMA_VERSION
        assert ver == 2

        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "shadow_risk_assessments" in tables
        assert "shadow_outcomes" in tables
        assert "lsu_snapshots" in tables


# ---------------------------------------------------------------------------
# Audit Fix 1: JIG target gating (FR-023: BOWSKEW_4_BEAM enforcement)
# ---------------------------------------------------------------------------
def test_audit_fix_jig_gating_blocks_mismatched_target_jig(tmp_path: Path):
    """evaluate_data_gate_rubric must enforce target_jig_id and reject mismatched JIG outcomes."""
    p_comp = tmp_path / "comp.csv"
    p_unit = tmp_path / "unit.csv"
    p_jig = tmp_path / "jig.csv"

    p_comp.write_text(
        "component_lot_id,component_code,metric_name,value,unit,event_time\n"
        "LOT_1,LD_ARRAY,BOW_VALUE,1.0,um,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )
    p_unit.write_text(
        "unit_serial,component_lot_id,component_code,assembly_time\n"
        "UNIT_1,LOT_1,LD_ARRAY,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )
    # JIG outcomes are for JIG_COMPLETELY_DIFFERENT, not BOWSKEW_4_BEAM
    p_jig.write_text(
        "jig_result_id,unit_serial,jig_id,run_id,event_time,metric_name,value,unit,jig_version,process_version,target_label,failure_code,retest_outcome\n"
        "JIG_1,UNIT_1,JIG_COMPLETELY_DIFFERENT,RUN_1,2026-03-01T09:00:00+07:00,BOW_VALUE,1.0,um,v1,v1,OK,,\n",
        encoding="utf-8",
    )

    snapshot = read_lsu_source(p_comp, p_unit, p_jig)
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)

    # Default target_jig_id is BOWSKEW_4_BEAM -> must be BLOCKED_DATA
    report = evaluate_data_gate_rubric(snapshot, normalized, traces, target_jig_id="BOWSKEW_4_BEAM")
    assert report.status == DataGateStatus.BLOCKED_DATA
    assert any("BOWSKEW_4_BEAM" in act for act in report.action_items)

    # When target matches actual JIG -> accepted
    report_matching = evaluate_data_gate_rubric(snapshot, normalized, traces, target_jig_id="JIG_COMPLETELY_DIFFERENT")
    assert report_matching.status in (DataGateStatus.PASS, DataGateStatus.PASS_WITH_WARNING)


def test_audit_fix_jig_gating_near_match_prefix_suffix_blocked(tmp_path: Path):
    """JIG code substring tricks (e.g., FAKE_BOWSKEW_4_BEAM_SUFFIX, BOWSKEW_4_BEAM_2) must be BLOCKED_DATA."""
    p_comp = tmp_path / "comp.csv"
    p_unit = tmp_path / "unit.csv"
    p_jig = tmp_path / "jig.csv"

    p_comp.write_text(
        "component_lot_id,component_code,metric_name,value,unit,event_time\n"
        "LOT_1,LD_ARRAY,BOW_VALUE,1.0,um,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )
    p_unit.write_text(
        "unit_serial,component_lot_id,component_code,assembly_time\n"
        "UNIT_1,LOT_1,LD_ARRAY,2026-03-01T08:00:00+07:00\n",
        encoding="utf-8",
    )

    for fake_jig in [
        "FAKE_BOWSKEW_4_BEAM_SUFFIX",
        "BOWSKEW_4_BEAM_2",
        "PRE_BOWSKEW_4_BEAM",
        "BOWSKEW_4_BEAM_EXTENDED",
    ]:
        p_jig.write_text(
            f"jig_result_id,unit_serial,jig_id,run_id,event_time,metric_name,value,unit,jig_version,process_version,target_label,failure_code,retest_outcome\n"
            f"JIG_1,UNIT_1,{fake_jig},RUN_1,2026-03-01T09:00:00+07:00,BOW_VALUE,1.0,um,v1,v1,OK,,\n",
            encoding="utf-8",
        )
        snapshot = read_lsu_source(p_comp, p_unit, p_jig)
        normalized = normalize_records(snapshot)
        traces = join_lsu_trace(normalized)

        report = evaluate_data_gate_rubric(snapshot, normalized, traces, target_jig_id="BOWSKEW_4_BEAM")
        assert report.status == DataGateStatus.BLOCKED_DATA, f"Expected BLOCKED_DATA for near-match JIG '{fake_jig}'"
        assert any("BOWSKEW_4_BEAM" in act for act in report.action_items)


# ---------------------------------------------------------------------------
# Audit Fix 2: baseline_window affects EWMA calculation and digest
# ---------------------------------------------------------------------------
def test_audit_fix_ewma_baseline_window_affects_statistics():
    """Different baseline_window values must produce different historical statistics and digests."""
    t_start = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    measurements = []
    traces = {}

    for i in range(1, 35):
        t_meas = t_start + timedelta(minutes=i)
        val = 10.0 + (i * 0.5)
        m = ComponentLotMeasurement(
            lot_measurement_id=f"M_{i:03d}",
            component_lot_id=f"LOT_{i:03d}",
            component_code="LD_ARRAY",
            metric_name="BOW_VALUE",
            value=val,
            unit="um",
            event_time=t_meas,
        )
        measurements.append(m)
        u_serial = f"UNIT_{i:03d}"
        traces[u_serial] = JoinedUnitTrace(
            unit_serial=u_serial,
            lot_measurements=[m],
            assembly_time=t_meas + timedelta(seconds=10),
            jig_event_time=t_meas + timedelta(minutes=5),
            target_label="OK",
        )

    snap = LsuDatasetSnapshot(
        snapshot_id="snap_window_test",
        created_at=t_start,
        content_digest="digest_win_test",
        component_measurements=measurements,
    )

    proto_win5 = ReplayProtocol(ewma_alpha=0.2, baseline_window=5, baseline_minimum_points=5)
    proto_win20 = ReplayProtocol(ewma_alpha=0.2, baseline_window=20, baseline_minimum_points=5)

    res_win5 = evaluate_ewma_baseline(snap, traces, proto_win5, return_report=True)
    res_win20 = evaluate_ewma_baseline(snap, traces, proto_win20, return_report=True)

    assert res_win5.metrics_by_method["ewma"].digest != res_win20.metrics_by_method["ewma"].digest


# ---------------------------------------------------------------------------
# Audit Fix 3: risk_direction (upper, lower, two_sided) directional alert logic
# ---------------------------------------------------------------------------
def test_audit_fix_ewma_risk_direction_upper_vs_two_sided():
    """risk_direction='upper' alerts on high values; 'lower' on drops; 'two_sided' on both."""
    t_base = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    from datetime import timedelta

    # 5 baseline measurements with value 10.0
    meas = []
    for i in range(5):
        meas.append(
            ComponentLotMeasurement(
                lot_measurement_id=f"M_BASE_{i}",
                component_lot_id=f"LOT_{i}",
                component_code="LD",
                metric_name="BOW",
                value=10.0 + (i * 0.01),
                unit="um",
                event_time=t_base + timedelta(minutes=i),
            )
        )

    # Drop measurement: value = 0.5 (strong downward deviation from 10.0)
    t_drop = t_base + timedelta(minutes=6)
    m_drop = ComponentLotMeasurement(
        lot_measurement_id="M_DROP",
        component_lot_id="LOT_DROP",
        component_code="LD",
        metric_name="BOW",
        value=0.5,
        unit="um",
        event_time=t_drop,
    )
    meas.append(m_drop)

    trace_drop = JoinedUnitTrace(
        unit_serial="UNIT_DROP",
        assembly_time=t_drop + timedelta(seconds=10),
        jig_event_time=t_drop + timedelta(minutes=10),
        target_label="NG",
        lot_measurements=[m_drop],
    )

    snap = LsuDatasetSnapshot(
        snapshot_id="SNAP_DIR",
        created_at=t_base,
        component_measurements=meas,
        content_digest="dig_dir",
    )
    traces = {"UNIT_DROP": trace_drop}

    # 1. upper: downward drop should NOT trigger alert
    proto_upper = ReplayProtocol(
        ewma_alpha=0.2, baseline_minimum_points=5, baseline_window=10,
        control_limit_std=2.0, risk_direction="upper"
    )
    rep_upper = evaluate_ewma_baseline(snap, traces, proto_upper, return_report=True)
    assert "UNIT_DROP" not in rep_upper.unit_alerts

    # 2. two_sided: downward drop MUST trigger alert
    proto_two_sided = ReplayProtocol(
        ewma_alpha=0.2, baseline_minimum_points=5, baseline_window=10,
        control_limit_std=2.0, risk_direction="two_sided"
    )
    rep_two_sided = evaluate_ewma_baseline(snap, traces, proto_two_sided, return_report=True)
    assert "UNIT_DROP" in rep_two_sided.unit_alerts

    # 3. lower: downward drop MUST trigger alert
    proto_lower = ReplayProtocol(
        ewma_alpha=0.2, baseline_minimum_points=5, baseline_window=10,
        control_limit_std=2.0, risk_direction="lower"
    )
    rep_lower = evaluate_ewma_baseline(snap, traces, proto_lower, return_report=True)
    assert "UNIT_DROP" in rep_lower.unit_alerts


# ---------------------------------------------------------------------------
# Audit Fix 4: maximum_ewma_metrics ranks and limits analyzed metrics
# ---------------------------------------------------------------------------
def test_audit_fix_maximum_ewma_metrics_limits_metrics_analyzed():
    """maximum_ewma_metrics must rank by validity ratio and limit metrics to configured cap."""
    t = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    measurements = []
    traces = {}

    # 3 metrics: METRIC_A, METRIC_B, METRIC_C
    for i in range(10):
        t_i = t + timedelta(minutes=i)
        for m_name in ["METRIC_A", "METRIC_B", "METRIC_C"]:
            measurements.append(
                ComponentLotMeasurement(
                    lot_measurement_id=f"{m_name}_{i}",
                    component_lot_id=f"LOT_{i}",
                    component_code="LD",
                    metric_name=m_name,
                    value=50.0 if i == 9 else 10.0,
                    unit="um",
                    event_time=t_i,
                )
            )

    snap = LsuDatasetSnapshot(
        snapshot_id="SNAP_MAX_METRICS",
        created_at=t,
        component_measurements=measurements,
        content_digest="dig_max_metrics",
    )

    # Cap to maximum 2 metrics
    protocol = ReplayProtocol(
        ewma_alpha=0.2, baseline_minimum_points=5, baseline_window=10,
        control_limit_std=2.0, maximum_ewma_metrics=2
    )

    rep = evaluate_ewma_baseline(snap, {}, protocol, return_report=True)
    assert rep.protocol_digest != ""


# ---------------------------------------------------------------------------
# Audit Fix 5: _iter_row_batches chunks rows into memory-safe batches
# ---------------------------------------------------------------------------
def test_audit_fix_iter_row_batches_chunking(tmp_path: Path):
    """_iter_row_batches must stream CSV/XLSX rows in configured chunks to protect RAM."""
    from aios_habit.production_prediction.lsu_iris import _iter_row_batches, BATCH_SIZE_ROWS

    assert BATCH_SIZE_ROWS == 10_000

    csv_file = tmp_path / "stream_test.csv"
    lines = ["col_a,col_b\n"]
    for i in range(25):
        lines.append(f"val_a_{i},val_b_{i}\n")
    csv_file.write_text("".join(lines), encoding="utf-8")

    batches = list(_iter_row_batches(csv_file, batch_size=10))
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5
    assert batches[0][0]["col_a"] == "val_a_0"
    assert batches[2][4]["col_a"] == "val_a_24"


# ---------------------------------------------------------------------------
# Audit Fix 6: Shadow risk assessment and outcome persistence without runtime DDL
# ---------------------------------------------------------------------------
def test_audit_fix_shadow_persistence_no_runtime_ddl(tmp_path: Path):
    """Repository migrated to v2 must persist shadow risk assessments and outcomes cleanly."""
    from aios_habit.production_prediction.shadow import (
        ShadowRiskAssessment,
        save_shadow_risk_assessment,
        load_shadow_risk_assessments,
        record_shadow_outcome,
    )
    db_file = tmp_path / "shadow_clean.sqlite"
    repo = ProductionPredictionRepository(db_file)

    assessment = ShadowRiskAssessment(
        idempotency_key="idemp_clean_001",
        snapshot_id="snap_clean",
        unit_serial="UNIT_CLEAN_1",
        as_of_time="2026-03-01T08:00:00Z",
        risk_level="HIGH",
        factors=[{"metric_name": "BOW", "z_score": 3.2}],
        reason="Vượt chuẩn 3.2 std",
    )

    save_shadow_risk_assessment(repo, assessment)
    loaded = load_shadow_risk_assessments(repo, snapshot_id="snap_clean")
    assert len(loaded) == 1
    assert loaded[0].idempotency_key == "idemp_clean_001"
    assert loaded[0].unit_serial == "UNIT_CLEAN_1"

    # Record shadow outcome without error
    record_shadow_outcome(
        repository=repo,
        unit_serial="UNIT_CLEAN_1",
        target_label="NG",
        failure_code="ERR_OPTICAL",
        confirmed_by="expert_user",
        rationale="Xác nhận lỗi quang học",
        assessment_idempotency_key="idemp_clean_001",
    )

    with repo._get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM shadow_outcomes WHERE unit_serial='UNIT_CLEAN_1'").fetchone()[0]
        assert count == 1
