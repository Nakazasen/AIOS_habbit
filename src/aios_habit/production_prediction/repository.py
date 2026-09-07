"""Repository for production prediction and LSU dataset snapshots in SQLite."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aios_habit.production_prediction.migrations import CURRENT_SCHEMA_VERSION, migrate_database
from aios_habit.production_prediction.models import (
    ComponentLotMeasurement,
    DataGateReport,
    DataGateStatus,
    JigOutcomeResult,
    JoinedUnitTrace,
    LsuDatasetSnapshot,
    UnitLotLink,
)


class ProductionPredictionRepository:
    """Safe SQLite repository for LSU Iris dataset snapshots and trace retrieval."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_migrated()

    def _ensure_migrated(self) -> None:
        migrate_database(self.db_path, target_version=CURRENT_SCHEMA_VERSION)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_lsu_snapshot(
        self,
        snapshot: LsuDatasetSnapshot,
        gate_report: DataGateReport,
    ) -> bool:
        """Register a validated LSU snapshot idempotently.

        Data with BLOCKED_DATA or FAIL_TECHNICAL status is strictly prohibited
        from being persisted.
        """
        if gate_report.status in (DataGateStatus.BLOCKED_DATA, DataGateStatus.FAIL_TECHNICAL):
            raise ValueError(
                f"Dữ liệu không đạt tiêu chí an toàn ({gate_report.status.value}), cấm ghi bền vững."
            )

        with closing(self._get_connection()) as conn:
            # Check idempotency by content_digest
            existing = conn.execute(
                "SELECT snapshot_id FROM lsu_snapshots WHERE content_digest = ?",
                (snapshot.content_digest,),
            ).fetchone()
            if existing is not None:
                return True

            with conn:
                # 1. Insert snapshot header
                conn.execute(
                    """
                    INSERT INTO lsu_snapshots (snapshot_id, created_at, content_digest, source_files_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        snapshot.snapshot_id,
                        snapshot.created_at.isoformat(),
                        snapshot.content_digest,
                        json.dumps(snapshot.source_files, ensure_ascii=False),
                    ),
                )

                # 2. Insert component measurements
                conn.executemany(
                    """
                    INSERT INTO component_measurements (
                        lot_measurement_id, snapshot_id, component_lot_id, component_code,
                        metric_name, value, unit, event_time, source_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            m.lot_measurement_id,
                            snapshot.snapshot_id,
                            m.component_lot_id,
                            m.component_code,
                            m.metric_name,
                            m.value,
                            m.unit,
                            m.event_time.isoformat(),
                            m.source_digest,
                        )
                        for m in snapshot.component_measurements
                    ],
                )

                # 3. Insert unit links
                conn.executemany(
                    """
                    INSERT INTO unit_links (
                        link_id, snapshot_id, unit_serial, component_lot_id,
                        component_code, assembly_time, line_id, station_id, source_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            u.link_id,
                            snapshot.snapshot_id,
                            u.unit_serial,
                            u.component_lot_id,
                            u.component_code,
                            u.assembly_time.isoformat(),
                            u.line_id,
                            u.station_id,
                            u.source_digest,
                        )
                        for u in snapshot.unit_links
                    ],
                )

                # 4. Insert jig outcomes
                conn.executemany(
                    """
                    INSERT INTO jig_outcomes (
                        jig_result_id, snapshot_id, unit_serial, jig_id, run_id,
                        event_time, metric_name, value, unit, jig_version,
                        process_version, target_label, failure_code, retest_outcome, source_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            j.jig_result_id,
                            snapshot.snapshot_id,
                            j.unit_serial,
                            j.jig_id,
                            j.run_id,
                            j.event_time.isoformat(),
                            j.metric_name,
                            j.value,
                            j.unit,
                            j.jig_version,
                            j.process_version,
                            j.target_label,
                            j.failure_code,
                            j.retest_outcome,
                            j.source_digest,
                        )
                        for j in snapshot.jig_outcomes
                    ],
                )

                # 5. Insert data gate report
                report_id = f"dgr_{snapshot.content_digest[:16]}"
                conn.execute(
                    """
                    INSERT INTO data_gate_reports (
                        report_id, snapshot_id, status, rubric_version, source_digest,
                        total_rows, join_coverage_percent, conflicting_primary_keys_count,
                        future_leak_count, ok_count, ng_count, unknown_count,
                        action_items_json, guidance, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        snapshot.snapshot_id,
                        gate_report.status.value,
                        gate_report.rubric_version,
                        gate_report.source_digest,
                        gate_report.total_rows,
                        gate_report.join_coverage_percent,
                        gate_report.conflicting_primary_keys_count,
                        gate_report.future_leak_count,
                        gate_report.ok_count,
                        gate_report.ng_count,
                        gate_report.unknown_count,
                        json.dumps(gate_report.action_items, ensure_ascii=False),
                        gate_report.guidance,
                        gate_report.created_at.isoformat(),
                    ),
                )

            return True

    def find_snapshot_by_digest(self, content_digest: str) -> Optional[LsuDatasetSnapshot]:
        with closing(self._get_connection()) as conn:
            row = conn.execute(
                "SELECT snapshot_id FROM lsu_snapshots WHERE content_digest = ?",
                (content_digest,),
            ).fetchone()
            if not row:
                return None
            return self.load_lsu_snapshot(row["snapshot_id"])

    def load_lsu_snapshot(self, snapshot_id: str) -> Optional[LsuDatasetSnapshot]:
        with closing(self._get_connection()) as conn:
            snap_row = conn.execute(
                "SELECT * FROM lsu_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if not snap_row:
                return None

            comp_rows = conn.execute(
                "SELECT * FROM component_measurements WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()
            unit_rows = conn.execute(
                "SELECT * FROM unit_links WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()
            jig_rows = conn.execute(
                "SELECT * FROM jig_outcomes WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()

            comp_list = [
                ComponentLotMeasurement(
                    lot_measurement_id=r["lot_measurement_id"],
                    component_lot_id=r["component_lot_id"],
                    component_code=r["component_code"],
                    metric_name=r["metric_name"],
                    value=float(r["value"]),
                    unit=r["unit"],
                    event_time=datetime.fromisoformat(r["event_time"]),
                    source_digest=r["source_digest"],
                )
                for r in comp_rows
            ]

            unit_list = [
                UnitLotLink(
                    link_id=r["link_id"],
                    unit_serial=r["unit_serial"],
                    component_lot_id=r["component_lot_id"],
                    component_code=r["component_code"],
                    assembly_time=datetime.fromisoformat(r["assembly_time"]),
                    line_id=r["line_id"],
                    station_id=r["station_id"],
                    source_digest=r["source_digest"],
                )
                for r in unit_rows
            ]

            jig_list = [
                JigOutcomeResult(
                    jig_result_id=r["jig_result_id"],
                    unit_serial=r["unit_serial"],
                    jig_id=r["jig_id"],
                    run_id=r["run_id"],
                    event_time=datetime.fromisoformat(r["event_time"]),
                    metric_name=r["metric_name"],
                    value=float(r["value"]) if r["value"] is not None else None,
                    unit=r["unit"],
                    jig_version=r["jig_version"],
                    process_version=r["process_version"],
                    target_label=r["target_label"],
                    failure_code=r["failure_code"],
                    retest_outcome=r["retest_outcome"],
                    source_digest=r["source_digest"],
                )
                for r in jig_rows
            ]

            return LsuDatasetSnapshot(
                snapshot_id=snap_row["snapshot_id"],
                created_at=datetime.fromisoformat(snap_row["created_at"]),
                source_files=json.loads(snap_row["source_files_json"]),
                component_measurements=comp_list,
                unit_links=unit_list,
                jig_outcomes=jig_list,
                content_digest=snap_row["content_digest"],
            )

    def list_snapshots(self) -> List[Dict[str, Any]]:
        with closing(self._get_connection()) as conn:
            rows = conn.execute(
                "SELECT snapshot_id, created_at, content_digest, source_files_json FROM lsu_snapshots ORDER BY created_at DESC"
            ).fetchall()
            return [
                {
                    "snapshot_id": r["snapshot_id"],
                    "created_at": r["created_at"],
                    "content_digest": r["content_digest"],
                    "source_files": json.loads(r["source_files_json"]),
                }
                for r in rows
            ]

    def load_unit_trace(self, snapshot_id: str, unit_serial: str) -> Optional[JoinedUnitTrace]:
        with closing(self._get_connection()) as conn:
            unit_rows = conn.execute(
                "SELECT * FROM unit_links WHERE snapshot_id = ? AND unit_serial = ?",
                (snapshot_id, unit_serial),
            ).fetchall()
            jig_rows = conn.execute(
                "SELECT * FROM jig_outcomes WHERE snapshot_id = ? AND unit_serial = ?",
                (snapshot_id, unit_serial),
            ).fetchall()

            if not unit_rows and not jig_rows:
                return None

            lot_ids = [r["component_lot_id"] for r in unit_rows if r["component_lot_id"]]
            comp_list: List[ComponentLotMeasurement] = []
            if lot_ids:
                placeholders = ",".join("?" for _ in lot_ids)
                comp_rows = conn.execute(
                    f"SELECT * FROM component_measurements WHERE snapshot_id = ? AND component_lot_id IN ({placeholders})",
                    [snapshot_id] + lot_ids,
                ).fetchall()
                comp_list = [
                    ComponentLotMeasurement(
                        lot_measurement_id=r["lot_measurement_id"],
                        component_lot_id=r["component_lot_id"],
                        component_code=r["component_code"],
                        metric_name=r["metric_name"],
                        value=float(r["value"]),
                        unit=r["unit"],
                        event_time=datetime.fromisoformat(r["event_time"]),
                        source_digest=r["source_digest"],
                    )
                    for r in comp_rows
                ]

            jig_list = [
                JigOutcomeResult(
                    jig_result_id=r["jig_result_id"],
                    unit_serial=r["unit_serial"],
                    jig_id=r["jig_id"],
                    run_id=r["run_id"],
                    event_time=datetime.fromisoformat(r["event_time"]),
                    metric_name=r["metric_name"],
                    value=float(r["value"]) if r["value"] is not None else None,
                    unit=r["unit"],
                    jig_version=r["jig_version"],
                    process_version=r["process_version"],
                    target_label=r["target_label"],
                    failure_code=r["failure_code"],
                    retest_outcome=r["retest_outcome"],
                    source_digest=r["source_digest"],
                )
                for r in jig_rows
            ]

            assembly_time = None
            if unit_rows:
                assembly_time = min(datetime.fromisoformat(r["assembly_time"]) for r in unit_rows)

            jig_event_time = None
            target_label = "UNKNOWN"
            failure_code = None
            if jig_list:
                jig_event_time = min(j.event_time for j in jig_list)
                ngs = [j for j in jig_list if j.target_label == "NG"]
                if ngs:
                    target_label = "NG"
                    failure_code = ngs[0].failure_code
                elif any(j.target_label == "OK" for j in jig_list):
                    target_label = "OK"

            return JoinedUnitTrace(
                unit_serial=unit_serial,
                assembly_time=assembly_time,
                jig_event_time=jig_event_time,
                target_label=target_label,
                failure_code=failure_code,
                lot_measurements=comp_list,
                jig_measurements=jig_list,
            )

    def load_latest_gate_report(self, snapshot_id: str) -> Optional[DataGateReport]:
        with closing(self._get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM data_gate_reports WHERE snapshot_id = ? ORDER BY created_at DESC LIMIT 1",
                (snapshot_id,),
            ).fetchone()
            if not row:
                return None
            return DataGateReport(
                status=DataGateStatus(row["status"]),
                rubric_version=row["rubric_version"],
                source_digest=row["source_digest"],
                total_rows=row["total_rows"],
                join_coverage_percent=row["join_coverage_percent"],
                conflicting_primary_keys_count=row["conflicting_primary_keys_count"],
                future_leak_count=row["future_leak_count"],
                time_parse_valid_percent=100.0,
                unit_recognition_percent=100.0,
                ok_count=row["ok_count"],
                ng_count=row["ng_count"],
                unknown_count=row["unknown_count"],
                action_items=json.loads(row["action_items_json"]),
                guidance=row["guidance"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )