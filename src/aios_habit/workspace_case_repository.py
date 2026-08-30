"""SQLite repository for local-only Workspace Chat case metadata."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

from aios_habit.workspace_case_models import CaseAuditEvent, CaseEvidenceReference, CaseRecord


class WorkspaceCaseRepositoryError(RuntimeError):
    """Safe persistence error for the Workspace Chat UI."""


class CaseCreationResult:
    def __init__(self, case_id: str, evidence_count: int) -> None:
        self.case_id = case_id
        self.evidence_count = evidence_count


def default_workspace_cases_db_path() -> Path:
    return Path.cwd() / "local_cases" / "workspace_cases.sqlite"


class WorkspaceCaseRepository:
    def __init__(self, database_path: Optional[Path] = None) -> None:
        self.database_path = Path(database_path or default_workspace_cases_db_path())

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    assistant_message_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS cases_trace_identity_unique
                ON cases (conversation_id, assistant_message_id, trace_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS case_evidence_references (
                    reference_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
                    trace_id TEXT NOT NULL,
                    evidence_node_id TEXT NOT NULL,
                    citation_id TEXT NOT NULL,
                    source_locator TEXT NOT NULL,
                    source_title TEXT NOT NULL,
                    reference_digest TEXT NOT NULL,
                    provenance_status TEXT NOT NULL,
                    privacy_label TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS case_audit_events (
                    event_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_case_with_evidence(
        self,
        case: CaseRecord,
        references: Iterable[CaseEvidenceReference],
    ) -> CaseCreationResult:
        reference_list = list(references)
        if not reference_list:
            raise WorkspaceCaseRepositoryError("Hồ sơ cần ít nhất một tham chiếu bằng chứng.")
        if any(reference.case_id != case.case_id for reference in reference_list):
            raise WorkspaceCaseRepositoryError("Tham chiếu bằng chứng không thuộc hồ sơ đang lưu.")

        try:
            self.initialize()
            audit_event = CaseAuditEvent.case_created(case.case_id)
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    """
                    SELECT case_id FROM cases
                    WHERE conversation_id = ? AND assistant_message_id = ? AND trace_id = ?
                    """,
                    (case.conversation_id, case.assistant_message_id, case.trace_id),
                ).fetchone()
                if existing is not None:
                    evidence_count = connection.execute(
                        "SELECT COUNT(*) FROM case_evidence_references WHERE case_id = ?",
                        (existing["case_id"],),
                    ).fetchone()[0]
                    connection.rollback()
                    return CaseCreationResult(existing["case_id"], evidence_count)
                connection.execute(
                    """
                    INSERT INTO cases (
                        case_id, conversation_id, assistant_message_id, trace_id,
                        evidence_digest, title, status, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id,
                        case.conversation_id,
                        case.assistant_message_id,
                        case.trace_id,
                        case.evidence_digest,
                        case.title,
                        case.status,
                        case.created_at,
                        case.created_by,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO case_evidence_references (
                        reference_id, case_id, trace_id, evidence_node_id, citation_id,
                        source_locator, source_title, reference_digest, provenance_status,
                        privacy_label, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            reference.reference_id,
                            reference.case_id,
                            reference.trace_id,
                            reference.evidence_node_id,
                            reference.citation_id,
                            reference.source_locator,
                            reference.source_title,
                            reference.reference_digest,
                            reference.provenance_status,
                            reference.privacy_label,
                            reference.created_at,
                        )
                        for reference in reference_list
                    ],
                )
                connection.execute(
                    """
                    INSERT INTO case_audit_events (event_id, case_id, event_type, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (audit_event.event_id, audit_event.case_id, audit_event.event_type, audit_event.created_at),
                )
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise WorkspaceCaseRepositoryError("Không thể lưu hồ sơ cục bộ một cách an toàn.") from error
        return CaseCreationResult(case.case_id, len(reference_list))

    def load_case(self, case_id: str) -> Optional[CaseRecord]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            return None
        return CaseRecord(**dict(row))

    def list_evidence_references(self, case_id: str) -> list[CaseEvidenceReference]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_evidence_references WHERE case_id = ? ORDER BY created_at, reference_id",
                (case_id,),
            ).fetchall()
        return [CaseEvidenceReference(**dict(row)) for row in rows]

    def list_audit_events(self, case_id: str) -> list[CaseAuditEvent]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_audit_events WHERE case_id = ? ORDER BY created_at, event_id",
                (case_id,),
            ).fetchall()
        return [CaseAuditEvent(**dict(row)) for row in rows]
