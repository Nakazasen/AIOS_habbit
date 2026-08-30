"""SQLite repository for local-only Workspace Chat case metadata."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

from aios_habit.workspace_case_authorization import RoleGrant
from aios_habit.workspace_case_migrations import WorkspaceCaseMigrationError, migrate_store
from aios_habit.workspace_case_models import (
    CaseActivity,
    CaseAuditEvent,
    CaseChecklistItem,
    CaseEvidenceReference,
    CaseFilter,
    CaseRecord,
    case_activity_digest,
)


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
        try:
            migrate_store(self.database_path)
            with self._connection() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
        except (OSError, sqlite3.Error, WorkspaceCaseMigrationError) as error:
            raise WorkspaceCaseRepositoryError("CASE_STORE_INITIALIZATION_FAILED") from error

    @staticmethod
    def _insert_activity(connection: sqlite3.Connection, activity: CaseActivity) -> None:
        connection.execute(
            """
            INSERT INTO case_activities (
                event_id, case_id, event_type, actor_id, occurred_at,
                payload_digest, previous_event_digest, event_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity.event_id,
                activity.case_id,
                activity.event_type,
                activity.actor_id,
                activity.occurred_at,
                activity.payload_digest,
                activity.previous_event_digest,
                activity.event_digest,
            ),
        )

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
            activity = CaseActivity.new(
                case_id=case.case_id,
                event_type="case_created",
                actor_id=case.created_by,
                payload_digest=case.evidence_digest,
            )
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    """
                    SELECT case_id, evidence_digest FROM cases
                    WHERE conversation_id = ? AND assistant_message_id = ? AND trace_id = ?
                    """,
                    (case.conversation_id, case.assistant_message_id, case.trace_id),
                ).fetchone()
                if existing is not None:
                    creation_activity = connection.execute(
                        """
                        SELECT payload_digest FROM case_activities
                        WHERE case_id = ? AND event_type = 'case_created'
                        ORDER BY rowid LIMIT 1
                        """,
                        (existing["case_id"],),
                    ).fetchone()
                    initial_digest = (
                        creation_activity["payload_digest"] if creation_activity is not None
                        else existing["evidence_digest"]
                    )
                    if initial_digest != case.evidence_digest:
                        raise WorkspaceCaseRepositoryError("CASE_TRACE_EVIDENCE_CONFLICT")
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
                        evidence_digest, title, status, created_at, created_by,
                        case_type, priority, owner_id, assignee_id, scope, version,
                        updated_at, activity_head_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        case.case_type,
                        case.priority,
                        case.owner_id,
                        case.assignee_id,
                        case.scope,
                        case.version,
                        case.updated_at,
                        activity.event_digest,
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
                    "INSERT INTO case_audit_events VALUES (?, ?, ?, ?)",
                    (audit_event.event_id, audit_event.case_id, audit_event.event_type, audit_event.created_at),
                )
                self._insert_activity(connection, activity)
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise WorkspaceCaseRepositoryError("Không thể lưu hồ sơ cục bộ một cách an toàn.") from error
        return CaseCreationResult(case.case_id, len(reference_list))

    def load_case(self, case_id: str) -> Optional[CaseRecord]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        return None if row is None else CaseRecord(**dict(row))

    def list_cases(self, case_filter: Optional[CaseFilter] = None) -> list[CaseRecord]:
        self.initialize()
        filters = case_filter or CaseFilter()
        clauses: list[str] = []
        parameters: list[str] = []
        for column in ("case_type", "status", "priority", "owner_id", "assignee_id"):
            value = getattr(filters, column)
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM cases{where} ORDER BY updated_at DESC, case_id", parameters
            ).fetchall()
        return [CaseRecord(**dict(row)) for row in rows]

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

    def list_activities(self, case_id: str) -> list[CaseActivity]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_activities WHERE case_id = ? ORDER BY rowid", (case_id,)
            ).fetchall()
        return [CaseActivity(**dict(row)) for row in rows]

    def list_checklist_items(self, case_id: str) -> list[CaseChecklistItem]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_checklist_items WHERE case_id = ? ORDER BY created_at, item_id", (case_id,)
            ).fetchall()
        return [CaseChecklistItem(**dict(row)) for row in rows]

    def verify_activity_chain(self, case_id: str) -> bool:
        case = self.load_case(case_id)
        if case is None:
            return False
        previous = ""
        for activity in self.list_activities(case_id):
            expected = case_activity_digest(
                event_id=activity.event_id,
                case_id=activity.case_id,
                event_type=activity.event_type,
                actor_id=activity.actor_id,
                occurred_at=activity.occurred_at,
                payload_digest=activity.payload_digest,
                previous_event_digest=previous,
            )
            if activity.previous_event_digest != previous or activity.event_digest != expected:
                return False
            previous = activity.event_digest
        return previous == case.activity_head_digest

    def transition_case(
        self,
        case_id: str,
        *,
        expected_version: int,
        new_status: str,
        actor_id: str,
        payload_digest: str,
    ) -> CaseRecord:
        return self._update_case_with_activity(
            case_id,
            expected_version=expected_version,
            actor_id=actor_id,
            event_type="status_transition",
            payload_digest=payload_digest,
            assignments={"status": new_status},
        )

    def assign_case(
        self,
        case_id: str,
        *,
        expected_version: int,
        assignee_id: str,
        actor_id: str,
        payload_digest: str,
    ) -> CaseRecord:
        return self._update_case_with_activity(
            case_id,
            expected_version=expected_version,
            actor_id=actor_id,
            event_type="case_assigned",
            payload_digest=payload_digest,
            assignments={"assignee_id": assignee_id},
        )

    def _update_case_with_activity(
        self,
        case_id: str,
        *,
        expected_version: int,
        actor_id: str,
        event_type: str,
        payload_digest: str,
        assignments: dict[str, str],
    ) -> CaseRecord:
        self.initialize()
        allowed_columns = {"status", "assignee_id", "priority"}
        if not assignments or not set(assignments) <= allowed_columns:
            raise WorkspaceCaseRepositoryError("CASE_UPDATE_INVALID")
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
                if int(row["version"]) != expected_version:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                if not self._verify_chain_in_connection(connection, row):
                    raise WorkspaceCaseRepositoryError("CASE_ACTIVITY_CHAIN_INVALID")
                activity = CaseActivity.new(
                    case_id=case_id,
                    event_type=event_type,
                    actor_id=actor_id,
                    payload_digest=payload_digest,
                    previous_event_digest=row["activity_head_digest"],
                )
                assignments_sql = ", ".join(f"{column} = ?" for column in assignments)
                values = list(assignments.values())
                values.extend([expected_version + 1, activity.occurred_at, activity.event_digest, case_id, expected_version])
                cursor = connection.execute(
                    f"""
                    UPDATE cases SET {assignments_sql}, version = ?, updated_at = ?, activity_head_digest = ?
                    WHERE case_id = ? AND version = ?
                    """,
                    values,
                )
                if cursor.rowcount != 1:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                self._insert_activity(connection, activity)
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except sqlite3.Error as error:
            raise WorkspaceCaseRepositoryError("CASE_UPDATE_FAILED") from error
        updated = self.load_case(case_id)
        if updated is None:
            raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
        return updated

    @staticmethod
    def _verify_chain_in_connection(connection: sqlite3.Connection, case_row: sqlite3.Row) -> bool:
        previous = ""
        rows = connection.execute(
            "SELECT * FROM case_activities WHERE case_id = ? ORDER BY rowid",
            (case_row["case_id"],),
        ).fetchall()
        for row in rows:
            expected = case_activity_digest(
                event_id=row["event_id"],
                case_id=row["case_id"],
                event_type=row["event_type"],
                actor_id=row["actor_id"],
                occurred_at=row["occurred_at"],
                payload_digest=row["payload_digest"],
                previous_event_digest=previous,
            )
            if row["previous_event_digest"] != previous or row["event_digest"] != expected:
                return False
            previous = row["event_digest"]
        return previous == case_row["activity_head_digest"]

    def attach_evidence(
        self,
        reference: CaseEvidenceReference,
        *,
        expected_version: int,
        actor_id: str,
    ) -> CaseRecord:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (reference.case_id,)).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
                if int(row["version"]) != expected_version:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                if not self._verify_chain_in_connection(connection, row):
                    raise WorkspaceCaseRepositoryError("CASE_ACTIVITY_CHAIN_INVALID")
                duplicate = connection.execute(
                    "SELECT 1 FROM case_evidence_references WHERE case_id = ? AND reference_digest = ?",
                    (reference.case_id, reference.reference_digest),
                ).fetchone()
                if duplicate:
                    raise WorkspaceCaseRepositoryError("CASE_EVIDENCE_DUPLICATE")
                current_digests = [
                    digest_row["reference_digest"]
                    for digest_row in connection.execute(
                        "SELECT reference_digest FROM case_evidence_references WHERE case_id = ?",
                        (reference.case_id,),
                    ).fetchall()
                ]
                evidence_set_digest = _digest_set((*current_digests, reference.reference_digest))
                activity = CaseActivity.new(
                    case_id=reference.case_id,
                    event_type="evidence_added",
                    actor_id=actor_id,
                    payload_digest=evidence_set_digest,
                    previous_event_digest=row["activity_head_digest"],
                )
                connection.execute(
                    """
                    INSERT INTO case_evidence_references VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reference.reference_id, reference.case_id, reference.trace_id,
                        reference.evidence_node_id, reference.citation_id, reference.source_locator,
                        reference.source_title, reference.reference_digest, reference.provenance_status,
                        reference.privacy_label, reference.created_at,
                    ),
                )
                cursor = connection.execute(
                    """
                    UPDATE cases SET version = ?, updated_at = ?, activity_head_digest = ?, evidence_digest = ?
                    WHERE case_id = ? AND version = ?
                    """,
                    (
                        expected_version + 1,
                        activity.occurred_at,
                        activity.event_digest,
                        evidence_set_digest,
                        reference.case_id,
                        expected_version,
                    ),
                )
                if cursor.rowcount != 1:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                self._insert_activity(connection, activity)
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except sqlite3.Error as error:
            raise WorkspaceCaseRepositoryError("CASE_EVIDENCE_ADD_FAILED") from error
        updated = self.load_case(reference.case_id)
        if updated is None:
            raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
        return updated

    def replace_role_grants(self, actor_id: str, grants: Iterable[RoleGrant]) -> None:
        self.initialize()
        grant_list = list(grants)
        if any(grant.actor_id != actor_id for grant in grant_list):
            raise WorkspaceCaseRepositoryError("CASE_ROLE_GRANT_INVALID")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM role_grants WHERE actor_id = ?", (actor_id,))
            connection.executemany(
                "INSERT INTO role_grants VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        grant.grant_id, grant.actor_id, grant.role, grant.scope,
                        grant.valid_from, grant.valid_until, grant.revoked_at,
                    )
                    for grant in grant_list
                ],
            )
            connection.commit()

    def list_role_grants(self, actor_id: str) -> list[RoleGrant]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM role_grants WHERE actor_id = ? ORDER BY grant_id", (actor_id,)
            ).fetchall()
        return [RoleGrant(**dict(row)) for row in rows]

    def add_checklist_item(self, item: CaseChecklistItem, *, expected_version: int, actor_id: str) -> CaseRecord:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (item.case_id,)).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
                if int(row["version"]) != expected_version:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                if not self._verify_chain_in_connection(connection, row):
                    raise WorkspaceCaseRepositoryError("CASE_ACTIVITY_CHAIN_INVALID")
                activity = CaseActivity.new(
                    case_id=item.case_id,
                    event_type="checklist_added",
                    actor_id=actor_id,
                    payload_digest=hashlib_sha256(item.description),
                    previous_event_digest=row["activity_head_digest"],
                )
                connection.execute(
                    "INSERT INTO case_checklist_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.item_id, item.case_id, item.description, item.status, item.created_by,
                        item.created_at, item.resolved_by, item.resolved_at,
                    ),
                )
                cursor = connection.execute(
                    """
                    UPDATE cases SET version = ?, updated_at = ?, activity_head_digest = ?
                    WHERE case_id = ? AND version = ?
                    """,
                    (expected_version + 1, activity.occurred_at, activity.event_digest, item.case_id, expected_version),
                )
                if cursor.rowcount != 1:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                self._insert_activity(connection, activity)
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except sqlite3.Error as error:
            raise WorkspaceCaseRepositoryError("CASE_CHECKLIST_ADD_FAILED") from error
        updated = self.load_case(item.case_id)
        if updated is None:
            raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")
        return updated


def hashlib_sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_set(digests: Iterable[str]) -> str:
    return hashlib_sha256("\n".join(sorted(digests)))
