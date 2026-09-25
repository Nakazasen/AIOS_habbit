"""Backfill rules for document-summary provenance."""

import json
import sqlite3

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import LocalChunkIndex
from aios_habit.rag_v2.summary_provenance import (
    apply_summary_provenance,
    plan_summary_provenance,
    summary_provenance_enabled,
)

FLAG = "AIOS_RAG_V2_SUMMARY_PROVENANCE"


def _summary(chunk_id: str, document_id: str, *, fingerprint=None, labels=(), text="summary body"):
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path="a.txt",
        source_name="a.txt",
        file_type="document_summary",
        text=text,
        normalized_text=text.lower(),
        element_ids=("summary-001",),
        element_types=("text",),
        privacy_labels=tuple(labels),
        source_fingerprint=fingerprint,
        metadata={"is_document_summary": True},
    )


def _body(chunk_id: str, document_id: str, *, fingerprint="fp-body", labels=("cloud_safe",)):
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path="a.txt",
        source_name="a.txt",
        file_type="txt",
        text="body text",
        normalized_text="body text",
        element_ids=("e1",),
        element_types=("text",),
        privacy_labels=tuple(labels),
        source_fingerprint=fingerprint,
        metadata={},
    )


@pytest.fixture
def index_path(tmp_path):
    path = tmp_path / "index.sqlite"
    with LocalChunkIndex(path) as index:
        index.upsert_chunks([
            _body("body-1", "doc-a"),
            _summary("summary-1", "doc-a"),
            _summary("summary-2", "doc-b", fingerprint="fp-existing", labels=("local_only",)),
            _body("body-2", "doc-b", fingerprint="fp-other", labels=("public",)),
        ])
    return path


def test_flag_resolver_defaults_off(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert summary_provenance_enabled() is False
    monkeypatch.setenv(FLAG, "on")
    assert summary_provenance_enabled() is True


def test_dry_run_reports_without_writing(index_path):
    plan = plan_summary_provenance(index_path)
    assert plan.summary_count == 2
    assert ("summary-1", "source_fingerprint", "fp-body") in plan.updates
    assert ("summary-1", "privacy_labels_json", json.dumps(["cloud_safe"])) in plan.updates
    assert not any(chunk_id == "summary-2" for chunk_id, _name, _value in plan.updates)

    conn = sqlite3.connect(index_path)
    row = conn.execute(
        "SELECT source_fingerprint, privacy_labels_json FROM chunks WHERE chunk_id = 'summary-1'"
    ).fetchone()
    conn.close()
    assert row == (None, "[]")


def test_apply_refuses_without_the_flag(index_path, monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    plan = plan_summary_provenance(index_path)
    with pytest.raises(RuntimeError, match="summary_provenance_disabled"):
        apply_summary_provenance(index_path, plan)


def test_apply_fills_only_missing_fields(index_path, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    plan = plan_summary_provenance(index_path)
    changed = apply_summary_provenance(index_path, plan)
    assert changed == 2

    conn = sqlite3.connect(index_path)
    rows = dict(
        (chunk_id, (fingerprint, json.loads(labels)))
        for chunk_id, fingerprint, labels in conn.execute(
            "SELECT chunk_id, source_fingerprint, privacy_labels_json FROM chunks"
        )
    )
    text = conn.execute("SELECT text FROM chunks WHERE chunk_id = 'summary-1'").fetchone()[0]
    conn.close()

    assert rows["summary-1"] == ("fp-body", ["cloud_safe"])
    assert rows["summary-2"] == ("fp-existing", ["local_only"])
    assert text == "summary body"

    # A second run has nothing left to fill.
    monkeypatch.setenv(FLAG, "1")
    assert apply_summary_provenance(index_path, plan_summary_provenance(index_path)) == 0


def test_ambiguous_body_provenance_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    path = tmp_path / "ambiguous.sqlite"
    with LocalChunkIndex(path) as index:
        index.upsert_chunks([
            _body("body-1", "doc-c", fingerprint="fp-one", labels=("cloud_safe",)),
            _body("body-2", "doc-c", fingerprint="fp-two", labels=("public",)),
            _summary("summary-3", "doc-c"),
        ])
    plan = plan_summary_provenance(path)
    assert plan.update_count == 0
    reasons = {reason for _chunk, _name, reason in plan.skipped_ambiguous}
    assert reasons == {"multiple_body_fingerprints", "multiple_body_privacy_sets"}
    assert apply_summary_provenance(path, plan) == 0


def test_summary_without_body_keeps_empty_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    path = tmp_path / "orphan.sqlite"
    with LocalChunkIndex(path) as index:
        index.upsert_chunks([_summary("summary-4", "doc-d")])
    plan = plan_summary_provenance(path)
    assert plan.update_count == 0
    assert "summary-4" in plan.skipped_no_body_value
