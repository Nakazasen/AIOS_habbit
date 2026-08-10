from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from aios_habit import benchmark_reference_acquisition as acquisition
from aios_habit.benchmark_reference_registry import stable_hash


def _questions() -> list[dict]:
    rows = [
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
    return acquisition.question_rows(rows)


def _manifest() -> dict:
    sources = [
        {
            "source_id": "source-1",
            "title": "synthetic.txt",
            "status": "READY",
        }
    ]
    return {
        "status": "PASS",
        "notebook_id": "notebook-synthetic",
        "title": "Synthetic Reference",
        "source_count": 1,
        "ready_count": 1,
        "all_ready": True,
        "sources": sources,
        "manifest_hash": stable_hash(sources),
    }


def _identity(*, profile: str = "profile-synthetic") -> dict:
    questions = _questions()
    manifest = _manifest()
    return {
        "notebook_id": manifest["notebook_id"],
        "notebook_title": manifest["title"],
        "notebook_manifest_hash": manifest["manifest_hash"],
        "question_set_hash": stable_hash(questions),
        "query_contract": "notebooklm_query_v1",
        "profile": profile,
        "corpus_fingerprint": "corpus-synthetic",
        "source_root_name": "synthetic-root",
        "corpus_audit_hash": "audit-synthetic",
    }


def _create(path: Path) -> dict:
    identity = _identity()
    return acquisition.create_or_resume_run(
        path,
        acquisition_id=acquisition.default_acquisition_id(identity),
        identity=identity,
        notebook_manifest=_manifest(),
        questions=_questions(),
    )


def _success(answer: str = "The approved date is 2032-05-14.") -> dict:
    return {
        "status": "success",
        "answer": answer,
        "provider_response": {"answer": answer, "citations": []},
        "latency_ms": 10.0,
        "attempt_count": 1,
        "captured_at": "2032-05-15T00:00:00Z",
    }


def _not_applicable() -> dict:
    return {
        "status": "not_applicable",
        "answer": "",
        "provider_response": {},
        "error": "not_in_reference_corpus",
        "reason": "",
        "latency_ms": 0.0,
        "attempt_count": 1,
        "captured_at": "2032-05-15T00:00:01Z",
    }


def test_commits_each_question_and_resumes_without_requery(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    questions = _questions()

    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=0,
        question=questions[0],
        result=_success(),
    )

    resumed = _create(path)
    assert resumed["resumed"] is True
    assert resumed["completed_question_count"] == 1
    assert acquisition.completed_question_ids(
        path, created["acquisition_id"], questions
    ) == {"Q1"}

    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=1,
        question=questions[1],
        result=_not_applicable(),
    )
    acquisition.mark_complete(path, created["acquisition_id"], questions)
    rows = acquisition.load_complete_rows(path, created["acquisition_id"], questions)

    assert [row["question_id"] for row in rows] == ["Q1", "Q2"]
    assert [row["status"] for row in rows] == ["success", "not_applicable"]


def test_incomplete_acquisition_cannot_be_loaded_or_completed(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    questions = _questions()
    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=0,
        question=questions[0],
        result=_success(),
    )

    with pytest.raises(acquisition.ReferenceAcquisitionError, match="incomplete"):
        acquisition.load_complete_rows(path, created["acquisition_id"], questions)
    with pytest.raises(acquisition.ReferenceAcquisitionError, match="incomplete"):
        acquisition.mark_complete(path, created["acquisition_id"], questions)


def test_resume_rejects_identity_and_question_metadata_drift(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    identity = _identity(profile="different-profile")

    with pytest.raises(acquisition.ReferenceAcquisitionError, match="identity mismatch"):
        acquisition.create_or_resume_run(
            path,
            acquisition_id=created["acquisition_id"],
            identity=identity,
            notebook_manifest=_manifest(),
            questions=_questions(),
            capture_id=created["capture_id"],
        )

    drifted_questions = _questions()
    drifted_questions[0]["category"] = "changed-category"
    drifted_identity = _identity()
    with pytest.raises(acquisition.ReferenceAcquisitionError, match="question-set hash mismatch"):
        acquisition.create_or_resume_run(
            tmp_path / "drift.sqlite3",
            acquisition_id="drift",
            identity=drifted_identity,
            notebook_manifest=_manifest(),
            questions=drifted_questions,
        )


def test_resume_detects_cross_column_tampering(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    questions = _questions()
    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=0,
        question=questions[0],
        result=_success(),
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE acquisition_rows SET answer = ? WHERE acquisition_id = ? AND question_id = ?",
            ("tampered", created["acquisition_id"], "Q1"),
        )

    with pytest.raises(acquisition.ReferenceAcquisitionError, match="columns do not match"):
        acquisition.completed_question_ids(path, created["acquisition_id"], questions)


def test_rejects_authentication_material_in_provider_payload(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    result = _success()
    result["provider_response"] = {
        "answer": result["answer"],
        "metadata": {"access_token": "must-never-be-stored"},
    }

    with pytest.raises(acquisition.ReferenceAcquisitionError, match="authentication material"):
        acquisition.commit_question_result(
            path,
            created["acquisition_id"],
            ordinal=0,
            question=_questions()[0],
            result=result,
        )
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisition_rows").fetchone()[0] == 0


def test_sealed_rows_are_immutable(tmp_path: Path):
    path = tmp_path / "acquisition.sqlite3"
    created = _create(path)
    questions = _questions()
    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=0,
        question=questions[0],
        result=_success(),
    )
    acquisition.commit_question_result(
        path,
        created["acquisition_id"],
        ordinal=1,
        question=questions[1],
        result=_not_applicable(),
    )
    acquisition.mark_complete(path, created["acquisition_id"], questions)
    acquisition.mark_sealed(
        path,
        created["acquisition_id"],
        capture_id=created["capture_id"],
        snapshot_digest="a" * 64,
    )

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE acquisition_rows SET answer = ? WHERE acquisition_id = ?",
                ("tampered", created["acquisition_id"]),
            )
    with pytest.raises(acquisition.ReferenceAcquisitionError, match="immutable"):
        acquisition.set_run_status(path, created["acquisition_id"], "ACQUIRING")