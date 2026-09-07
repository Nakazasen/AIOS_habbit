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
    CaseArtifactRecord,
    CaseAuditEvent,
    CaseChecklistItem,
    CaseEvidenceReference,
    CaseFilter,
    CaseLesson,
    CaseRecord,
    ExpertRequest,
    ExpertReview,
    LESSON_STATUS_APPROVED,
    LESSON_STATUS_CANDIDATE,
    LESSON_STATUS_REVOKED,
    case_activity_digest,
    utc_now_iso,
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

    def update_evidence_provenance(
        self,
        case_id: str,
        reference_id: str,
        *,
        expected_version: int,
        new_provenance: str,
        actor_id: str,
        note: str = "",
    ) -> CaseRecord:
        self.initialize()
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
                ref_row = connection.execute(
                    "SELECT * FROM case_evidence_references WHERE reference_id = ? AND case_id = ?",
                    (reference_id, case_id),
                ).fetchone()
                if ref_row is None:
                    raise WorkspaceCaseRepositoryError("CASE_EVIDENCE_NOT_FOUND")

                activity = CaseActivity.new(
                    case_id=case_id,
                    event_type="clue_relevance_reviewed",
                    actor_id=actor_id,
                    payload_digest=hashlib_sha256(f"{reference_id}:{new_provenance}:{note}"),
                    previous_event_digest=row["activity_head_digest"],
                )
                connection.execute(
                    "UPDATE case_evidence_references SET provenance_status = ? WHERE reference_id = ?",
                    (new_provenance, reference_id),
                )
                cursor = connection.execute(
                    """
                    UPDATE cases SET version = ?, updated_at = ?, activity_head_digest = ?
                    WHERE case_id = ? AND version = ?
                    """,
                    (expected_version + 1, activity.occurred_at, activity.event_digest, case_id, expected_version),
                )
                if cursor.rowcount != 1:
                    raise WorkspaceCaseRepositoryError("CASE_VERSION_CONFLICT")
                self._insert_activity(connection, activity)
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except sqlite3.Error as error:
            raise WorkspaceCaseRepositoryError("CASE_EVIDENCE_UPDATE_FAILED") from error
        updated = self.load_case(case_id)
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

    def create_expert_request(self, request: ExpertRequest, *, activity: Optional[CaseActivity] = None) -> ExpertRequest:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO expert_requests (
                        request_id, case_id, claim_digest, question_text, requested_expert_id,
                        required_scope, status, due_at, created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.request_id,
                        request.case_id,
                        request.claim_digest,
                        request.question_text,
                        request.requested_expert_id,
                        request.required_scope,
                        request.status,
                        request.due_at,
                        request.created_by,
                        request.created_at,
                    ),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, request.case_id),
                    )
                connection.commit()
        except sqlite3.Error as error:
            raise WorkspaceCaseRepositoryError("EXPERT_REQUEST_CREATE_FAILED") from error
        return request

    def load_expert_request(self, request_id: str) -> Optional[ExpertRequest]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM expert_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is None:
                return None
            return ExpertRequest(
                request_id=row["request_id"],
                case_id=row["case_id"],
                claim_digest=row["claim_digest"],
                question_text=row["question_text"],
                requested_expert_id=row["requested_expert_id"],
                required_scope=row["required_scope"],
                status=row["status"],
                due_at=row["due_at"],
                created_by=row["created_by"],
                created_at=row["created_at"],
            )

    def list_expert_requests(self, case_id: str) -> list[ExpertRequest]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM expert_requests WHERE case_id = ? ORDER BY created_at ASC", (case_id,)
            ).fetchall()
            return [
                ExpertRequest(
                    request_id=row["request_id"],
                    case_id=row["case_id"],
                    claim_digest=row["claim_digest"],
                    question_text=row["question_text"],
                    requested_expert_id=row["requested_expert_id"],
                    required_scope=row["required_scope"],
                    status=row["status"],
                    due_at=row["due_at"],
                    created_by=row["created_by"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def record_expert_review(
        self,
        review: ExpertReview,
        *,
        updated_request_status: str = "answered",
        activity: Optional[CaseActivity] = None,
        fault_injector: Optional[Callable[[str], None]] = None,
    ) -> ExpertReview:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO expert_reviews (
                        review_id, request_id, case_id, claim_digest, evidence_digest,
                        decision, reviewer_id, reviewer_role, scope, rationale,
                        confidence, supersedes_review_id, reviewed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review.review_id,
                        review.request_id,
                        review.case_id,
                        review.claim_digest,
                        review.evidence_digest,
                        review.decision,
                        review.reviewer_id,
                        review.reviewer_role,
                        review.scope,
                        review.rationale,
                        review.confidence,
                        review.supersedes_review_id,
                        review.reviewed_at,
                    ),
                )
                connection.execute(
                    "UPDATE expert_requests SET status = ? WHERE request_id = ?",
                    (updated_request_status, review.request_id),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, review.case_id),
                    )
                if fault_injector is not None:
                    fault_injector("before_commit")
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except Exception as error:
            raise WorkspaceCaseRepositoryError("EXPERT_REVIEW_RECORD_FAILED") from error
        return review

    def record_expert_review_with_fault(
        self,
        *,
        request_id: str,
        decision: str,
        rationale: str,
        confidence: float = 1.0,
        actor_id: str,
        fault_injector: Optional[Callable[[str], None]] = None,
        supersedes_review_id: Optional[str] = None,
    ) -> ExpertReview:
        from uuid import uuid4

        req = self.load_expert_request(request_id)
        if req is None:
            raise WorkspaceCaseRepositoryError("EXPERT_REQUEST_NOT_FOUND")
        case = self.load_case(req.case_id)
        if case is None:
            raise WorkspaceCaseRepositoryError("CASE_NOT_FOUND")

        review_id = f"EXP-REV-{uuid4().hex[:12].upper()}"
        review = ExpertReview(
            review_id=review_id,
            request_id=request_id,
            case_id=req.case_id,
            claim_digest=req.claim_digest,
            evidence_digest=case.evidence_digest,
            decision=decision,
            reviewer_id=actor_id,
            reviewer_role="expert",
            scope=req.required_scope,
            rationale=rationale,
            confidence=confidence,
            supersedes_review_id=supersedes_review_id,
        )
        activity = CaseActivity.new(
            case_id=case.case_id,
            event_type="expert_review_recorded",
            actor_id=actor_id,
            payload_digest=hashlib_sha256(f"{review_id}:{decision}"),
            previous_event_digest=case.activity_head_digest,
        )
        return self.record_expert_review(
            review,
            updated_request_status="answered",
            activity=activity,
            fault_injector=fault_injector,
        )

    def list_expert_reviews(self, case_id: str) -> list[ExpertReview]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM expert_reviews WHERE case_id = ? ORDER BY reviewed_at ASC", (case_id,)
            ).fetchall()
            return [
                ExpertReview(
                    review_id=row["review_id"],
                    request_id=row["request_id"],
                    case_id=row["case_id"],
                    claim_digest=row["claim_digest"],
                    evidence_digest=row["evidence_digest"],
                    decision=row["decision"],
                    reviewer_id=row["reviewer_id"],
                    reviewer_role=row["reviewer_role"],
                    scope=row["scope"],
                    rationale=row["rationale"],
                    confidence=float(row["confidence"]),
                    supersedes_review_id=row["supersedes_review_id"],
                    reviewed_at=row["reviewed_at"],
                )
                for row in rows
            ]

    def load_expert_review(self, review_id: str) -> Optional[ExpertReview]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM expert_reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if row is None:
                return None
            return ExpertReview(
                review_id=row["review_id"],
                request_id=row["request_id"],
                case_id=row["case_id"],
                claim_digest=row["claim_digest"],
                evidence_digest=row["evidence_digest"],
                decision=row["decision"],
                reviewer_id=row["reviewer_id"],
                reviewer_role=row["reviewer_role"],
                scope=row["scope"],
                rationale=row["rationale"],
                confidence=float(row["confidence"]),
                supersedes_review_id=row["supersedes_review_id"],
                reviewed_at=row["reviewed_at"],
            )

    def create_case_lesson(
        self,
        lesson: CaseLesson,
        *,
        activity: Optional[CaseActivity] = None,
        fault_injector: Optional[Callable[[str], None]] = None,
    ) -> CaseLesson:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO case_lessons (
                        lesson_id, case_id, review_id, claim_digest, evidence_digest,
                        title, content, status, version, created_by, created_at,
                        updated_by, updated_at, approved_by, approved_at,
                        revoked_by, revoked_at, revocation_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lesson.lesson_id,
                        lesson.case_id,
                        lesson.review_id,
                        lesson.claim_digest,
                        lesson.evidence_digest,
                        lesson.title,
                        lesson.content,
                        lesson.status,
                        lesson.version,
                        lesson.created_by,
                        lesson.created_at,
                        lesson.updated_by,
                        lesson.updated_at,
                        lesson.approved_by,
                        lesson.approved_at,
                        lesson.revoked_by,
                        lesson.revoked_at,
                        lesson.revocation_reason,
                    ),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, lesson.case_id),
                    )
                if fault_injector is not None:
                    fault_injector("before_commit")
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except Exception as error:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_CREATE_FAILED") from error
        return lesson

    def update_case_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
        title: str,
        content: str,
        actor_id: str,
        activity: Optional[CaseActivity] = None,
    ) -> CaseLesson:
        self.initialize()
        now = utc_now_iso()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT version FROM case_lessons WHERE lesson_id = ?", (lesson_id,)
                ).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
                if row["version"] != expected_version:
                    raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
                new_version = expected_version + 1
                connection.execute(
                    """
                    UPDATE case_lessons
                    SET title = ?, content = ?, version = ?, updated_by = ?, updated_at = ?
                    WHERE lesson_id = ? AND version = ?
                    """,
                    (title, content, new_version, actor_id, now, lesson_id, expected_version),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, activity.case_id),
                    )
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except Exception as error:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_UPDATE_FAILED") from error
        updated = self.load_case_lesson(lesson_id)
        if updated is None:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
        return updated

    def promote_case_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
        actor_id: str,
        activity: Optional[CaseActivity] = None,
    ) -> CaseLesson:
        self.initialize()
        now = utc_now_iso()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT version, status FROM case_lessons WHERE lesson_id = ?", (lesson_id,)
                ).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
                if row["version"] != expected_version:
                    raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
                if row["status"] != LESSON_STATUS_CANDIDATE:
                    raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_CANDIDATE")
                new_version = expected_version + 1
                connection.execute(
                    """
                    UPDATE case_lessons
                    SET status = ?, approved_by = ?, approved_at = ?, version = ?, updated_by = ?, updated_at = ?
                    WHERE lesson_id = ? AND version = ?
                    """,
                    (LESSON_STATUS_APPROVED, actor_id, now, new_version, actor_id, now, lesson_id, expected_version),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, activity.case_id),
                    )
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except Exception as error:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_PROMOTE_FAILED") from error
        promoted = self.load_case_lesson(lesson_id)
        if promoted is None:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
        return promoted

    def revoke_case_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
        actor_id: str,
        reason: str,
        activity: Optional[CaseActivity] = None,
    ) -> CaseLesson:
        self.initialize()
        now = utc_now_iso()
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT version, status FROM case_lessons WHERE lesson_id = ?", (lesson_id,)
                ).fetchone()
                if row is None:
                    raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
                if row["version"] != expected_version:
                    raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
                new_version = expected_version + 1
                connection.execute(
                    """
                    UPDATE case_lessons
                    SET status = ?, revoked_by = ?, revoked_at = ?, revocation_reason = ?, version = ?, updated_by = ?, updated_at = ?
                    WHERE lesson_id = ? AND version = ?
                    """,
                    (LESSON_STATUS_REVOKED, actor_id, now, reason, new_version, actor_id, now, lesson_id, expected_version),
                )
                if activity is not None:
                    self._insert_activity(connection, activity)
                    connection.execute(
                        "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                        (activity.event_digest, activity.occurred_at, activity.case_id),
                    )
                connection.commit()
        except WorkspaceCaseRepositoryError:
            raise
        except Exception as error:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_REVOKE_FAILED") from error
        revoked = self.load_case_lesson(lesson_id)
        if revoked is None:
            raise WorkspaceCaseRepositoryError("CASE_LESSON_NOT_FOUND")
        return revoked

    def load_case_lesson(self, lesson_id: str) -> Optional[CaseLesson]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM case_lessons WHERE lesson_id = ?", (lesson_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_lesson(row)

    def list_case_lessons(self, case_id: str) -> list[CaseLesson]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_lessons WHERE case_id = ? ORDER BY created_at ASC", (case_id,)
            ).fetchall()
            return [self._row_to_lesson(row) for row in rows]

    def list_all_lessons(self, *, status: Optional[str] = None) -> list[CaseLesson]:
        self.initialize()
        with self._connection() as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM case_lessons WHERE status = ? ORDER BY updated_at DESC", (status,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM case_lessons ORDER BY updated_at DESC"
                ).fetchall()
            return [self._row_to_lesson(row) for row in rows]

    def search_approved_lessons(self, query: str, *, limit: int = 20) -> list[CaseLesson]:
        self.initialize()
        clean_q = f"%{query.strip()}%"
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM case_lessons
                WHERE status = 'approved' AND (title LIKE ? OR content LIKE ?)
                ORDER BY approved_at DESC, updated_at DESC
                LIMIT ?
                """,
                (clean_q, clean_q, limit),
            ).fetchall()
            return [self._row_to_lesson(row) for row in rows]

    @staticmethod
    def _row_to_lesson(row: sqlite3.Row) -> CaseLesson:
        return CaseLesson(
            lesson_id=row["lesson_id"],
            case_id=row["case_id"],
            review_id=row["review_id"],
            claim_digest=row["claim_digest"],
            evidence_digest=row["evidence_digest"],
            title=row["title"],
            content=row["content"],
            status=row["status"],
            version=int(row["version"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_by=row["updated_by"],
            updated_at=row["updated_at"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            revoked_by=row["revoked_by"],
            revoked_at=row["revoked_at"],
            revocation_reason=row["revocation_reason"],
        )

    def insert_artifact(self, artifact: CaseArtifactRecord, *, activity: Optional[CaseActivity] = None) -> CaseArtifactRecord:
        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO case_artifacts (
                    artifact_id, case_id, artifact_type, title, content_markdown,
                    content_digest, version, status, created_by, created_at,
                    updated_by, updated_at, approved_by, approved_at, approval_notes,
                    exported_path, provenance_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id,
                    artifact.case_id,
                    artifact.artifact_type,
                    artifact.title,
                    artifact.content_markdown,
                    artifact.content_digest,
                    artifact.version,
                    artifact.status,
                    artifact.created_by,
                    artifact.created_at,
                    artifact.updated_by,
                    artifact.updated_at,
                    artifact.approved_by,
                    artifact.approved_at,
                    artifact.approval_notes,
                    artifact.exported_path,
                    artifact.provenance_digest,
                ),
            )
            if activity is not None:
                self._insert_activity(connection, activity)
                connection.execute(
                    "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                    (activity.event_digest, activity.occurred_at, activity.case_id),
                )
            connection.commit()
        return artifact

    def update_artifact_content(
        self,
        artifact_id: str,
        *,
        expected_version: int,
        title: Optional[str] = None,
        content_markdown: str,
        content_digest: str,
        updated_by: str,
        activity: Optional[CaseActivity] = None,
    ) -> CaseArtifactRecord:
        self.initialize()
        now_iso = utc_now_iso()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT version, status, title, case_id FROM case_artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
            if int(row["version"]) != expected_version:
                raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
            if row["status"] == "approved":
                raise WorkspaceCaseRepositoryError("APPROVED_ARTIFACT_IMMUTABLE")

            new_title = title if title is not None else row["title"]
            new_version = expected_version + 1
            cursor = connection.execute(
                """
                UPDATE case_artifacts
                SET title = ?, content_markdown = ?, content_digest = ?, version = ?,
                    status = 'draft', updated_by = ?, updated_at = ?, approved_by = NULL,
                    approved_at = NULL, approval_notes = NULL
                WHERE artifact_id = ? AND version = ?
                """,
                (new_title, content_markdown, content_digest, new_version, updated_by, now_iso, artifact_id, expected_version),
            )
            if cursor.rowcount != 1:
                raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
            if activity is not None:
                self._insert_activity(connection, activity)
                connection.execute(
                    "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                    (activity.event_digest, activity.occurred_at, activity.case_id),
                )
            connection.commit()
        updated = self.load_case_artifact(artifact_id)
        if updated is None:
            raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
        return updated

    def approve_artifact(
        self,
        artifact_id: str,
        *,
        expected_version: int,
        approved_by: str,
        approval_notes: str = "",
        approved_content: Optional[str] = None,
        activity: Optional[CaseActivity] = None,
    ) -> CaseArtifactRecord:
        self.initialize()
        now_iso = utc_now_iso()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT version, status, content_markdown, case_id FROM case_artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
            if int(row["version"]) != expected_version:
                raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
            if row["status"] != "draft":
                raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_DRAFT")

            final_content = approved_content if approved_content is not None else row["content_markdown"]
            final_digest = hashlib_sha256(final_content)
            new_version = expected_version + 1
            cursor = connection.execute(
                """
                UPDATE case_artifacts
                SET status = 'approved', content_markdown = ?, content_digest = ?,
                    version = ?, updated_by = ?, updated_at = ?,
                    approved_by = ?, approved_at = ?, approval_notes = ?
                WHERE artifact_id = ? AND version = ?
                """,
                (
                    final_content,
                    final_digest,
                    new_version,
                    approved_by,
                    now_iso,
                    approved_by,
                    now_iso,
                    approval_notes,
                    artifact_id,
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                raise WorkspaceCaseRepositoryError("CONCURRENT_UPDATE_CONFLICT")
            if activity is not None:
                self._insert_activity(connection, activity)
                connection.execute(
                    "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                    (activity.event_digest, activity.occurred_at, activity.case_id),
                )
            connection.commit()
        approved = self.load_case_artifact(artifact_id)
        if approved is None:
            raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
        return approved

    def record_artifact_export(
        self,
        artifact_id: str,
        *,
        exported_path: str,
        activity: Optional[CaseActivity] = None,
    ) -> CaseArtifactRecord:
        self.initialize()
        now_iso = utc_now_iso()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, case_id FROM case_artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
            if row["status"] != "approved":
                raise WorkspaceCaseRepositoryError("UNAPPROVED_ARTIFACT_EXPORT_FORBIDDEN")
            connection.execute(
                """
                UPDATE case_artifacts
                SET exported_path = ?, updated_at = ?
                WHERE artifact_id = ?
                """,
                (exported_path, now_iso, artifact_id),
            )
            if activity is not None:
                self._insert_activity(connection, activity)
                connection.execute(
                    "UPDATE cases SET activity_head_digest = ?, updated_at = ? WHERE case_id = ?",
                    (activity.event_digest, activity.occurred_at, activity.case_id),
                )
            connection.commit()
        exported = self.load_case_artifact(artifact_id)
        if exported is None:
            raise WorkspaceCaseRepositoryError("CASE_ARTIFACT_NOT_FOUND")
        return exported

    def load_case_artifact(self, artifact_id: str) -> Optional[CaseArtifactRecord]:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM case_artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_artifact(row)

    def list_case_artifacts(self, case_id: str) -> list[CaseArtifactRecord]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM case_artifacts WHERE case_id = ? ORDER BY created_at ASC", (case_id,)
            ).fetchall()
            return [self._row_to_artifact(row) for row in rows]

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row) -> CaseArtifactRecord:
        return CaseArtifactRecord(
            artifact_id=row["artifact_id"],
            case_id=row["case_id"],
            artifact_type=row["artifact_type"],
            title=row["title"],
            content_markdown=row["content_markdown"],
            content_digest=row["content_digest"],
            version=int(row["version"]),
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_by=row["updated_by"],
            updated_at=row["updated_at"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            approval_notes=row["approval_notes"],
            exported_path=row["exported_path"],
            provenance_digest=row["provenance_digest"],
        )


def hashlib_sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_set(digests: Iterable[str]) -> str:
    return hashlib_sha256("\n".join(sorted(digests)))
