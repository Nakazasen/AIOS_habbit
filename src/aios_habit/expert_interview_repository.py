"""SQLite repository for append-only and idempotent persistence of interview sessions, turns, and checkpoints.

Implements T031 of 010-expert-knowledge-acquisition.
Follows ADR-0009 and data-model.md.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from aios_habit.expert_interview_models import (
    InterviewCheckpoint,
    InterviewSession,
    InterviewTurn,
)
from aios_habit.local_transcription import (
    AudioPathSecurityError,
    ConsentRecord,
    TranscriptionReceipt,
    TranscriptionSegment,
    validate_local_only_audio_path,
)


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
                    segments_json TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    all_critical_tokens_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS interview_transcripts_session_idx ON interview_transcripts(session_id)")

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
        """Idempotently save transcription receipt, validating local_only audio boundary."""
        self.initialize()
        if local_only_root:
            validate_local_only_audio_path(Path(receipt.audio_path), local_only_root)

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
        segments_json = json.dumps(segments_data, ensure_ascii=False)
        critical_json = json.dumps(list(receipt.all_critical_tokens), ensure_ascii=False)

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO interview_transcripts (
                    receipt_id, session_id, audio_path, audio_digest,
                    engine_name, engine_version, segments_json, full_text,
                    all_critical_tokens_json, state, created_at, idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    state = excluded.state,
                    segments_json = excluded.segments_json,
                    full_text = excluded.full_text,
                    all_critical_tokens_json = excluded.all_critical_tokens_json
                """,
                (
                    receipt.receipt_id,
                    receipt.session_id,
                    receipt.audio_path,
                    receipt.audio_digest,
                    receipt.engine_name,
                    receipt.engine_version,
                    segments_json,
                    receipt.full_text,
                    critical_json,
                    receipt.state,
                    receipt.created_at,
                    idempotency_key,
                ),
            )

    def get_transcription_receipt(self, session_id: str) -> Optional[TranscriptionReceipt]:
        """Fetch transcription receipt for a session."""
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT receipt_id, session_id, audio_path, audio_digest,
                       engine_name, engine_version, segments_json, full_text,
                       all_critical_tokens_json, state, created_at
                FROM interview_transcripts
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None

            segments_raw = json.loads(row["segments_json"])
            segments = tuple(
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
            )
            critical_tokens = tuple(json.loads(row["all_critical_tokens_json"]))

            return TranscriptionReceipt(
                receipt_id=row["receipt_id"],
                session_id=row["session_id"],
                audio_path=row["audio_path"],
                audio_digest=row["audio_digest"],
                engine_name=row["engine_name"],
                engine_version=row["engine_version"],
                segments=segments,
                full_text=row["full_text"],
                all_critical_tokens=critical_tokens,
                state=row["state"],
                created_at=row["created_at"],
            )
