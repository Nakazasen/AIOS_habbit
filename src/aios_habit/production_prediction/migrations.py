"""Versioned, recoverable migrations for production prediction SQLite store."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

CURRENT_SCHEMA_VERSION = 2
FaultInjector = Callable[[str, int], None]


class PredictionMigrationError(RuntimeError):
    """Migration error for production prediction store."""


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    migrated: bool
    backup_path: Optional[Path] = None


_MIGRATION_DESCRIPTIONS = {
    1: "initial_lsu_prediction_schema",
    2: "add_shadow_risk_and_outcome_tables",
}
_MIGRATION_CHECKSUMS = {
    version: hashlib.sha256(description.encode("utf-8")).hexdigest()
    for version, description in _MIGRATION_DESCRIPTIONS.items()
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_fault(fault_injector: Optional[FaultInjector], stage: str, version: int) -> None:
    if fault_injector is not None:
        fault_injector(stage, version)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def read_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        )
        """
    )


def quick_check(connection: sqlite3.Connection) -> bool:
    row = connection.execute("PRAGMA quick_check").fetchone()
    return bool(row and str(row[0]).lower() == "ok")


def backup_database(db_path: Path) -> Optional[Path]:
    if not db_path.exists():
        return None
    backup_path = db_path.with_name(f"{db_path.name}.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def restore_database(backup_path: Path, db_path: Path) -> None:
    if not backup_path.exists():
        raise PredictionMigrationError(f"Tệp sao lưu không tồn tại: {backup_path.name}")
    shutil.copy2(backup_path, db_path)


def _apply_v1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS lsu_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            content_digest TEXT UNIQUE NOT NULL,
            source_files_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS component_measurements (
            lot_measurement_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            component_lot_id TEXT NOT NULL,
            component_code TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            event_time TEXT NOT NULL,
            source_digest TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, lot_measurement_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS unit_links (
            link_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            unit_serial TEXT NOT NULL,
            component_lot_id TEXT NOT NULL,
            component_code TEXT NOT NULL,
            assembly_time TEXT NOT NULL,
            line_id TEXT,
            station_id TEXT,
            source_digest TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, link_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jig_outcomes (
            jig_result_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            unit_serial TEXT NOT NULL,
            jig_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            event_time TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL,
            unit TEXT,
            jig_version TEXT NOT NULL,
            process_version TEXT NOT NULL,
            target_label TEXT NOT NULL,
            failure_code TEXT,
            retest_outcome TEXT,
            source_digest TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, jig_result_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS data_gate_reports (
            report_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            status TEXT NOT NULL,
            rubric_version TEXT NOT NULL,
            source_digest TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            join_coverage_percent REAL NOT NULL,
            conflicting_primary_keys_count INTEGER NOT NULL,
            future_leak_count INTEGER NOT NULL,
            ok_count INTEGER NOT NULL,
            ng_count INTEGER NOT NULL,
            unknown_count INTEGER NOT NULL,
            action_items_json TEXT NOT NULL,
            guidance TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def _apply_v2(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS shadow_risk_assessments (
            idempotency_key TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            unit_serial TEXT NOT NULL,
            as_of_time TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            factors_json TEXT NOT NULL,
            reason TEXT NOT NULL,
            link_status TEXT NOT NULL,
            case_id TEXT,
            future_leakage_detected INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shadow_risk_snapshot_unit
        ON shadow_risk_assessments (snapshot_id, unit_serial)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS shadow_outcomes (
            outcome_id TEXT PRIMARY KEY,
            unit_serial TEXT NOT NULL,
            target_label TEXT NOT NULL,
            failure_code TEXT,
            confirmed_by TEXT NOT NULL,
            rationale TEXT NOT NULL,
            is_missed_alert INTEGER NOT NULL,
            assessment_idempotency_key TEXT,
            recorded_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shadow_outcome_unit
        ON shadow_outcomes (unit_serial)
        """
    )


def migrate_database(
    db_path: Path,
    target_version: int = CURRENT_SCHEMA_VERSION,
    fault_injector: Optional[FaultInjector] = None,
) -> MigrationResult:
    if target_version > CURRENT_SCHEMA_VERSION:
        raise PredictionMigrationError(
            f"Phiên bản đích {target_version} vượt quá phiên bản hỗ trợ {CURRENT_SCHEMA_VERSION}."
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_database(db_path) if db_path.exists() else None

    try:
        with closing(sqlite3.connect(db_path)) as connection:
            ensure_migration_table(connection)
            from_version = read_schema_version(connection)

            if from_version >= target_version:
                return MigrationResult(
                    from_version=from_version,
                    to_version=from_version,
                    migrated=False,
                    backup_path=backup_path,
                )

            connection.execute("BEGIN IMMEDIATE")
            for next_ver in range(from_version + 1, target_version + 1):
                _call_fault(fault_injector, "before_step", next_ver)
                if next_ver == 1:
                    _apply_v1(connection)
                elif next_ver == 2:
                    _apply_v2(connection)
                _call_fault(fault_injector, "after_step", next_ver)

                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at, checksum) VALUES (?, ?, ?)",
                    (next_ver, _utc_now(), _MIGRATION_CHECKSUMS[next_ver]),
                )
                connection.execute(f"PRAGMA user_version = {next_ver}")

            _call_fault(fault_injector, "before_commit", target_version)
            connection.commit()

            if not quick_check(connection):
                raise PredictionMigrationError("Kiểm tra toàn vẹn quick_check thất bại sau di chuyển.")

        return MigrationResult(
            from_version=from_version,
            to_version=target_version,
            migrated=True,
            backup_path=backup_path,
        )
    except Exception as exc:
        if backup_path and backup_path.exists():
            restore_database(backup_path, db_path)
        raise PredictionMigrationError(f"Di chuyển cơ sở dữ liệu thất bại: {str(exc)}") from exc