"""Immutable, evaluation-only SQLite registry for benchmark references.

The module deliberately has no provider or MCP dependency. It stores a captured
reference as normalized, hash-checked rows and materializes portable JSON only at
the evaluation boundary.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

SCHEMA_VERSION = 1
_ALLOWED_ANSWER_STATUSES = frozenset({"success", "not_applicable"})


class ReferenceRegistryError(RuntimeError):
    """Raised when a registry or immutable reference fails validation."""


def canonical_json(value: Any) -> str:
    """Return the canonical JSON representation used by benchmark snapshots."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decode_json(raw: str, label: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReferenceRegistryError(f"Registry contains malformed {label} JSON") from exc


def _readonly_uri(path: Path) -> str:
    return f"file:{quote(path.resolve().as_posix(), safe='/:')}?mode=ro"


def _connect(path: str | Path, *, readonly: bool) -> sqlite3.Connection:
    db_path = Path(path)
    if readonly:
        if not db_path.is_file():
            raise ReferenceRegistryError(f"Reference registry does not exist: {db_path}")
        connection = sqlite3.connect(_readonly_uri(db_path), uri=True)
        connection.execute("PRAGMA query_only = ON")
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise ReferenceRegistryError("SQLite foreign-key enforcement is unavailable")
    return connection


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    migration_note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS question_sets (
    question_set_hash TEXT PRIMARY KEY,
    questions_digest TEXT NOT NULL,
    question_count INTEGER NOT NULL CHECK (question_count > 0),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    question_set_hash TEXT NOT NULL REFERENCES question_sets(question_set_hash),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_hash TEXT NOT NULL,
    row_json TEXT NOT NULL,
    PRIMARY KEY (question_set_hash, question_id),
    UNIQUE (question_set_hash, ordinal)
);
CREATE TABLE IF NOT EXISTS reference_snapshots (
    capture_id TEXT PRIMARY KEY,
    question_set_hash TEXT NOT NULL REFERENCES question_sets(question_set_hash),
    notebook_id TEXT NOT NULL,
    notebook_title TEXT NOT NULL,
    notebook_manifest_hash TEXT NOT NULL,
    corpus_fingerprint TEXT NOT NULL,
    query_contract TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    notebook_manifest_json TEXT NOT NULL,
    top_level_json TEXT NOT NULL,
    snapshot_digest TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0 CHECK (sealed IN (0, 1))
);
CREATE TABLE IF NOT EXISTS reference_answers (
    capture_id TEXT NOT NULL REFERENCES reference_snapshots(capture_id),
    question_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    status TEXT NOT NULL,
    answer TEXT NOT NULL,
    answer_hash TEXT NOT NULL,
    error_text TEXT NOT NULL,
    reason_text TEXT NOT NULL,
    latency_ms REAL,
    row_json TEXT NOT NULL,
    PRIMARY KEY (capture_id, question_id),
    UNIQUE (capture_id, ordinal)
);
CREATE TABLE IF NOT EXISTS reference_sources (
    capture_id TEXT NOT NULL REFERENCES reference_snapshots(capture_id),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    source_identity TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    row_json TEXT NOT NULL,
    PRIMARY KEY (capture_id, ordinal)
);
CREATE TRIGGER IF NOT EXISTS sealed_snapshot_update BEFORE UPDATE ON reference_snapshots
WHEN OLD.sealed = 1 BEGIN SELECT RAISE(ABORT, 'sealed reference snapshot is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_snapshot_delete BEFORE DELETE ON reference_snapshots
WHEN OLD.sealed = 1 BEGIN SELECT RAISE(ABORT, 'sealed reference snapshot is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_answer_insert BEFORE INSERT ON reference_answers
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = NEW.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference answer is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_answer_update BEFORE UPDATE ON reference_answers
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = OLD.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference answer is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_answer_delete BEFORE DELETE ON reference_answers
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = OLD.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference answer is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_source_insert BEFORE INSERT ON reference_sources
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = NEW.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_source_update BEFORE UPDATE ON reference_sources
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = OLD.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_source_delete BEFORE DELETE ON reference_sources
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE capture_id = OLD.capture_id AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_question_insert BEFORE INSERT ON questions
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE question_set_hash = NEW.question_set_hash AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference question set is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_question_update BEFORE UPDATE ON questions
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE question_set_hash = OLD.question_set_hash AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference question set is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_question_delete BEFORE DELETE ON questions
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE question_set_hash = OLD.question_set_hash AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference question set is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_question_set_update BEFORE UPDATE ON question_sets
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE question_set_hash = OLD.question_set_hash AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference question set is immutable'); END;
CREATE TRIGGER IF NOT EXISTS sealed_question_set_delete BEFORE DELETE ON question_sets
WHEN EXISTS (SELECT 1 FROM reference_snapshots WHERE question_set_hash = OLD.question_set_hash AND sealed = 1)
BEGIN SELECT RAISE(ABORT, 'sealed reference question set is immutable'); END;
"""


def initialize_registry(path: str | Path) -> dict[str, Any]:
    """Create or validate the versioned registry schema."""
    connection = _connect(path, readonly=False)
    try:
        with connection:
            connection.executescript(_SCHEMA_SQL)
            row = connection.execute(
                "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_metadata VALUES (1, ?, datetime('now'), ?)",
                    (SCHEMA_VERSION, "initial immutable reference registry"),
                )
            elif int(row["schema_version"]) != SCHEMA_VERSION:
                raise ReferenceRegistryError(
                    f"Unsupported registry schema version: {row['schema_version']}"
                )
    finally:
        connection.close()
    return {"status": "PASS", "schema_version": SCHEMA_VERSION, "path": str(Path(path))}


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferenceRegistryError(f"Reference {label} must be an object")
    return value


def _require_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ReferenceRegistryError(f"Reference {label} must be a non-empty array")
    if not all(isinstance(row, Mapping) for row in value):
        raise ReferenceRegistryError(f"Reference {label} rows must be objects")
    return list(value)


def _validate_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = dict(payload)
    capture_id = str(snapshot.get("reference_capture_id") or "").strip()
    question_set_hash = str(snapshot.get("question_set_hash") or "").strip()
    if not capture_id or not question_set_hash:
        raise ReferenceRegistryError("Reference requires capture and question-set identities")
    questions = _require_rows(snapshot.get("questions"), "questions")
    answers = _require_rows(snapshot.get("answers"), "answers")
    manifest = _require_mapping(snapshot.get("notebook_manifest"), "notebook manifest")
    sources = _require_rows(manifest.get("sources"), "manifest sources")
    if stable_hash(sources) != str(snapshot.get("notebook_manifest_hash") or ""):
        raise ReferenceRegistryError("Reference notebook manifest hash mismatch")
    if int(manifest.get("source_count", -1)) != len(sources):
        raise ReferenceRegistryError("Reference notebook manifest source count mismatch")
    if int(manifest.get("ready_count", -1)) != len(sources) or manifest.get("all_ready") is not True:
        raise ReferenceRegistryError("Reference notebook manifest is not fully ready")

    question_ids: list[str] = []
    for row in questions:
        question_id = str(row.get("id") or "").strip()
        question_text = str(row.get("question") or "").strip()
        if not question_id or not question_text or question_id in question_ids:
            raise ReferenceRegistryError("Reference contains an invalid or duplicate question identity")
        expected_hash = stable_hash({"id": question_id, "question": question_text})
        if str(row.get("question_hash") or "") != expected_hash:
            raise ReferenceRegistryError(f"Reference question hash mismatch: {question_id}")
        question_ids.append(question_id)

    answers_by_id: dict[str, Mapping[str, Any]] = {}
    questions_by_id = {str(row["id"]): row for row in questions}
    for row in answers:
        question_id = str(row.get("question_id") or "").strip()
        if not question_id or question_id in answers_by_id or question_id not in questions_by_id:
            raise ReferenceRegistryError("Reference contains an invalid or duplicate answer identity")
        question = questions_by_id[question_id]
        if str(row.get("question") or "") != str(question["question"]):
            raise ReferenceRegistryError(f"Reference answer question mismatch: {question_id}")
        if str(row.get("question_hash") or "") != str(question["question_hash"]):
            raise ReferenceRegistryError(f"Reference answer question hash mismatch: {question_id}")
        status = str(row.get("status") or "")
        answer = str(row.get("answer") or "")
        if status not in _ALLOWED_ANSWER_STATUSES:
            raise ReferenceRegistryError(f"Reference answer status is invalid: {question_id}")
        if status == "success" and not answer.strip():
            raise ReferenceRegistryError(f"Reference success answer is empty: {question_id}")
        if status == "not_applicable" and not str(row.get("error") or row.get("reason") or "").strip():
            raise ReferenceRegistryError(f"Reference not-applicable answer lacks a reason: {question_id}")
        if stable_hash(answer) != str(row.get("answer_hash") or ""):
            raise ReferenceRegistryError(f"Reference answer hash mismatch: {question_id}")
        answers_by_id[question_id] = row
    if set(answers_by_id) != set(question_ids):
        raise ReferenceRegistryError("Reference answer coverage does not match its questions")
    return {
        "snapshot": snapshot,
        "capture_id": capture_id,
        "question_set_hash": question_set_hash,
        "questions": questions,
        "answers": answers,
        "manifest": manifest,
        "sources": sources,
        "snapshot_digest": stable_hash(snapshot),
        "questions_digest": stable_hash(questions),
    }


def _schema_version(connection: sqlite3.Connection) -> int:
    try:
        row = connection.execute(
            "SELECT schema_version FROM schema_metadata WHERE singleton = 1"
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise ReferenceRegistryError("Reference registry schema is missing or malformed") from exc
    if row is None or int(row["schema_version"]) != SCHEMA_VERSION:
        actual = "missing" if row is None else str(row["schema_version"])
        raise ReferenceRegistryError(f"Unsupported registry schema version: {actual}")
    return int(row["schema_version"])


def import_snapshot(path: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Atomically import and seal one validated portable reference snapshot."""
    validated = _validate_snapshot(_require_mapping(payload, "snapshot"))
    initialize_registry(path)
    connection = _connect(path, readonly=False)
    capture_id = validated["capture_id"]
    question_set_hash = validated["question_set_hash"]
    snapshot = validated["snapshot"]
    try:
        _schema_version(connection)
        with connection:
            duplicate = connection.execute(
                "SELECT 1 FROM reference_snapshots WHERE capture_id = ?", (capture_id,)
            ).fetchone()
            if duplicate:
                raise ReferenceRegistryError(f"Reference capture already exists: {capture_id}")
            existing_set = connection.execute(
                "SELECT questions_digest, question_count FROM question_sets WHERE question_set_hash = ?",
                (question_set_hash,),
            ).fetchone()
            if existing_set is None:
                connection.execute(
                    "INSERT INTO question_sets VALUES (?, ?, ?, datetime('now'))",
                    (question_set_hash, validated["questions_digest"], len(validated["questions"])),
                )
                for ordinal, row in enumerate(validated["questions"]):
                    connection.execute(
                        "INSERT INTO questions VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            question_set_hash,
                            ordinal,
                            str(row["id"]),
                            str(row["question"]),
                            str(row["question_hash"]),
                            canonical_json(row),
                        ),
                    )
            elif (
                str(existing_set["questions_digest"]) != validated["questions_digest"]
                or int(existing_set["question_count"]) != len(validated["questions"])
            ):
                raise ReferenceRegistryError("Question-set hash already maps to different questions")

            top_level = {
                key: value
                for key, value in snapshot.items()
                if key not in {"questions", "answers", "notebook_manifest"}
            }
            connection.execute(
                """INSERT INTO reference_snapshots (
                    capture_id, question_set_hash, notebook_id, notebook_title,
                    notebook_manifest_hash, corpus_fingerprint, query_contract,
                    captured_at, notebook_manifest_json, top_level_json,
                    snapshot_digest, sealed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    capture_id,
                    question_set_hash,
                    str(snapshot.get("notebook_id") or ""),
                    str(snapshot.get("notebook_title") or ""),
                    str(snapshot.get("notebook_manifest_hash") or ""),
                    str(snapshot.get("corpus_fingerprint") or ""),
                    str(snapshot.get("query_contract") or ""),
                    str(snapshot.get("captured_at") or ""),
                    canonical_json(validated["manifest"]),
                    canonical_json(top_level),
                    validated["snapshot_digest"],
                ),
            )
            for ordinal, row in enumerate(validated["answers"]):
                connection.execute(
                    "INSERT INTO reference_answers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        capture_id,
                        str(row["question_id"]),
                        ordinal,
                        str(row.get("status") or ""),
                        str(row.get("answer") or ""),
                        str(row.get("answer_hash") or ""),
                        str(row.get("error") or ""),
                        str(row.get("reason") or ""),
                        row.get("latency_ms"),
                        canonical_json(row),
                    ),
                )
            for ordinal, row in enumerate(validated["sources"]):
                source_identity = str(row.get("source_id") or row.get("id") or f"source-{ordinal}")
                connection.execute(
                    "INSERT INTO reference_sources VALUES (?, ?, ?, ?, ?)",
                    (capture_id, ordinal, source_identity, stable_hash(row), canonical_json(row)),
                )
            connection.execute(
                "UPDATE reference_snapshots SET sealed = 1 WHERE capture_id = ?", (capture_id,)
            )
    except sqlite3.IntegrityError as exc:
        raise ReferenceRegistryError(f"Reference import failed integrity checks: {exc}") from exc
    finally:
        connection.close()
    loaded = load_snapshot(path, capture_id)
    return {
        "status": "PASS",
        "capture_id": capture_id,
        "schema_version": SCHEMA_VERSION,
        "snapshot_digest": loaded["snapshot_digest"],
        "registry_file_sha256": loaded["registry_file_sha256"],
    }


def _materialize_snapshot(
    connection: sqlite3.Connection,
    capture_id: str,
) -> tuple[dict[str, Any], sqlite3.Row]:
    snapshot_row = connection.execute(
        "SELECT * FROM reference_snapshots WHERE capture_id = ?", (capture_id,)
    ).fetchone()
    if snapshot_row is None:
        raise ReferenceRegistryError(f"Unknown reference capture: {capture_id}")
    if int(snapshot_row["sealed"]) != 1:
        raise ReferenceRegistryError(f"Reference capture is not sealed: {capture_id}")
    question_rows = connection.execute(
        """SELECT question_id, question_text, question_hash, row_json
             FROM questions WHERE question_set_hash = ? ORDER BY ordinal""",
        (snapshot_row["question_set_hash"],),
    ).fetchall()
    answer_rows = connection.execute(
        """SELECT question_id, status, answer, answer_hash, error_text,
                  reason_text, latency_ms, row_json
             FROM reference_answers WHERE capture_id = ? ORDER BY ordinal""",
        (capture_id,),
    ).fetchall()
    source_rows = connection.execute(
        "SELECT row_json, source_hash FROM reference_sources WHERE capture_id = ? ORDER BY ordinal",
        (capture_id,),
    ).fetchall()
    questions = [_decode_json(row["row_json"], "question") for row in question_rows]
    answers = [_decode_json(row["row_json"], "answer") for row in answer_rows]
    sources = [_decode_json(row["row_json"], "source") for row in source_rows]
    for row, question in zip(question_rows, questions):
        normalized = (
            str(question.get("id") or ""),
            str(question.get("question") or ""),
            str(question.get("question_hash") or ""),
        )
        stored = (str(row["question_id"]), str(row["question_text"]), str(row["question_hash"]))
        if normalized != stored:
            raise ReferenceRegistryError("Registry question columns do not match row JSON")
    for row, answer in zip(answer_rows, answers):
        normalized = (
            str(answer.get("question_id") or ""),
            str(answer.get("status") or ""),
            str(answer.get("answer") or ""),
            str(answer.get("answer_hash") or ""),
            str(answer.get("error") or ""),
            str(answer.get("reason") or ""),
            answer.get("latency_ms"),
        )
        stored = (
            str(row["question_id"]),
            str(row["status"]),
            str(row["answer"]),
            str(row["answer_hash"]),
            str(row["error_text"]),
            str(row["reason_text"]),
            row["latency_ms"],
        )
        if normalized != stored:
            raise ReferenceRegistryError("Registry answer columns do not match row JSON")
    for row, source in zip(source_rows, sources):
        if stable_hash(source) != str(row["source_hash"]):
            raise ReferenceRegistryError("Registry source row hash mismatch")
    manifest = _decode_json(snapshot_row["notebook_manifest_json"], "manifest")
    top_level = _decode_json(snapshot_row["top_level_json"], "top-level snapshot")
    if not isinstance(manifest, dict) or not isinstance(top_level, dict):
        raise ReferenceRegistryError("Registry snapshot JSON must contain objects")
    if manifest.get("sources") != sources:
        raise ReferenceRegistryError("Registry manifest sources do not match normalized rows")
    normalized_identity = (
        str(top_level.get("reference_capture_id") or ""),
        str(top_level.get("question_set_hash") or ""),
        str(top_level.get("notebook_id") or ""),
        str(top_level.get("notebook_title") or ""),
        str(top_level.get("notebook_manifest_hash") or ""),
        str(top_level.get("corpus_fingerprint") or ""),
        str(top_level.get("query_contract") or ""),
        str(top_level.get("captured_at") or ""),
    )
    stored_identity = (
        str(snapshot_row["capture_id"]),
        str(snapshot_row["question_set_hash"]),
        str(snapshot_row["notebook_id"]),
        str(snapshot_row["notebook_title"]),
        str(snapshot_row["notebook_manifest_hash"]),
        str(snapshot_row["corpus_fingerprint"]),
        str(snapshot_row["query_contract"]),
        str(snapshot_row["captured_at"]),
    )
    if normalized_identity != stored_identity:
        raise ReferenceRegistryError("Registry snapshot columns do not match top-level JSON")
    manifest["sources"] = sources
    snapshot = dict(top_level)
    snapshot.update(
        {"questions": questions, "answers": answers, "notebook_manifest": manifest}
    )
    return snapshot, snapshot_row


def load_snapshot(path: str | Path, capture_id: str) -> dict[str, Any]:
    """Load one sealed snapshot through a strictly read-only SQLite connection."""
    db_path = Path(path)
    connection = _connect(db_path, readonly=True)
    try:
        schema_version = _schema_version(connection)
        snapshot, row = _materialize_snapshot(connection, str(capture_id))
        validated = _validate_snapshot(snapshot)
        if validated["snapshot_digest"] != str(row["snapshot_digest"]):
            raise ReferenceRegistryError("Registry snapshot digest mismatch")
        question_set = connection.execute(
            "SELECT questions_digest FROM question_sets WHERE question_set_hash = ?",
            (row["question_set_hash"],),
        ).fetchone()
        if (
            validated["question_set_hash"] != str(row["question_set_hash"])
            or question_set is None
            or validated["questions_digest"] != str(question_set["questions_digest"])
        ):
            raise ReferenceRegistryError("Registry question-set identity mismatch")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ReferenceRegistryError("Registry foreign-key check failed")
    finally:
        connection.close()
    return {
        "snapshot": snapshot,
        "schema_version": schema_version,
        "snapshot_digest": validated["snapshot_digest"],
        "registry_file_sha256": file_sha256(db_path),
    }


def list_snapshots(path: str | Path) -> list[dict[str, Any]]:
    """List provenance only; raw questions and answers are intentionally omitted."""
    connection = _connect(path, readonly=True)
    try:
        _schema_version(connection)
        rows = connection.execute(
            """SELECT capture_id, question_set_hash, notebook_id, notebook_title,
                      notebook_manifest_hash, corpus_fingerprint, query_contract,
                      captured_at, snapshot_digest, sealed
               FROM reference_snapshots ORDER BY captured_at, capture_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def verify_registry(path: str | Path, capture_id: str | None = None) -> dict[str, Any]:
    """Verify schema, FK integrity and every selected sealed snapshot digest."""
    captures = list_snapshots(path)
    selected = (
        captures
        if capture_id is None
        else [row for row in captures if row["capture_id"] == capture_id]
    )
    if capture_id is not None and not selected:
        raise ReferenceRegistryError(f"Unknown reference capture: {capture_id}")
    verified = [load_snapshot(path, str(row["capture_id"])) for row in selected]
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "capture_count": len(selected),
        "capture_ids": [str(row["capture_id"]) for row in selected],
        "snapshot_digests": [item["snapshot_digest"] for item in verified],
        "registry_file_sha256": file_sha256(path),
    }


def export_snapshot(path: str | Path, capture_id: str) -> dict[str, Any]:
    """Return the portable JSON-compatible representation of a sealed capture."""
    return load_snapshot(path, capture_id)["snapshot"]
