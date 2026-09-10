"""SQLite repository for append-only and idempotent persistence of interview sessions, turns, and checkpoints.

Implements T031 of 010-expert-knowledge-acquisition.
Follows ADR-0009 and data-model.md.
"""
from __future__ import annotations

from aios_habit.controlled_knowledge_artifact import (
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_CHANGES_REQUESTED,
    ARTIFACT_STATUS_REJECTED,
    ARTIFACT_STATUS_REVOKED,
    ArtifactApproval,
    ControlledKnowledgeArtifact,
    DecisionRecord,
)

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from aios_habit.expert_interview_models import (
    CompletionRubric,
    InterviewBudget,
    InterviewCheckpoint,
    InterviewPlan,
    InterviewSession,
    InterviewTurn,
    SeedQuestion,
)
from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CANDIDATE,
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    CLAIM_STATUS_REJECTED,
    CLAIM_STATUS_SUPERSEDED,
    KnowledgeClaim,
)
from aios_habit.local_transcription import (
    AudioPathSecurityError,
    ConsentRecord,
    TranscriptionReceipt,
    TranscriptionSegment,
    validate_local_only_audio_path,
)


def _atomic_write_bytes(destination: Path, payload: bytes) -> None:
    """Durably replace one file without exposing a partially written payload."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _file_has_digest(path: Path, expected_digest: str) -> bool:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest
    except OSError:
        return False


def default_interview_db_path() -> Path:
    return Path.cwd() / "local_cases" / "workspace_cases.sqlite"


class ExpertInterviewRepository:
    """Persistence manager for interview sessions, turns, and checkpoints."""

    def __init__(self, database_path: Optional[Path] = None) -> None:
        self.database_path = Path(database_path or default_interview_db_path())

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expert_interview_plans (
                    plan_id TEXT PRIMARY KEY,
                    plan_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    expert_id TEXT NOT NULL,
                    principal_subject_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    consent_state TEXT NOT NULL,
                    checkpoint_seq INTEGER NOT NULL,
                    last_turn_digest TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    ended_at TEXT,
                    stop_reason TEXT,
                    idempotency_key TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_sessions_plan_idx ON interview_sessions(plan_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS interview_sessions_expert_idx ON interview_sessions(expert_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    question_reason TEXT NOT NULL,
                    trigger_refs_json TEXT NOT NULL,
                    answer_confidence REAL NOT NULL,
                    answer_state TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    supersedes_turn_id TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_turns_session_seq_idx ON interview_turns(session_id, sequence)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_checkpoints_session_seq_idx ON interview_checkpoints(session_id, sequence)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_consents (
                    consent_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    version TEXT NOT NULL,
                    state TEXT NOT NULL,
                    purposes_json TEXT NOT NULL,
                    retention_policy TEXT NOT NULL,
                    granted_at TEXT,
                    withdrawn_at TEXT,
                    policy_digest TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_consents_session_idx ON interview_consents(session_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_transcripts (
                    receipt_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    audio_path TEXT NOT NULL,
                    audio_digest TEXT NOT NULL,
                    engine_name TEXT NOT NULL,
                    engine_version TEXT NOT NULL,
                    transcript_locator TEXT NOT NULL DEFAULT '',
                    transcript_digest TEXT NOT NULL DEFAULT '',
                    segments_json TEXT NOT NULL DEFAULT '',
                    full_text TEXT NOT NULL DEFAULT '',
                    all_critical_tokens_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_transcripts_session_idx ON interview_transcripts(session_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_claims (
                    claim_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    version TEXT NOT NULL,
                    validity_conditions_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    uncertainty_note TEXT NOT NULL,
                    status TEXT NOT NULL,
                    conflict_claim_ids_json TEXT NOT NULL,
                    escalation_id TEXT,
                    confirmed_by TEXT,
                    confirmed_at TEXT,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS knowledge_claims_scope_idx ON knowledge_claims(scope)")
            conn.execute("CREATE INDEX IF NOT EXISTS knowledge_claims_status_idx ON knowledge_claims(status)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS claim_review_decisions (
                    decision_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS claim_review_decisions_claim_idx ON claim_review_decisions(claim_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS controlled_knowledge_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_markdown TEXT NOT NULL,
                    claim_ids_json TEXT NOT NULL,
                    claim_map_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS artifacts_scope_idx ON controlled_knowledge_artifacts(scope)")
            conn.execute("CREATE INDEX IF NOT EXISTS artifacts_status_idx ON controlled_knowledge_artifacts(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS controlled_knowledge_artifact_versions (
                    artifact_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_markdown TEXT NOT NULL,
                    claim_ids_json TEXT NOT NULL,
                    claim_map_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    PRIMARY KEY (artifact_id, version)
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO controlled_knowledge_artifact_versions (
                    artifact_id, artifact_type, title, scope, version,
                    content_markdown, claim_ids_json, claim_map_json, status,
                    created_by, digest, created_at, idempotency_key
                )
                SELECT artifact_id, artifact_type, title, scope, version,
                       content_markdown, claim_ids_json, claim_map_json, status,
                       created_by, digest, created_at, 'BASELINE-' || artifact_id || '-' || version
                FROM controlled_knowledge_artifacts
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_approvals (
                    approval_id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    artifact_digest TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS artifact_approvals_art_idx ON artifact_approvals(artifact_id)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_decisions (
                    decision_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    subject_digest TEXT NOT NULL,
                    subject_version TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    recorded_name TEXT NOT NULL,
                    machine_ref TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    checked_source_refs_json TEXT NOT NULL,
                    responsibility_acknowledged INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS artifact_decisions_subject_idx ON artifact_decisions(subject_id)")


    @staticmethod
    def _plan_payload(plan: InterviewPlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "version": plan.version,
            "gap_ids": list(plan.gap_ids),
            "required_scope": plan.required_scope,
            "eligible_expert_ids": list(plan.eligible_expert_ids),
            "seed_questions": [
                {
                    "question_id": question.question_id,
                    "text": question.text,
                    "target_gap_id": question.target_gap_id,
                    "expected_aspects": list(question.expected_aspects),
                    "suggested_order": question.suggested_order,
                }
                for question in plan.seed_questions
            ],
            "budget": {
                "max_turns": plan.budget.max_turns,
                "max_minutes": plan.budget.max_minutes,
                "token_budget": plan.budget.token_budget,
            },
            "completion_rubric": {
                "required_aspects": list(plan.completion_rubric.required_aspects),
                "min_grounded_claims": plan.completion_rubric.min_grounded_claims,
                "allow_unknown": plan.completion_rubric.allow_unknown,
                "stop_on_repeated_unknowns": plan.completion_rubric.stop_on_repeated_unknowns,
                "escalation_owner": plan.completion_rubric.escalation_owner,
            },
            "status": plan.status,
            "created_by": plan.created_by,
            "created_at": plan.created_at,
            "digest": plan.digest,
        }

    def save_interview_plan(self, plan: InterviewPlan, idempotency_key: str) -> None:
        """Persist an immutable interview plan so UI reruns can resume safely."""
        self.initialize()
        plan_json = json.dumps(self._plan_payload(plan), ensure_ascii=False, sort_keys=True)
        with self._connection() as conn:
            existing = conn.execute(
                "SELECT plan_id, plan_json, digest, idempotency_key FROM expert_interview_plans WHERE plan_id = ? OR idempotency_key = ?",
                (plan.plan_id, idempotency_key),
            ).fetchone()
            expected = (plan.plan_id, plan_json, plan.digest, idempotency_key)
            if existing is not None:
                if tuple(existing) != expected:
                    raise ValueError("Mã kế hoạch hoặc mã chống ghi lặp đã được dùng cho nội dung khác.")
                return
            conn.execute(
                "INSERT INTO expert_interview_plans (plan_id, plan_json, digest, idempotency_key) VALUES (?, ?, ?, ?)",
                expected,
            )

    def get_interview_plan(self, plan_id: str) -> Optional[InterviewPlan]:
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT plan_json FROM expert_interview_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["plan_json"])
        return InterviewPlan(
            plan_id=payload["plan_id"],
            version=payload["version"],
            gap_ids=tuple(payload["gap_ids"]),
            required_scope=payload["required_scope"],
            eligible_expert_ids=tuple(payload["eligible_expert_ids"]),
            seed_questions=tuple(
                SeedQuestion(
                    question_id=question["question_id"],
                    text=question["text"],
                    target_gap_id=question["target_gap_id"],
                    expected_aspects=tuple(question["expected_aspects"]),
                    suggested_order=question["suggested_order"],
                )
                for question in payload["seed_questions"]
            ),
            budget=InterviewBudget(**payload["budget"]),
            completion_rubric=CompletionRubric(
                required_aspects=tuple(payload["completion_rubric"]["required_aspects"]),
                min_grounded_claims=payload["completion_rubric"]["min_grounded_claims"],
                allow_unknown=payload["completion_rubric"]["allow_unknown"],
                stop_on_repeated_unknowns=payload["completion_rubric"]["stop_on_repeated_unknowns"],
                escalation_owner=payload["completion_rubric"]["escalation_owner"],
            ),
            status=payload["status"],
            created_by=payload["created_by"],
            created_at=payload["created_at"],
            digest=payload["digest"],
        )

    def save_session(self, session: InterviewSession, idempotency_key: str) -> None:
        """Idempotently save or update an interview session."""
        self.initialize()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO interview_sessions (
                    session_id, plan_id, expert_id, principal_subject_id,
                    state, consent_state, checkpoint_seq, last_turn_digest,
                    started_at, updated_at, ended_at, stop_reason, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state = excluded.state,
                    consent_state = excluded.consent_state,
                    checkpoint_seq = excluded.checkpoint_seq,
                    last_turn_digest = excluded.last_turn_digest,
                    updated_at = excluded.updated_at,
                    ended_at = excluded.ended_at,
                    stop_reason = excluded.stop_reason,
                    idempotency_key = excluded.idempotency_key
                """,
                (
                    session.session_id,
                    session.plan_id,
                    session.expert_id,
                    session.principal_subject_id,
                    session.state,
                    session.consent_state,
                    session.checkpoint_seq,
                    session.last_turn_digest,
                    session.started_at,
                    session.updated_at,
                    session.ended_at,
                    session.stop_reason,
                    idempotency_key,
                ),
            )

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Fetch session by ID."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT session_id, plan_id, expert_id, principal_subject_id,
                       state, consent_state, checkpoint_seq, last_turn_digest,
                       started_at, updated_at, ended_at, stop_reason
                FROM interview_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return InterviewSession(
                session_id=row["session_id"],
                plan_id=row["plan_id"],
                expert_id=row["expert_id"],
                principal_subject_id=row["principal_subject_id"],
                state=row["state"],
                consent_state=row["consent_state"],
                checkpoint_seq=row["checkpoint_seq"],
                last_turn_digest=row["last_turn_digest"],
                started_at=row["started_at"],
                updated_at=row["updated_at"],
                ended_at=row["ended_at"],
                stop_reason=row["stop_reason"],
            )

    def list_sessions(self, plan_id: Optional[str] = None) -> list[InterviewSession]:
        """Fetch all interview sessions, optionally filtered by plan_id, ordered by started_at DESC."""
        self.initialize()
        with self._connection() as conn:
            if plan_id:
                rows = conn.execute(
                    """
                    SELECT session_id, plan_id, expert_id, principal_subject_id,
                           state, consent_state, checkpoint_seq, last_turn_digest,
                           started_at, updated_at, ended_at, stop_reason
                    FROM interview_sessions
                    WHERE plan_id = ?
                    ORDER BY started_at DESC
                    """,
                    (plan_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT session_id, plan_id, expert_id, principal_subject_id,
                           state, consent_state, checkpoint_seq, last_turn_digest,
                           started_at, updated_at, ended_at, stop_reason
                    FROM interview_sessions
                    ORDER BY started_at DESC
                    """
                ).fetchall()
            return [
                InterviewSession(
                    session_id=r["session_id"],
                    plan_id=r["plan_id"],
                    expert_id=r["expert_id"],
                    principal_subject_id=r["principal_subject_id"],
                    state=r["state"],
                    consent_state=r["consent_state"],
                    checkpoint_seq=r["checkpoint_seq"],
                    last_turn_digest=r["last_turn_digest"],
                    started_at=r["started_at"],
                    updated_at=r["updated_at"],
                    ended_at=r["ended_at"],
                    stop_reason=r["stop_reason"],
                )
                for r in rows
            ]

    def save_turn(self, turn: InterviewTurn, idempotency_key: str) -> None:
        """Idempotently save an interview turn."""
        self.initialize()
        triggers_json = json.dumps(list(turn.trigger_refs), ensure_ascii=False)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO interview_turns (
                    turn_id, session_id, sequence, question_text, answer_text,
                    question_reason, trigger_refs_json, answer_confidence,
                    answer_state, payload_digest, created_at, supersedes_turn_id,
                    idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO UPDATE SET
                    answer_text = excluded.answer_text,
                    answer_confidence = excluded.answer_confidence,
                    answer_state = excluded.answer_state,
                    payload_digest = excluded.payload_digest
                """,
                (
                    turn.turn_id,
                    turn.session_id,
                    turn.sequence,
                    turn.question_text,
                    turn.answer_text,
                    turn.question_reason,
                    triggers_json,
                    turn.answer_confidence,
                    turn.answer_state,
                    turn.payload_digest,
                    turn.created_at,
                    turn.supersedes_turn_id,
                    idempotency_key,
                ),
            )

    def list_turns(self, session_id: str) -> list[InterviewTurn]:
        """Fetch all turns of a session in sequence order."""
        self.initialize()
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT turn_id, session_id, sequence, question_text, answer_text,
                       question_reason, trigger_refs_json, answer_confidence,
                       answer_state, payload_digest, created_at, supersedes_turn_id
                FROM interview_turns
                WHERE session_id = ?
                ORDER BY sequence ASC
                """,
                (session_id,),
            ).fetchall()
            return [
                InterviewTurn(
                    turn_id=r["turn_id"],
                    session_id=r["session_id"],
                    sequence=r["sequence"],
                    question_text=r["question_text"],
                    answer_text=r["answer_text"],
                    question_reason=r["question_reason"],
                    trigger_refs=tuple(json.loads(r["trigger_refs_json"])),
                    answer_confidence=r["answer_confidence"],
                    answer_state=r["answer_state"],
                    payload_digest=r["payload_digest"],
                    created_at=r["created_at"],
                    supersedes_turn_id=r["supersedes_turn_id"],
                )
                for r in rows
            ]

    def save_checkpoint(self, checkpoint: InterviewCheckpoint) -> None:
        """Append-only save of a session checkpoint."""
        self.initialize()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO interview_checkpoints (
                    checkpoint_id, session_id, sequence, state,
                    snapshot_json, digest, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(checkpoint_id) DO NOTHING
                """,
                (
                    checkpoint.checkpoint_id,
                    checkpoint.session_id,
                    checkpoint.sequence,
                    checkpoint.state,
                    checkpoint.snapshot_json,
                    checkpoint.digest,
                    checkpoint.created_at,
                ),
            )

    def get_latest_checkpoint(self, session_id: str) -> Optional[InterviewCheckpoint]:
        """Fetch latest checkpoint for a session."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT checkpoint_id, session_id, sequence, state, snapshot_json, digest, created_at
                FROM interview_checkpoints
                WHERE session_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return InterviewCheckpoint(
                checkpoint_id=row["checkpoint_id"],
                session_id=row["session_id"],
                sequence=row["sequence"],
                state=row["state"],
                snapshot_json=row["snapshot_json"],
                digest=row["digest"],
                created_at=row["created_at"],
            )

    def save_consent(self, consent: ConsentRecord, idempotency_key: str) -> None:
        """Idempotently save or update expert consent record."""
        self.initialize()
        purposes_json = json.dumps(list(consent.purposes), ensure_ascii=False)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO interview_consents (
                    consent_id, session_id, subject, version, state,
                    purposes_json, retention_policy, granted_at, withdrawn_at,
                    policy_digest, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state = excluded.state,
                    withdrawn_at = excluded.withdrawn_at,
                    policy_digest = excluded.policy_digest
                """,
                (
                    consent.consent_id,
                    consent.session_id,
                    consent.subject,
                    consent.version,
                    consent.state,
                    purposes_json,
                    consent.retention_policy,
                    consent.granted_at,
                    consent.withdrawn_at,
                    consent.policy_digest or consent.compute_digest(),
                    idempotency_key,
                ),
            )

    def get_consent(self, session_id: str) -> Optional[ConsentRecord]:
        """Fetch consent record for a session."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT consent_id, session_id, subject, version, state,
                       purposes_json, retention_policy, granted_at, withdrawn_at, policy_digest
                FROM interview_consents
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return ConsentRecord(
                consent_id=row["consent_id"],
                session_id=row["session_id"],
                subject=row["subject"],
                version=row["version"],
                state=row["state"],
                purposes=tuple(json.loads(row["purposes_json"])),
                retention_policy=row["retention_policy"],
                granted_at=row["granted_at"],
                withdrawn_at=row["withdrawn_at"],
                policy_digest=row["policy_digest"],
            )

    def save_transcription_receipt(
        self,
        receipt: TranscriptionReceipt,
        idempotency_key: str,
        local_only_root: Optional[Path] = None,
    ) -> None:
        """Idempotently save transcription receipt, isolating raw transcript data into local_only storage."""
        self.initialize()
        if local_only_root and receipt.audio_path != "manual_input" and Path(receipt.audio_path).exists():
            validate_local_only_audio_path(Path(receipt.audio_path), local_only_root)

        if local_only_root:
            transcripts_dir = Path(local_only_root) / "transcripts"
        else:
            transcripts_dir = self.database_path.parent / "local_only" / "transcripts"

        try:
            transcripts_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(f"Không thể khởi tạo thư mục lưu trữ cục bộ '{transcripts_dir}': {exc}") from exc

        # 1. Isolate raw transcript into local_only storage (outside SQLite database)
        segments_data = [
            {
                "segment_id": s.segment_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
                "tokens": list(s.tokens),
                "critical_tokens": list(s.critical_tokens),
                "is_confirmed": s.is_confirmed,
                "edited_text": s.edited_text,
            }
            for s in receipt.segments
        ]
        raw_payload = {
            "receipt_id": receipt.receipt_id,
            "session_id": receipt.session_id,
            "full_text": receipt.full_text,
            "segments": segments_data,
        }
        raw_json_bytes = json.dumps(raw_payload, ensure_ascii=False, indent=2).encode("utf-8")
        transcript_digest = hashlib.sha256(raw_json_bytes).hexdigest()

        with self._connection() as conn:
            existing = conn.execute(
                """
                SELECT receipt_id, session_id, transcript_locator, transcript_digest, idempotency_key
                FROM interview_transcripts
                WHERE receipt_id = ? OR idempotency_key = ?
                """,
                (receipt.receipt_id, idempotency_key),
            ).fetchone()
        if existing is not None:
            if (
                existing["receipt_id"] != receipt.receipt_id
                or existing["session_id"] != receipt.session_id
                or existing["transcript_digest"] != transcript_digest
                or existing["idempotency_key"] != idempotency_key
            ):
                raise ValueError("Mã bản chép lời hoặc mã chống ghi lặp đã được dùng cho nội dung khác.")
            existing_file = Path(existing["transcript_locator"])
            if existing_file.exists() and _file_has_digest(existing_file, transcript_digest):
                return
            raise RuntimeError("Bản chép lời đã lưu bị thiếu hoặc không còn khớp mã kiểm tra.")

        # Sanitize filename strictly against path traversal
        safe_receipt_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", receipt.receipt_id)
        if not safe_receipt_stem or safe_receipt_stem.startswith("."):
            safe_receipt_stem = f"receipt_{safe_receipt_stem.lstrip('.')}"
        # Keep enough human-readable context without exceeding Windows path limits.
        safe_receipt_stem = safe_receipt_stem[:48].rstrip("_-.") or "receipt"
        receipt_key = hashlib.sha256(receipt.receipt_id.encode("utf-8")).hexdigest()[:12]
        transcript_file = (
            transcripts_dir / f"{safe_receipt_stem}_{receipt_key}_{transcript_digest[:12]}.json"
        ).resolve()
        resolved_dir = transcripts_dir.resolve()
        if not str(transcript_file).startswith(str(resolved_dir)):
            raise ValueError(f"Đường dẫn transcript không hợp lệ (path traversal): '{receipt.receipt_id}'")

        # Atomic write with rollback on DB failure
        already_existed = transcript_file.exists()
        backup_bytes = transcript_file.read_bytes() if already_existed else None

        _atomic_write_bytes(transcript_file, raw_json_bytes)
        transcript_locator = str(transcript_file)
        critical_json = json.dumps(list(receipt.all_critical_tokens), ensure_ascii=False)

        try:
            with self._connection() as conn:
                # Ensure migration columns exist
                columns = {str(r[1]) for r in conn.execute("PRAGMA table_info(interview_transcripts)")}
                if "transcript_locator" not in columns:
                    conn.execute("ALTER TABLE interview_transcripts ADD COLUMN transcript_locator TEXT NOT NULL DEFAULT ''")
                if "transcript_digest" not in columns:
                    conn.execute("ALTER TABLE interview_transcripts ADD COLUMN transcript_digest TEXT NOT NULL DEFAULT ''")

                conn.execute(
                    """
                    INSERT INTO interview_transcripts (
                        receipt_id, session_id, audio_path, audio_digest,
                        engine_name, engine_version, transcript_locator, transcript_digest,
                        segments_json, full_text, all_critical_tokens_json, state,
                        created_at, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        receipt.session_id,
                        receipt.audio_path,
                        receipt.audio_digest,
                        receipt.engine_name,
                        receipt.engine_version,
                        transcript_locator,
                        transcript_digest,
                        "",  # Zero raw transcript stored in SQLite DB
                        "",  # Zero raw full text stored in SQLite DB
                        critical_json,
                        receipt.state,
                        receipt.created_at,
                        idempotency_key,
                    ),
                )
        except Exception:
            # Only undo our own payload. A concurrent newer replacement must win.
            if _file_has_digest(transcript_file, transcript_digest):
                if not already_existed:
                    transcript_file.unlink(missing_ok=True)
                elif backup_bytes is not None:
                    _atomic_write_bytes(transcript_file, backup_bytes)
            raise

    def get_transcription_receipt(self, session_id: str) -> Optional[TranscriptionReceipt]:
        """Fetch transcription receipt for a session, resolving raw transcript from local_only store."""
        self.initialize()
        with self._connection() as conn:
            columns = {str(r[1]) for r in conn.execute("PRAGMA table_info(interview_transcripts)")}
            has_locator = "transcript_locator" in columns and "transcript_digest" in columns

            if has_locator:
                row = conn.execute(
                    """
                    SELECT receipt_id, session_id, audio_path, audio_digest,
                           engine_name, engine_version, transcript_locator, transcript_digest,
                           segments_json, full_text, all_critical_tokens_json, state, created_at
                    FROM interview_transcripts
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT receipt_id, session_id, audio_path, audio_digest,
                           engine_name, engine_version,
                           segments_json, full_text, all_critical_tokens_json, state, created_at
                    FROM interview_transcripts
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()

            if row is None:
                return None

            full_text = ""
            segments_list = []

            transcript_locator = row["transcript_locator"] if has_locator and "transcript_locator" in row.keys() else ""
            transcript_digest = row["transcript_digest"] if has_locator and "transcript_digest" in row.keys() else ""

            locator_path = Path(transcript_locator) if transcript_locator else None
            if locator_path and not locator_path.exists():
                fallback_path = self.database_path.parent / "local_only" / "transcripts" / locator_path.name
                if fallback_path.exists():
                    locator_path = fallback_path

            if locator_path and locator_path.exists():
                file_bytes = locator_path.read_bytes()
                computed_digest = hashlib.sha256(file_bytes).hexdigest()
                if transcript_digest and computed_digest != transcript_digest:
                    raise RuntimeError(f"Sai lệch mã băm bản chép lời tại '{locator_path}'.")
                data = json.loads(file_bytes.decode("utf-8"))
                full_text = data.get("full_text", "")
                segments_raw = data.get("segments", [])
                segments_list = [
                    TranscriptionSegment(
                        segment_id=s["segment_id"],
                        start_time=float(s["start_time"]),
                        end_time=float(s["end_time"]),
                        text=s["text"],
                        tokens=tuple(s.get("tokens", [])),
                        critical_tokens=tuple(s.get("critical_tokens", [])),
                        is_confirmed=bool(s.get("is_confirmed", False)),
                        edited_text=s.get("edited_text"),
                    )
                    for s in segments_raw
                ]
            elif row["segments_json"]:
                # Legacy fallback
                segments_raw = json.loads(row["segments_json"])
                segments_list = [
                    TranscriptionSegment(
                        segment_id=s["segment_id"],
                        start_time=float(s["start_time"]),
                        end_time=float(s["end_time"]),
                        text=s["text"],
                        tokens=tuple(s.get("tokens", [])),
                        critical_tokens=tuple(s.get("critical_tokens", [])),
                        is_confirmed=bool(s.get("is_confirmed", False)),
                        edited_text=s.get("edited_text"),
                    )
                    for s in segments_raw
                ]
                full_text = row["full_text"]
            elif transcript_locator:
                raise FileNotFoundError(f"Tệp bản chép lời cục bộ không tồn tại hoặc đã bị mất tại: '{transcript_locator}'.")

            critical_tokens = tuple(json.loads(row["all_critical_tokens_json"]))

            return TranscriptionReceipt(
                receipt_id=row["receipt_id"],
                session_id=row["session_id"],
                audio_path=row["audio_path"],
                audio_digest=row["audio_digest"],
                engine_name=row["engine_name"],
                engine_version=row["engine_version"],
                segments=tuple(segments_list),
                full_text=full_text,
                all_critical_tokens=critical_tokens,
                state=row["state"],
                created_at=row["created_at"],
            )

    def save_claim(self, claim: KnowledgeClaim, idempotency_key: str) -> None:
        """Idempotently save or update a knowledge claim."""
        self.initialize()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_claims (
                    claim_id, statement, scope, source_refs_json,
                    version, validity_conditions_json, confidence,
                    uncertainty_note, status, conflict_claim_ids_json,
                    escalation_id, confirmed_by, confirmed_at, digest,
                    created_at, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    statement = excluded.statement,
                    scope = excluded.scope,
                    source_refs_json = excluded.source_refs_json,
                    version = excluded.version,
                    validity_conditions_json = excluded.validity_conditions_json,
                    confidence = excluded.confidence,
                    uncertainty_note = excluded.uncertainty_note,
                    status = excluded.status,
                    conflict_claim_ids_json = excluded.conflict_claim_ids_json,
                    escalation_id = excluded.escalation_id,
                    confirmed_by = excluded.confirmed_by,
                    confirmed_at = excluded.confirmed_at,
                    digest = excluded.digest,
                    idempotency_key = excluded.idempotency_key
                """,
                (
                    claim.claim_id,
                    claim.statement,
                    claim.scope,
                    json.dumps(list(claim.source_refs)),
                    claim.version,
                    json.dumps(list(claim.validity_conditions)),
                    claim.confidence,
                    claim.uncertainty_note,
                    claim.status,
                    json.dumps(list(claim.conflict_claim_ids)),
                    claim.escalation_id,
                    claim.confirmed_by,
                    claim.confirmed_at,
                    claim.digest,
                    claim.created_at,
                    idempotency_key,
                ),
            )

    def get_claim(self, claim_id: str) -> Optional[KnowledgeClaim]:
        """Fetch claim by ID."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT claim_id, statement, scope, source_refs_json,
                       version, validity_conditions_json, confidence,
                       uncertainty_note, status, conflict_claim_ids_json,
                       escalation_id, confirmed_by, confirmed_at, digest, created_at
                FROM knowledge_claims
                WHERE claim_id = ?
                """,
                (claim_id,),
            ).fetchone()
            if row is None:
                return None

            return KnowledgeClaim(
                claim_id=row["claim_id"],
                statement=row["statement"],
                scope=row["scope"],
                source_refs=tuple(json.loads(row["source_refs_json"])),
                version=row["version"],
                validity_conditions=tuple(json.loads(row["validity_conditions_json"])),
                confidence=float(row["confidence"]),
                uncertainty_note=row["uncertainty_note"],
                status=row["status"],
                conflict_claim_ids=tuple(json.loads(row["conflict_claim_ids_json"])),
                escalation_id=row["escalation_id"],
                confirmed_by=row["confirmed_by"],
                confirmed_at=row["confirmed_at"],
                created_at=row["created_at"],
            )

    def list_claims(
        self,
        scope: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[KnowledgeClaim]:
        """List claims with optional scope and status filtering."""
        self.initialize()
        with self._connection() as conn:
            query = "SELECT claim_id, statement, scope, source_refs_json, version, validity_conditions_json, confidence, uncertainty_note, status, conflict_claim_ids_json, escalation_id, confirmed_by, confirmed_at, digest, created_at FROM knowledge_claims"
            params: list[str] = []
            conditions: list[str] = []

            if scope is not None:
                conditions.append("scope = ?")
                params.append(scope)
            if status is not None:
                conditions.append("status = ?")
                params.append(status)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at ASC"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                KnowledgeClaim(
                    claim_id=r["claim_id"],
                    statement=r["statement"],
                    scope=r["scope"],
                    source_refs=tuple(json.loads(r["source_refs_json"])),
                    version=r["version"],
                    validity_conditions=tuple(json.loads(r["validity_conditions_json"])),
                    confidence=float(r["confidence"]),
                    uncertainty_note=r["uncertainty_note"],
                    status=r["status"],
                    conflict_claim_ids=tuple(json.loads(r["conflict_claim_ids_json"])),
                    escalation_id=r["escalation_id"],
                    confirmed_by=r["confirmed_by"],
                    confirmed_at=r["confirmed_at"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def save_claim_review_decision(
        self,
        decision_id: str,
        claim_id: str,
        decision: str,
        reviewer_id: str,
        reason: str,
        idempotency_key: str,
    ) -> None:
        """Record review decision for a claim."""
        self.initialize()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO claim_review_decisions (
                    decision_id, claim_id, decision, reviewer_id,
                    reason, created_at, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(decision_id) DO NOTHING
                """,
                (decision_id, claim_id, decision, reviewer_id, reason, idempotency_key),
            )

    def save_artifact(self, artifact: ControlledKnowledgeArtifact, idempotency_key: str) -> None:
        """Save or update controlled knowledge artifact idempotently."""
        self.initialize()
        with self._connection() as conn:
            self._insert_artifact_version(conn, artifact, idempotency_key)
            conn.execute(
                """
                INSERT INTO controlled_knowledge_artifacts (
                    artifact_id, artifact_type, title, scope, version,
                    content_markdown, claim_ids_json, claim_map_json,
                    status, created_by, digest, created_at, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    title = excluded.title,
                    version = excluded.version,
                    content_markdown = excluded.content_markdown,
                    claim_ids_json = excluded.claim_ids_json,
                    claim_map_json = excluded.claim_map_json,
                    status = excluded.status,
                    digest = excluded.digest,
                    idempotency_key = excluded.idempotency_key
                """,
                (
                    artifact.artifact_id,
                    artifact.artifact_type,
                    artifact.title,
                    artifact.scope,
                    artifact.version,
                    artifact.content_markdown,
                    json.dumps(list(artifact.claim_ids)),
                    json.dumps(artifact.claim_map),
                    artifact.status,
                    artifact.created_by,
                    artifact.digest,
                    artifact.created_at,
                    idempotency_key,
                ),
            )

    def get_artifact(self, artifact_id: str) -> Optional[ControlledKnowledgeArtifact]:
        """Fetch artifact by ID including associated approvals."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT artifact_id, artifact_type, title, scope, version,
                       content_markdown, claim_ids_json, claim_map_json,
                       status, created_by, digest, created_at
                FROM controlled_knowledge_artifacts
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()
            if row is None:
                return None

            approvals = self.list_artifact_approvals(artifact_id)
            decisions = self.list_decision_records(artifact_id)

            return ControlledKnowledgeArtifact(
                artifact_id=row["artifact_id"],
                artifact_type=row["artifact_type"],
                title=row["title"],
                scope=row["scope"],
                version=row["version"],
                content_markdown=row["content_markdown"],
                claim_ids=tuple(json.loads(row["claim_ids_json"])),
                claim_map=json.loads(row["claim_map_json"]),
                status=row["status"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                approvals=tuple(approvals),
                decisions=tuple(decisions),
            )

    def list_artifacts(
        self,
        scope: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ControlledKnowledgeArtifact]:
        """List artifacts with optional filtering."""
        self.initialize()
        with self._connection() as conn:
            query = "SELECT artifact_id FROM controlled_knowledge_artifacts"
            params: list[str] = []
            conditions: list[str] = []

            if scope is not None:
                conditions.append("scope = ?")
                params.append(scope)
            if status is not None:
                conditions.append("status = ?")
                params.append(status)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at ASC"
            rows = conn.execute(query, tuple(params)).fetchall()

            result: list[ControlledKnowledgeArtifact] = []
            for r in rows:
                art = self.get_artifact(r["artifact_id"])
                if art:
                    result.append(art)
            return result

    def save_artifact_approval(self, approval: ArtifactApproval, idempotency_key: str) -> None:
        """Record approval action audit log."""
        self.initialize()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO artifact_approvals (
                    approval_id, artifact_id, artifact_digest, action,
                    actor_id, scope, reason, created_at, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(approval_id) DO NOTHING
                """,
                (
                    approval.approval_id,
                    approval.artifact_id,
                    approval.artifact_digest,
                    approval.action,
                    approval.actor_id,
                    approval.scope,
                    approval.reason,
                    approval.created_at,
                    idempotency_key,
                ),
            )

    def list_artifact_approvals(self, artifact_id: str) -> list[ArtifactApproval]:
        """Fetch all approval decisions for an artifact."""
        self.initialize()
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT approval_id, artifact_id, artifact_digest, action,
                       actor_id, scope, reason, created_at
                FROM artifact_approvals
                WHERE artifact_id = ?
                ORDER BY created_at ASC
                """,
                (artifact_id,),
            ).fetchall()

            return [
                ArtifactApproval(
                    approval_id=r["approval_id"],
                    artifact_id=r["artifact_id"],
                    artifact_digest=r["artifact_digest"],
                    action=r["action"],
                    actor_id=r["actor_id"],
                    scope=r["scope"],
                    reason=r["reason"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def save_decision_record(self, decision: DecisionRecord, idempotency_key: str) -> None:
        """Persist one immutable responsibility decision idempotently."""
        self.initialize()
        sources_json = json.dumps(list(decision.checked_source_refs), ensure_ascii=False)
        with self._connection() as conn:
            existing = conn.execute(
                """
                SELECT decision_id, subject_id, subject_digest, subject_version,
                       decision, recorded_name, machine_ref, confidence, rationale,
                       checked_source_refs_json, responsibility_acknowledged, idempotency_key
                FROM artifact_decisions WHERE decision_id = ? OR idempotency_key = ?
                """,
                (decision.decision_id, idempotency_key),
            ).fetchone()
            expected = (
                decision.decision_id, decision.subject_id, decision.subject_digest,
                decision.subject_version, decision.decision, decision.recorded_name,
                decision.machine_ref, decision.confidence, decision.rationale,
                sources_json, int(decision.responsibility_acknowledged), idempotency_key,
            )
            if existing is not None:
                if tuple(existing) != expected:
                    raise ValueError("Mã quyết định hoặc mã chống ghi lặp đã được dùng cho nội dung khác.")
                return
            conn.execute(
                """
                INSERT INTO artifact_decisions (
                    decision_id, subject_id, subject_digest, subject_version,
                    decision, recorded_name, machine_ref, confidence, rationale,
                    checked_source_refs_json, responsibility_acknowledged,
                    created_at, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.subject_id,
                    decision.subject_digest,
                    decision.subject_version,
                    decision.decision,
                    decision.recorded_name,
                    decision.machine_ref,
                    decision.confidence,
                    decision.rationale,
                    sources_json,
                    int(decision.responsibility_acknowledged),
                    decision.created_at,
                    idempotency_key,
                ),
            )

    @staticmethod
    def _insert_artifact_version(
        conn: sqlite3.Connection,
        artifact: ControlledKnowledgeArtifact,
        idempotency_key: str,
    ) -> None:
        claim_ids_json = json.dumps(list(artifact.claim_ids))
        claim_map_json = json.dumps(artifact.claim_map)
        existing = conn.execute(
            """
            SELECT artifact_id, artifact_type, title, scope, version,
                   content_markdown, claim_ids_json, claim_map_json, status,
                   created_by, digest, created_at, idempotency_key
            FROM controlled_knowledge_artifact_versions
            WHERE (artifact_id = ? AND version = ?) OR idempotency_key = ?
            """,
            (artifact.artifact_id, artifact.version, idempotency_key),
        ).fetchone()
        expected = (
            artifact.artifact_id, artifact.artifact_type, artifact.title, artifact.scope,
            artifact.version, artifact.content_markdown, claim_ids_json, claim_map_json,
            artifact.status, artifact.created_by, artifact.digest, artifact.created_at,
            idempotency_key,
        )
        if existing is not None:
            if tuple(existing) != expected:
                raise ValueError("Phiên bản nội dung hoặc mã chống ghi lặp đã được dùng cho dữ liệu khác.")
            return
        conn.execute(
            """
            INSERT INTO controlled_knowledge_artifact_versions (
                artifact_id, artifact_type, title, scope, version,
                content_markdown, claim_ids_json, claim_map_json, status,
                created_by, digest, created_at, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            expected,
        )

    def list_artifact_versions(self, artifact_id: str) -> list[ControlledKnowledgeArtifact]:
        """Return every immutable content version for one logical artifact."""
        self.initialize()
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT artifact_id, artifact_type, title, scope, version,
                       content_markdown, claim_ids_json, claim_map_json, status,
                       created_by, created_at
                FROM controlled_knowledge_artifact_versions
                WHERE artifact_id = ? ORDER BY created_at, version
                """,
                (artifact_id,),
            ).fetchall()
        return [
            ControlledKnowledgeArtifact(
                artifact_id=row["artifact_id"], artifact_type=row["artifact_type"],
                title=row["title"], scope=row["scope"], version=row["version"],
                content_markdown=row["content_markdown"],
                claim_ids=tuple(json.loads(row["claim_ids_json"])),
                claim_map=json.loads(row["claim_map_json"]), status=row["status"],
                created_by=row["created_by"], created_at=row["created_at"],
                decisions=tuple(self.list_decision_records(artifact_id)),
            )
            for row in rows
        ]

    def save_decision_and_artifact(
        self,
        decision: DecisionRecord,
        artifact: ControlledKnowledgeArtifact,
        idempotency_key: str,
    ) -> None:
        """Atomically append a decision and apply its matching artifact state."""
        self.initialize()
        if decision.subject_id != artifact.artifact_id:
            raise ValueError("Quyết định không thuộc đúng nội dung cần đổi trạng thái.")
        sources_json = json.dumps(list(decision.checked_source_refs), ensure_ascii=False)
        with self._connection() as conn:
            existing = conn.execute(
                """
                SELECT decision_id, subject_id, subject_digest, subject_version, decision,
                       recorded_name, machine_ref, confidence, rationale,
                       checked_source_refs_json, responsibility_acknowledged, idempotency_key
                FROM artifact_decisions
                WHERE decision_id = ? OR idempotency_key = ?
                """,
                (decision.decision_id, idempotency_key),
            ).fetchone()
            expected = (
                decision.decision_id,
                decision.subject_id,
                decision.subject_digest,
                decision.subject_version,
                decision.decision,
                decision.recorded_name,
                decision.machine_ref,
                decision.confidence,
                decision.rationale,
                sources_json,
                int(decision.responsibility_acknowledged),
                idempotency_key,
            )
            if existing is not None and tuple(existing) != expected:
                raise ValueError("Mã quyết định hoặc mã chống ghi lặp đã được dùng cho nội dung khác.")
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO artifact_decisions (
                        decision_id, subject_id, subject_digest, subject_version,
                        decision, recorded_name, machine_ref, confidence, rationale,
                        checked_source_refs_json, responsibility_acknowledged,
                        created_at, idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*expected[:-1], decision.created_at, idempotency_key),
                )
            conn.execute(
                """
                UPDATE controlled_knowledge_artifacts
                SET status = ?, idempotency_key = ?
                WHERE artifact_id = ? AND digest = ? AND version = ?
                """,
                (
                    artifact.status,
                    idempotency_key,
                    artifact.artifact_id,
                    decision.subject_digest,
                    decision.subject_version,
                ),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValueError("Nội dung đã thay đổi; hãy xem lại bản mới trước khi quyết định.")

    def list_decision_records(self, subject_id: str) -> list[DecisionRecord]:
        """Return responsibility decisions for one exact content subject."""
        self.initialize()
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT decision_id, subject_id, subject_digest, subject_version,
                       decision, recorded_name, machine_ref, confidence, rationale,
                       checked_source_refs_json, responsibility_acknowledged, created_at
                FROM artifact_decisions
                WHERE subject_id = ?
                ORDER BY created_at ASC
                """,
                (subject_id,),
            ).fetchall()
        return [
            DecisionRecord(
                decision_id=row["decision_id"],
                subject_id=row["subject_id"],
                subject_digest=row["subject_digest"],
                subject_version=row["subject_version"],
                decision=row["decision"],
                recorded_name=row["recorded_name"],
                machine_ref=row["machine_ref"],
                confidence=row["confidence"],
                rationale=row["rationale"],
                checked_source_refs=tuple(json.loads(row["checked_source_refs_json"])),
                responsibility_acknowledged=bool(row["responsibility_acknowledged"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
