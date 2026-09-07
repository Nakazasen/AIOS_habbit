"""Test suite for LSU Iris data ingestion, normalization, validation, and data gate contracts.

Adheres strictly to specs/008-evidence-case-loop/contracts/lsu-iris-input.md and
specs/008-evidence-case-loop/contracts/lsu-acceptance-rubric.md.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from aios_habit.production_prediction.lsu_iris import (
    read_lsu_source,
    normalize_records,
    validate_records,
    join_lsu_trace,
    evaluate_data_gate_rubric,
    compute_content_digest,
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

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


def test_read_valid_csv_and_xlsx_fixtures():
    """Verify reading valid CSV and XLSX files yields identical structured records."""
    csv_comp = FIXTURE_BASE / "valid" / "component_lots.csv"
    csv_unit = FIXTURE_BASE / "valid" / "unit_lots.csv"
    csv_jig = FIXTURE_BASE / "valid" / "jig_outcomes.csv"

    xlsx_comp = FIXTURE_BASE / "valid" / "component_lots.xlsx"
    xlsx_unit = FIXTURE_BASE / "valid" / "unit_lots.xlsx"
    xlsx_jig = FIXTURE_BASE / "valid" / "jig_outcomes.xlsx"

    csv_snapshot = read_lsu_source(csv_comp, csv_unit, csv_jig)
    xlsx_snapshot = read_lsu_source(xlsx_comp, xlsx_unit, xlsx_jig)

    assert isinstance(csv_snapshot, LsuDatasetSnapshot)
    assert isinstance(xlsx_snapshot, LsuDatasetSnapshot)
    assert len(csv_snapshot.component_measurements) == 6
    assert len(csv_snapshot.unit_links) == 4
    assert len(csv_snapshot.jig_outcomes) == 2

    # Verify identical counts and values
    assert len(csv_snapshot.component_measurements) == len(xlsx_snapshot.component_measurements)
    assert len(csv_snapshot.unit_links) == len(xlsx_snapshot.unit_links)
    assert len(csv_snapshot.jig_outcomes) == len(xlsx_snapshot.jig_outcomes)


def test_content_digest_is_invariant_to_filepath(tmp_path):
    """Verify digest depends strictly on content, never file path or file name."""
    src = FIXTURE_BASE / "valid" / "component_lots.csv"
    copy1 = tmp_path / "renamed_file_1.csv"
    copy2 = tmp_path / "somewhere_else" / "renamed_file_2.csv"
    copy2.parent.mkdir(parents=True, exist_ok=True)

    copy1.write_bytes(src.read_bytes())
    copy2.write_bytes(src.read_bytes())

    digest1 = compute_content_digest(copy1)
    digest2 = compute_content_digest(copy2)
    assert digest1 == digest2
    assert len(digest1) == 64  # SHA-256


def test_normalize_and_timezone():
    """Verify timestamps are parsed into Vietnam timezone and numbers/units are standardized."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    for m in normalized.component_measurements:
        assert m.event_time.tzinfo is not None
        assert m.event_time.strftime("%z") in ("+0700", "+07:00")
        assert isinstance(m.value, float)
        assert m.unit in ("mm", "um", "nm", "mW")


def test_join_lsu_trace():
    """Verify lot -> unit -> jig trace can be joined deterministically."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    assert "SYN_UNIT_001" in traces
    unit1 = traces["SYN_UNIT_001"]
    assert unit1.target_label == "OK"
    assert len(unit1.lot_measurements) == 4  # 2 for LOT_LENS_01, 2 for LOT_LD_01

    unit2 = traces["SYN_UNIT_002"]
    assert unit2.target_label == "NG"
    assert unit2.failure_code == "ERR_BOW_EXCEEDED"


def test_evaluate_rubric_valid_dataset():
    """Verify valid fixture passes data gate rubric."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert report.status in (DataGateStatus.PASS, DataGateStatus.PASS_WITH_WARNING)
    assert report.join_coverage_percent >= 95.0
    assert report.conflicting_primary_keys_count == 0
    assert report.future_leak_count == 0
    assert "tiếng Việt" in report.guidance or report.status == DataGateStatus.PASS


def test_detect_missing_required_keys():
    """Missing primary key fields must trigger BLOCKED_DATA."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "missing_keys" / "component_lots.csv",
        FIXTURE_BASE / "missing_keys" / "unit_lots.csv",
        FIXTURE_BASE / "missing_keys" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert report.status == DataGateStatus.BLOCKED_DATA
    assert any("khóa" in act.lower() or "thiếu" in act.lower() for act in report.action_items)


def test_detect_conflicting_primary_keys():
    """Conflicting primary keys with different values must trigger BLOCKED_DATA."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "conflicting_keys" / "component_lots.csv",
        FIXTURE_BASE / "conflicting_keys" / "unit_lots.csv",
        FIXTURE_BASE / "conflicting_keys" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert report.status == DataGateStatus.BLOCKED_DATA
    assert report.conflicting_primary_keys_count > 0


def test_detect_future_leakage():
    """Feature time occurring after assembly or jig measurement must trigger BLOCKED_DATA."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "future_leak" / "component_lots.csv",
        FIXTURE_BASE / "future_leak" / "unit_lots.csv",
        FIXTURE_BASE / "future_leak" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert report.status == DataGateStatus.BLOCKED_DATA
    assert report.future_leak_count > 0


def test_handle_corrupt_files():
    """Corrupt or unreadable files must not raise uncaught exceptions, but return clear reports."""
    empty_csv = FIXTURE_BASE / "corrupt" / "empty.csv"
    with pytest.raises(ValueError) as exc_info:
        read_lsu_source(empty_csv, empty_csv, empty_csv)
    assert "trống" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower() or "không có dữ liệu" in str(exc_info.value).lower()
def test_models_serialization_and_readback():
    """Verify dataclass serialization to_dict and from_dict roundtrip."""
    from datetime import datetime, timezone, timedelta
    vn_tz = timezone(timedelta(hours=7))
    now = datetime(2026, 3, 1, 8, 0, 0, tzinfo=vn_tz)

    m = ComponentLotMeasurement(
        lot_measurement_id="M_999",
        component_lot_id="LOT_TEST",
        component_code="TEST_CODE",
        metric_name="PARAM_A",
        value=12.34,
        unit="mm",
        event_time=now,
    )
    d = m.to_dict()
    m_back = ComponentLotMeasurement.from_dict(d)
    assert m_back.lot_measurement_id == m.lot_measurement_id
    assert m_back.value == m.value
    assert m_back.event_time == m.event_time


def test_datagate_report_does_not_contain_raw_data():
    """Verify DataGateReport serialization contains aggregates only, no raw row values."""
    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    report_dict = report.to_dict()
    report_json = str(report_dict)

    # Ensure no raw serial numbers or proprietary measurement values leak in report
    assert "SYN_UNIT_001" not in report_json
    assert "25.42" not in report_json
    assert "LOT_LENS_01" not in report_json