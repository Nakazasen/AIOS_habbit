"""Test suite for production prediction SQLite repository and recoverable migrations."""

from __future__ import annotations

from pathlib import Path
import pytest
import sqlite3

from aios_habit.production_prediction.lsu_iris import (
    evaluate_data_gate_rubric,
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.migrations import (
    CURRENT_SCHEMA_VERSION,
    PredictionMigrationError,
    migrate_database,
    read_schema_version,
)
from aios_habit.production_prediction.models import (
    DataGateReport,
    DataGateStatus,
    LsuDatasetSnapshot,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


def test_repository_migration_and_integrity(tmp_path):
    """Repository must automatically migrate schema and ensure quick_check passes."""
    db_path = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_path)

    with sqlite3.connect(db_path) as conn:
        assert read_schema_version(conn) == CURRENT_SCHEMA_VERSION
        check = conn.execute("PRAGMA quick_check").fetchone()
        assert check[0].lower() == "ok"


def test_register_and_load_valid_snapshot(tmp_path):
    """Register valid snapshot and retrieve it with full field fidelity."""
    db_path = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_path)

    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert repo.register_lsu_snapshot(normalized, gate_report) is True

    # Test load_lsu_snapshot
    loaded = repo.load_lsu_snapshot(normalized.snapshot_id)
    assert loaded is not None
    assert loaded.snapshot_id == normalized.snapshot_id
    assert loaded.content_digest == normalized.content_digest
    assert len(loaded.component_measurements) == 6
    assert len(loaded.unit_links) == 4
    assert len(loaded.jig_outcomes) == 2

    # Test find by digest
    found = repo.find_snapshot_by_digest(normalized.content_digest)
    assert found is not None
    assert found.snapshot_id == normalized.snapshot_id

    # Test list_snapshots
    snapshots = repo.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0]["snapshot_id"] == normalized.snapshot_id


def test_idempotent_registration(tmp_path):
    """Registering identical snapshot twice must return True without duplicating rows."""
    db_path = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_path)

    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert repo.register_lsu_snapshot(normalized, gate_report) is True
    assert repo.register_lsu_snapshot(normalized, gate_report) is True

    with sqlite3.connect(db_path) as conn:
        snap_count = conn.execute("SELECT COUNT(*) FROM lsu_snapshots").fetchone()[0]
        comp_count = conn.execute("SELECT COUNT(*) FROM component_measurements").fetchone()[0]
        unit_count = conn.execute("SELECT COUNT(*) FROM unit_links").fetchone()[0]
        jig_count = conn.execute("SELECT COUNT(*) FROM jig_outcomes").fetchone()[0]

        assert snap_count == 1
        assert comp_count == 6
        assert unit_count == 4
        assert jig_count == 2


def test_prohibit_blocked_data_persistence(tmp_path):
    """Snapshots evaluated as BLOCKED_DATA must be strictly rejected from persistence."""
    db_path = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_path)

    snapshot = read_lsu_source(
        FIXTURE_BASE / "conflicting_keys" / "component_lots.csv",
        FIXTURE_BASE / "conflicting_keys" / "unit_lots.csv",
        FIXTURE_BASE / "conflicting_keys" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)

    assert gate_report.status == DataGateStatus.BLOCKED_DATA

    with pytest.raises(ValueError) as exc_info:
        repo.register_lsu_snapshot(normalized, gate_report)
    assert "cấm ghi bền vững" in str(exc_info.value) or "không đạt" in str(exc_info.value)

    # Verify nothing was persisted
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lsu_snapshots").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM component_measurements").fetchone()[0] == 0


def test_load_unit_trace_from_repository(tmp_path):
    """Retrieve joined unit trace directly from SQLite repository."""
    db_path = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_path)

    snapshot = read_lsu_source(
        FIXTURE_BASE / "valid" / "component_lots.csv",
        FIXTURE_BASE / "valid" / "unit_lots.csv",
        FIXTURE_BASE / "valid" / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)
    repo.register_lsu_snapshot(normalized, gate_report)

    # Query unit 1 (OK)
    t1 = repo.load_unit_trace(normalized.snapshot_id, "SYN_UNIT_001")
    assert t1 is not None
    assert t1.unit_serial == "SYN_UNIT_001"
    assert t1.target_label == "OK"
    assert len(t1.lot_measurements) == 4
    assert len(t1.jig_measurements) == 1

    # Query unit 2 (NG)
    t2 = repo.load_unit_trace(normalized.snapshot_id, "SYN_UNIT_002")
    assert t2 is not None
    assert t2.unit_serial == "SYN_UNIT_002"
    assert t2.target_label == "NG"
    assert t2.failure_code == "ERR_BOW_EXCEEDED"

    # Query nonexistent unit
    t_none = repo.load_unit_trace(normalized.snapshot_id, "NONEXISTENT_UNIT")
    assert t_none is None


def test_migration_fault_injection_and_recovery(tmp_path):
    """Verify fault injection during migration restores backup safely."""
    db_path = tmp_path / "fault_test.sqlite"

    def fault_injector(stage: str, version: int):
        if stage == "before_commit":
            raise RuntimeError("Mô phỏng sập nguồn trước khi commit migration")

    with pytest.raises(PredictionMigrationError):
        migrate_database(db_path, target_version=1, fault_injector=fault_injector)

    # Check that database either doesn't exist or is restored to version 0
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            assert read_schema_version(conn) == 0