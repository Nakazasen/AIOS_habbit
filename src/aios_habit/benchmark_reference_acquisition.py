"""Provider-free SQLite staging for durable NotebookLM benchmark acquisition."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from aios_habit.benchmark_reference_registry import canonical_json, stable_hash

SCHEMA_VERSION = 1
RUN_STATUSES = frozenset({"ACQUIRING", "WAITING_FOR_AUTH", "INTERRUPTED", "COMPLETE", "SEALED"})
ROW_STATUSES = frozenset({"success", "not_applicable"})
ERROR_CODES = frozenset({"", "auth_required", "timeout", "provider_error", "invalid_json", "empty_answer", "interrupted"})
_FORBIDDEN_KEY = re.compile(
    r"(?:authorization|cookie|credential|access[_-]?token|refresh[_-]?token|"
    r"browser[_-]?profile|profile[_-]?path|credential[_-]?path)",
    re.IGNORECASE,
)


class ReferenceAcquisitionError(RuntimeError):
    """Raised when acquisition staging fails closed validation."""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def acquisition_identity_hash(identity: Mapping[str, Any]) -> str:
    return stable_hash(dict(identity))


def default_acquisition_id(identity: Mapping[str, Any]) -> str:
    return f"NLM-ACQUIRE-{acquisition_identity_hash(identity)[:20]}"


def default_capture_id(identity: Mapping[str, Any]) -> str:
    return f"NLM-REFERENCE-{acquisition_identity_hash(identity)[:20]}"


def _connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise ReferenceAcquisitionError("SQLite foreign-key enforcement is unavailable")
    return connection


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acquisition_runs (
    acquisition_id TEXT PRIMARY KEY,
    identity_hash TEXT NOT NULL,
    expected_question_count INTEGER NOT NULL CHECK (expected_question_count > 0),
    notebook_manifest_json TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    identity_json TEXT NOT NULL,
    status TEXT NOT NULL,
    last_error_code TEXT NOT NULL DEFAULT '',
    capture_id TEXT NOT NULL,
    snapshot_digest TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acquisition_rows (
    acquisition_id TEXT NOT NULL REFERENCES acquisition_runs(acquisition_id),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    question_id TEXT NOT NULL,
    question_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    answer TEXT NOT NULL,
    answer_hash TEXT NOT NULL,
    provider_payload_json TEXT NOT NULL,
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    latency_ms REAL NOT NULL CHECK (latency_ms >= 0),
    captured_at TEXT NOT NULL,
    row_json TEXT NOT NULL,
    PRIMARY KEY (acquisition_id, question_id),
    UNIQUE (acquisition_id, ordinal)
);
CREATE TRIGGER IF NOT EXISTS sealed_acquisition_row_insert BEFORE INSERT ON acquisition_rows
WHEN EXISTS (
    SELECT 1 FROM acquisition_runs
    WHERE acquisition_id = NEW.acquisition_id AND status = 'SEALED'
)
BEGIN SELECT RAISE(ABORT, 'sealed acquisition is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_acquisition_row_update BEFORE UPDATE ON acquisition_rows
WHEN EXISTS (
    SELECT 1 FROM acquisition_runs
    WHERE acquisition_id = OLD.acquisition_id AND status = 'SEALED'
)
BEGIN SELECT RAISE(ABORT, 'sealed acquisition is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_acquisition_row_delete BEFORE DELETE ON acquisition_rows
WHEN EXISTS (
    SELECT 1 FROM acquisition_runs
    WHERE acquisition_id = OLD.acquisition_id AND status = 'SEALED'
)
BEGIN SELECT RAISE(ABORT, 'sealed acquisition is immutable'); END;
"""


