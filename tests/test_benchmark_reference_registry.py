from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aios_habit import benchmark_reference_registry as registry


def _snapshot() -> dict:
    questions = [
        {
            "id": "Q1",
            "question": "What is the approved launch date?",
            "category": "synthetic",
            "expected_type": "answerable",
        },
        {
            "id": "Q2",
            "question": "What unsupported detail is absent?",
            "category": "synthetic",
            "expected_type": "insufficient",
        },
    ]
    for row in questions:
        row["question_hash"] = registry.stable_hash({
            "id": row["id"],
            "question": row["question"],
        })
    sources = [{"source_id": "source-1", "title": "synthetic.txt", "status": "READY"}]
    manifest = {
        "status": "PASS",
        "notebook_id": "notebook-synthetic",
        "title": "Synthetic Reference",
        "source_count": 1,
        "ready_count": 1,
        "all_ready": True,
        "sources": sources,
        "manifest_hash": registry.stable_hash(sources),
    }
    answers = [
        {
            "question_id": "Q1",
            "question": questions[0]["question"],
            "question_hash": questions[0]["question_hash"],
            "status": "success",
            "answer": "The approved date is 2032-05-14.",
            "answer_hash": registry.stable_hash("The approved date is 2032-05-14."),
            "latency_ms": 10.0,
            "error": "",
            "reason": "",
        },
        {
            "question_id": "Q2",
            "question": questions[1]["question"],
            "question_hash": questions[1]["question_hash"],
            "status": "not_applicable",
            "answer": "",
            "answer_hash": registry.stable_hash(""),
            "latency_ms": 0.0,
            "error": "not_in_reference_corpus",
            "reason": "",
        },
    ]
    return {
        "schema_version": 1,
        "reference_capture_id": "capture-synthetic-001",
        "captured_at": "2032-05-15T00:00:00Z",
        "query_contract": "notebooklm_query_v1",
        "notebook_id": "notebook-synthetic",
        "notebook_title": "Synthetic Reference",
        "notebook_manifest_hash": registry.stable_hash(sources),
        "corpus_fingerprint": "corpus-synthetic",
        "question_set_hash": registry.stable_hash(questions),
        "questions": questions,
        "answers": answers,
        "notebook_manifest": manifest,
        "capture_config": {"temperature": 0},
    }


def test_registry_round_trip_and_provenance_only_list(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    snapshot = _snapshot()

    imported = registry.import_snapshot(path, snapshot)
    loaded = registry.load_snapshot(path, snapshot["reference_capture_id"])
    listed = registry.list_snapshots(path)
    verified = registry.verify_registry(path)

    assert loaded["snapshot"] == snapshot
    assert registry.export_snapshot(path, snapshot["reference_capture_id"]) == snapshot
    assert imported["snapshot_digest"] == registry.stable_hash(snapshot)
    assert verified["capture_ids"] == [snapshot["reference_capture_id"]]
    assert listed[0]["sealed"] == 1
    assert "answer" not in json.dumps(listed).lower()


def test_registry_rejects_duplicate_capture(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    snapshot = _snapshot()
    registry.import_snapshot(path, snapshot)

    with pytest.raises(registry.ReferenceRegistryError, match="already exists"):
        registry.import_snapshot(path, snapshot)


def test_registry_rolls_back_partial_import(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    registry.initialize_registry(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TRIGGER force_second_answer_failure
               BEFORE INSERT ON reference_answers WHEN NEW.ordinal = 1
               BEGIN SELECT RAISE(ABORT, 'test forced failure'); END"""
        )

    with pytest.raises(registry.ReferenceRegistryError, match="integrity checks"):
        registry.import_snapshot(path, _snapshot())

    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reference_snapshots").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM reference_answers").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM question_sets").fetchone()[0] == 0


def test_sealed_rows_reject_sql_mutation(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    snapshot = _snapshot()
    registry.import_snapshot(path, snapshot)

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE reference_answers SET answer = ? WHERE capture_id = ?",
                ("tampered", snapshot["reference_capture_id"]),
            )


def test_load_detects_cross_column_tampering(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    snapshot = _snapshot()
    registry.import_snapshot(path, snapshot)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER sealed_answer_update")
        connection.execute(
            "UPDATE reference_answers SET answer = ? WHERE capture_id = ? AND question_id = ?",
            ("tampered", snapshot["reference_capture_id"], "Q1"),
        )

    with pytest.raises(registry.ReferenceRegistryError, match="columns do not match"):
        registry.load_snapshot(path, snapshot["reference_capture_id"])


def test_read_only_load_does_not_mutate_registry(tmp_path: Path):
    path = tmp_path / "references.sqlite3"
    snapshot = _snapshot()
    registry.import_snapshot(path, snapshot)
    before = registry.file_sha256(path)

    loaded = registry.load_snapshot(path, snapshot["reference_capture_id"])

    assert loaded["snapshot_digest"] == registry.stable_hash(snapshot)
    assert registry.file_sha256(path) == before


def test_invalid_answer_hash_is_rejected_before_import(tmp_path: Path):
    snapshot = _snapshot()
    snapshot["answers"][0]["answer_hash"] = "0" * 64

    with pytest.raises(registry.ReferenceRegistryError, match="answer hash mismatch"):
        registry.import_snapshot(tmp_path / "references.sqlite3", snapshot)