def initialize_database(path: str | Path) -> dict[str, Any]:
    connection = _connect(path)
    try:
        with connection:
            connection.executescript(_SCHEMA_SQL)
            row = connection.execute(
                "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_metadata VALUES (1, ?, ?)",
                    (SCHEMA_VERSION, utc_now()),
                )
            elif int(row["schema_version"]) != SCHEMA_VERSION:
                raise ReferenceAcquisitionError(
                    f"Unsupported acquisition schema version: {row['schema_version']}"
                )
    finally:
        connection.close()
    return {"status": "PASS", "schema_version": SCHEMA_VERSION, "path": str(Path(path))}


def _validate_schema(connection: sqlite3.Connection) -> None:
    try:
        row = connection.execute(
            "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise ReferenceAcquisitionError("Acquisition staging schema is missing or malformed") from exc
    if row is None or int(row["schema_version"]) != SCHEMA_VERSION:
        actual = "missing" if row is None else str(row["schema_version"])
        raise ReferenceAcquisitionError(f"Unsupported acquisition schema version: {actual}")


def question_rows(questions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not questions:
        raise ReferenceAcquisitionError("Acquisition requires a non-empty question set")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in questions:
        question_id = str(raw.get("id") or "").strip()
        question = str(raw.get("question") or "").strip()
        if not question_id or not question or question_id in seen:
            raise ReferenceAcquisitionError("Acquisition contains an invalid or duplicate question")
        expected_hash = stable_hash({"id": question_id, "question": question})
        supplied_hash = str(raw.get("question_hash") or "")
        if supplied_hash and supplied_hash != expected_hash:
            raise ReferenceAcquisitionError(
                f"Acquisition question hash mismatch: {question_id}"
            )
        seen.add(question_id)
        row = dict(raw)
        row["id"] = question_id
        row["question"] = question
        row["question_hash"] = expected_hash
        rows.append(row)
    return rows


def _normalized_identity(identity: Mapping[str, Any]) -> dict[str, str]:
    required = (
        "notebook_id",
        "notebook_title",
        "notebook_manifest_hash",
        "question_set_hash",
        "query_contract",
        "profile",
        "corpus_fingerprint",
        "source_root_name",
        "corpus_audit_hash",
    )
    result = {key: str(identity.get(key) or "").strip() for key in required}
    missing = [key for key, value in result.items() if not value]
    if missing:
        raise ReferenceAcquisitionError(
            "Acquisition identity is incomplete: " + ", ".join(missing)
        )
    return result


def _validate_manifest(manifest: Mapping[str, Any], identity: Mapping[str, str]) -> None:
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ReferenceAcquisitionError("Acquisition notebook manifest has no sources")
    if stable_hash(sources) != identity["notebook_manifest_hash"]:
        raise ReferenceAcquisitionError("Acquisition notebook manifest hash mismatch")
    if (
        str(manifest.get("notebook_id") or "") != identity["notebook_id"]
        or str(manifest.get("title") or "") != identity["notebook_title"]
    ):
        raise ReferenceAcquisitionError("Acquisition notebook identity mismatch")
    if (
        int(manifest.get("source_count", -1)) != len(sources)
        or int(manifest.get("ready_count", -1)) != len(sources)
        or manifest.get("all_ready") is not True
    ):
        raise ReferenceAcquisitionError("Acquisition notebook sources are not fully ready")


def create_or_resume_run(
    path: str | Path,
    *,
    acquisition_id: str,
    identity: Mapping[str, Any],
    notebook_manifest: Mapping[str, Any],
    questions: Sequence[Mapping[str, Any]],
    capture_id: str = "",
) -> dict[str, Any]:
    """Create a run or resume it only when every sealed identity is exact."""
    normalized = _normalized_identity(identity)
    expected_questions = question_rows(questions)
    if stable_hash(expected_questions) != normalized["question_set_hash"]:
        raise ReferenceAcquisitionError("Acquisition question-set hash mismatch")
    _validate_manifest(notebook_manifest, normalized)
    identity_hash = acquisition_identity_hash(normalized)
    acquisition_id = str(acquisition_id or "").strip()
    if not acquisition_id:
        raise ReferenceAcquisitionError("Acquisition ID is required")
    capture_id = str(capture_id or default_capture_id(normalized)).strip()
    expected = {
        "identity_hash": identity_hash,
        "notebook_manifest_json": canonical_json(dict(notebook_manifest)),
        "questions_json": canonical_json(expected_questions),
        "identity_json": canonical_json(normalized),
        "capture_id": capture_id,
    }
    initialize_database(path)
    connection = _connect(path)
    try:
        _validate_schema(connection)
        existing = connection.execute(
            "SELECT * FROM acquisition_runs WHERE acquisition_id = ?", (acquisition_id,)
        ).fetchone()
        now = utc_now()
        if existing is None:
            with connection:
                connection.execute(
                    """INSERT INTO acquisition_runs VALUES (
                        ?, ?, ?, ?, ?, ?, 'ACQUIRING', '', ?, '', ?, ?
                    )""",
                    (
                        acquisition_id,
                        identity_hash,
                        len(expected_questions),
                        expected["notebook_manifest_json"],
                        expected["questions_json"],
                        expected["identity_json"],
                        capture_id,
                        now,
                        now,
                    ),
                )
            resumed, status = False, "ACQUIRING"
        else:
            mismatches = [
                key for key, value in expected.items() if str(existing[key]) != value
            ]
            if int(existing["expected_question_count"]) != len(expected_questions):
                mismatches.append("expected_question_count")
            if mismatches:
                raise ReferenceAcquisitionError(
                    "Acquisition resume identity mismatch: " + ", ".join(mismatches)
                )
            status = str(existing["status"])
            if status not in RUN_STATUSES:
                raise ReferenceAcquisitionError(f"Acquisition run status is invalid: {status}")
            resumed = True
    finally:
        connection.close()
    completed = completed_question_ids(path, acquisition_id, questions)
    return {
        "status": status,
        "acquisition_id": acquisition_id,
        "capture_id": capture_id,
        "resumed": resumed,
        "completed_question_count": len(completed),
        "expected_question_count": len(expected_questions),
    }


def _reject_sensitive_keys(value: Any, path: str = "provider_response") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _FORBIDDEN_KEY.search(str(key)):
                raise ReferenceAcquisitionError(
                    f"Provider payload contains forbidden authentication material at {path}"
                )
            _reject_sensitive_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_keys(nested, f"{path}[{index}]")


def _load_run(connection: sqlite3.Connection, acquisition_id: str) -> sqlite3.Row:
    _validate_schema(connection)
    row = connection.execute(
        "SELECT * FROM acquisition_runs WHERE acquisition_id = ?", (acquisition_id,)
    ).fetchone()
    if row is None:
        raise ReferenceAcquisitionError(f"Unknown acquisition run: {acquisition_id}")
    if str(row["status"]) not in RUN_STATUSES:
        raise ReferenceAcquisitionError("Stored acquisition run status is invalid")
    try:
        identity = json.loads(str(row["identity_json"]))
    except json.JSONDecodeError as exc:
        raise ReferenceAcquisitionError("Stored acquisition identity is malformed") from exc
    if stable_hash(identity) != str(row["identity_hash"]):
        raise ReferenceAcquisitionError("Stored acquisition identity hash mismatch")
    return row


def _stored_questions(run: sqlite3.Row) -> list[dict[str, str]]:
    try:
        rows = json.loads(str(run["questions_json"]))
    except json.JSONDecodeError as exc:
        raise ReferenceAcquisitionError("Stored acquisition questions are malformed") from exc
    if not isinstance(rows, list):
        raise ReferenceAcquisitionError("Stored acquisition questions are not an array")
    return rows


def _validate_stored_row(raw: sqlite3.Row, expected: Mapping[str, Any]) -> dict[str, Any]:
    try:
        row = json.loads(str(raw["row_json"]))
        provider = json.loads(str(raw["provider_payload_json"]))
    except json.JSONDecodeError as exc:
        raise ReferenceAcquisitionError("Stored acquisition row contains malformed JSON") from exc
    columns = {
        "question_id": str(raw["question_id"]),
        "question_hash": str(raw["question_hash"]),
        "status": str(raw["status"]),
        "answer": str(raw["answer"]),
        "answer_hash": str(raw["answer_hash"]),
        "provider_response": provider,
        "attempt_count": int(raw["attempt_count"]),
        "latency_ms": float(raw["latency_ms"]),
        "captured_at": str(raw["captured_at"]),
    }
    if not isinstance(row, Mapping) or any(row.get(key) != value for key, value in columns.items()):
        raise ReferenceAcquisitionError(
            f"Stored acquisition row columns do not match row JSON: {raw['question_id']}"
        )
    if (
        str(raw["question_id"]) != str(expected["id"])
        or str(raw["question_hash"]) != str(expected["question_hash"])
    ):
        raise ReferenceAcquisitionError("Stored acquisition question identity mismatch")
    status, answer = str(raw["status"]), str(raw["answer"])
    if status not in ROW_STATUSES or (status == "success" and not answer.strip()):
        raise ReferenceAcquisitionError("Stored acquisition answer status is invalid")
    if status == "not_applicable" and not str(row.get("error") or row.get("reason") or "").strip():
        raise ReferenceAcquisitionError("Stored not-applicable row lacks a reason")
    if stable_hash(answer) != str(raw["answer_hash"]):
        raise ReferenceAcquisitionError(
            f"Stored acquisition answer hash mismatch: {raw['question_id']}"
        )
    _reject_sensitive_keys(provider)
    return dict(row)


def completed_question_ids(
    path: str | Path,
    acquisition_id: str,
    questions: Sequence[Mapping[str, Any]],
) -> set[str]:
    expected = question_rows(questions)
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        if _stored_questions(run) != expected:
            raise ReferenceAcquisitionError("Acquisition question identities drifted on resume")
        raw_rows = connection.execute(
            "SELECT * FROM acquisition_rows WHERE acquisition_id = ? ORDER BY ordinal",
            (acquisition_id,),
        ).fetchall()
        completed: set[str] = set()
        for raw in raw_rows:
            ordinal = int(raw["ordinal"])
            if ordinal >= len(expected):
                raise ReferenceAcquisitionError("Acquisition row ordinal is out of range")
            _validate_stored_row(raw, expected[ordinal])
            completed.add(str(raw["question_id"]))
        return completed
    finally:
        connection.close()


def commit_question_result(
    path: str | Path,
    acquisition_id: str,
    *,
    ordinal: int,
    question: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Commit one final row independently; duplicate success is never overwritten."""
    expected = question_rows([question])[0]
    status, answer = str(result.get("status") or ""), str(result.get("answer") or "")
    error, reason = str(result.get("error") or ""), str(result.get("reason") or "")
    if status not in ROW_STATUSES or (status == "success" and not answer.strip()):
        raise ReferenceAcquisitionError(f"Cannot checkpoint answer status: {status}")
    if status == "not_applicable" and not (error or reason):
        raise ReferenceAcquisitionError("Not-applicable answer requires a reason")
    provider = result.get("provider_response", {})
    if not isinstance(provider, (Mapping, list)):
        raise ReferenceAcquisitionError("Provider payload must be an object or array")
    _reject_sensitive_keys(provider)
    attempts = int(result.get("attempt_count", 0))
    latency = float(result.get("latency_ms", 0.0))
    if attempts < 0 or latency < 0:
        raise ReferenceAcquisitionError("Acquisition attempts and latency must be non-negative")
    captured_at = str(result.get("captured_at") or utc_now())
    row = {
        "question_id": expected["id"],
        "question": expected["question"],
        "question_hash": expected["question_hash"],
        "status": status,
        "answer": answer,
        "answer_hash": stable_hash(answer),
        "provider_response": provider,
        "latency_ms": latency,
        "error": error,
        "reason": reason,
        "attempt_count": attempts,
        "captured_at": captured_at,
    }
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        stored_questions = _stored_questions(run)
        if (
            ordinal < 0
            or ordinal >= len(stored_questions)
            or stored_questions[ordinal] != expected
        ):
            raise ReferenceAcquisitionError("Acquisition row does not match its sealed ordinal")
        existing = connection.execute(
            "SELECT * FROM acquisition_rows WHERE acquisition_id = ? AND question_id = ?",
            (acquisition_id, expected["id"]),
        ).fetchone()
        if existing is not None:
            if _validate_stored_row(existing, expected) != row:
                raise ReferenceAcquisitionError(
                    f"Completed row already has different evidence: {expected['id']}"
                )
            return {"status": "REUSED", "question_id": expected["id"]}
        with connection:
            connection.execute(
                "INSERT INTO acquisition_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    acquisition_id,
                    ordinal,
                    expected["id"],
                    expected["question_hash"],
                    status,
                    answer,
                    row["answer_hash"],
                    canonical_json(provider),
                    attempts,
                    latency,
                    captured_at,
                    canonical_json(row),
                ),
            )
            connection.execute(
                """UPDATE acquisition_runs
                   SET status = 'ACQUIRING', last_error_code = '', updated_at = ?
                   WHERE acquisition_id = ?""",
                (utc_now(), acquisition_id),
            )
    except sqlite3.IntegrityError as exc:
        raise ReferenceAcquisitionError(
            f"Acquisition row failed integrity checks: {exc}"
        ) from exc
    finally:
        connection.close()
    return {"status": "COMMITTED", "question_id": expected["id"]}


def set_run_status(
    path: str | Path,
    acquisition_id: str,
    status: str,
    *,
    error_code: str = "",
) -> dict[str, Any]:
    """Store a classified code only, never raw CLI output or credentials."""
    if status not in RUN_STATUSES or error_code not in ERROR_CODES:
        raise ReferenceAcquisitionError("Invalid acquisition status or classified error code")
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        if str(run["status"]) == "SEALED" and status != "SEALED":
            raise ReferenceAcquisitionError("Sealed acquisition status is immutable")
        with connection:
            connection.execute(
                """UPDATE acquisition_runs
                   SET status = ?, last_error_code = ?, updated_at = ?
                   WHERE acquisition_id = ?""",
                (status, error_code, utc_now(), acquisition_id),
            )
    finally:
        connection.close()
    return {"status": status, "acquisition_id": acquisition_id, "error_code": error_code}


def load_run_context(path: str | Path, acquisition_id: str) -> dict[str, Any]:
    """Load the exact identity-bound context required by the offline finalizer."""
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        try:
            identity = json.loads(str(run["identity_json"]))
            notebook_manifest = json.loads(str(run["notebook_manifest_json"]))
        except json.JSONDecodeError as exc:
            raise ReferenceAcquisitionError("Stored acquisition context is malformed") from exc
        questions = _stored_questions(run)
        normalized_identity = _normalized_identity(identity)
        if normalized_identity != identity:
            raise ReferenceAcquisitionError("Stored acquisition identity is not canonical")
        if stable_hash(questions) != normalized_identity["question_set_hash"]:
            raise ReferenceAcquisitionError("Stored acquisition question-set hash mismatch")
        if not isinstance(notebook_manifest, Mapping):
            raise ReferenceAcquisitionError("Stored notebook manifest is not an object")
        _validate_manifest(notebook_manifest, normalized_identity)
        if len(questions) != int(run["expected_question_count"]):
            raise ReferenceAcquisitionError("Stored acquisition question count mismatch")
        return {
            "acquisition_id": str(run["acquisition_id"]),
            "capture_id": str(run["capture_id"]),
            "status": str(run["status"]),
            "identity": normalized_identity,
            "notebook_manifest": dict(notebook_manifest),
            "questions": questions,
            "created_at": str(run["created_at"]),
            "updated_at": str(run["updated_at"]),
            "snapshot_digest": str(run["snapshot_digest"]),
        }
    finally:
        connection.close()


def load_complete_rows(
    path: str | Path,
    acquisition_id: str,
    questions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return ordered, hash-verified rows only after complete question coverage."""
    expected = question_rows(questions)
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        if _stored_questions(run) != expected:
            raise ReferenceAcquisitionError("Acquisition question identities drifted")
        raw_rows = connection.execute(
            "SELECT * FROM acquisition_rows WHERE acquisition_id = ? ORDER BY ordinal",
            (acquisition_id,),
        ).fetchall()
        if len(raw_rows) != len(expected):
            raise ReferenceAcquisitionError(
                f"Acquisition is incomplete: {len(raw_rows)}/{len(expected)} rows"
            )
        rows: list[dict[str, Any]] = []
        for ordinal, (raw, question) in enumerate(zip(raw_rows, expected)):
            if int(raw["ordinal"]) != ordinal:
                raise ReferenceAcquisitionError(
                    "Acquisition row ordering is incomplete or malformed"
                )
            rows.append(_validate_stored_row(raw, question))
        return rows
    finally:
        connection.close()


def mark_complete(
    path: str | Path,
    acquisition_id: str,
    questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    load_complete_rows(path, acquisition_id, questions)
    return set_run_status(path, acquisition_id, "COMPLETE")


def mark_sealed(
    path: str | Path,
    acquisition_id: str,
    *,
    capture_id: str,
    snapshot_digest: str,
) -> dict[str, Any]:
    if not str(snapshot_digest or "").strip():
        raise ReferenceAcquisitionError("Snapshot digest is required before sealing staging")
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        if (
            str(run["capture_id"]) != str(capture_id)
            or str(run["status"]) not in {"COMPLETE", "SEALED"}
        ):
            raise ReferenceAcquisitionError(
                "Only the identity-bound complete acquisition can be sealed"
            )
        if (
            str(run["status"]) == "SEALED"
            and str(run["snapshot_digest"]) != str(snapshot_digest)
        ):
            raise ReferenceAcquisitionError("Sealed acquisition snapshot digest mismatch")
        with connection:
            connection.execute(
                """UPDATE acquisition_runs
                   SET status = 'SEALED', snapshot_digest = ?, updated_at = ?
                   WHERE acquisition_id = ?""",
                (str(snapshot_digest), utc_now(), acquisition_id),
            )
    finally:
        connection.close()
    return {"status": "SEALED", "acquisition_id": acquisition_id, "capture_id": capture_id}


def run_summary(path: str | Path, acquisition_id: str) -> dict[str, Any]:
    """Return provenance and counts only; raw questions and answers are omitted."""
    connection = _connect(path)
    try:
        run = _load_run(connection, acquisition_id)
        count = int(connection.execute(
            "SELECT COUNT(*) FROM acquisition_rows WHERE acquisition_id = ?",
            (acquisition_id,),
        ).fetchone()[0])
        identity = json.loads(str(run["identity_json"]))
        return {
            "status": str(run["status"]),
            "acquisition_id": acquisition_id,
            "capture_id": str(run["capture_id"]),
            "identity_hash": str(run["identity_hash"]),
            "notebook_manifest_hash": str(identity["notebook_manifest_hash"]),
            "question_set_hash": str(identity["question_set_hash"]),
            "query_contract": str(identity["query_contract"]),
            "profile": str(identity["profile"]),
            "completed_question_count": count,
            "expected_question_count": int(run["expected_question_count"]),
            "last_error_code": str(run["last_error_code"]),
            "snapshot_digest": str(run["snapshot_digest"]),
            "created_at": str(run["created_at"]),
            "updated_at": str(run["updated_at"]),
        }
    finally:
        connection.close()