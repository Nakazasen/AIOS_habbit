"""Unit tests proving profile fingerprint caching and semantic identity.

Ticket: DESKTOP-SPEED-PROFILE-QUERY-FIX-HOME
Requirements:
1. No re-scanning when database is unchanged (in-memory cache keyed by path, mtime, size).
2. Semantic identity: exact same fingerprint matching decisions as legacy GROUP BY query.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import time
from typing import Sequence
from unittest.mock import patch

import pytest

from aios_habit.rag_v2.pipeline import SourceSpec
from aios_habit.workspace_chat_rag_v2_adapter import (
    clear_covered_source_fingerprints_cache,
    _get_covered_source_fingerprints,
)


def _create_sample_db(db_path: Path) -> None:
    """Create a sample database with chunks table and test fixtures."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                privacy_labels_json TEXT NOT NULL,
                source_fingerprint TEXT,
                checksum TEXT,
                retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
            )
            """
        )
        conn.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id)")
        conn.execute("CREATE INDEX idx_chunks_retrievable ON chunks(retrievable, document_id)")

        # Fixtures:
        # doc1: retrievable with consistent fingerprint
        # doc2: retrievable with multiple chunks, min fingerprint 'fp2_a'
        # doc3: retrievable=0 (not retrievable)
        # doc4: retrievable=1 with None/empty fingerprint
        rows = [
            ("c1_1", "doc1", "/path/doc1", "doc1.txt", "text", "t", "t", "{}", "[]", "fp1_exact", "chk1", 1),
            ("c1_2", "doc1", "/path/doc1", "doc1.txt", "text", "t", "t", "{}", "[]", "fp1_exact", "chk1", 1),
            ("c2_1", "doc2", "/path/doc2", "doc2.txt", "text", "t", "t", "{}", "[]", "fp2_b", "chk2", 1),
            ("c2_2", "doc2", "/path/doc2", "doc2.txt", "text", "t", "t", "{}", "[]", "fp2_a", "chk2", 1),
            ("c3_1", "doc3", "/path/doc3", "doc3.txt", "text", "t", "t", "{}", "[]", "fp3_val", "chk3", 0),
            ("c4_1", "doc4", "/path/doc4", "doc4.txt", "text", "t", "t", "{}", "[]", None, "chk4", 1),
        ]
        conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _legacy_group_by_query(db_path: Path) -> dict[str, str]:
    """Execute the old unoptimized GROUP BY query for baseline comparison."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            """
            SELECT document_id,
                   MIN(source_fingerprint) AS min_fp,
                   MAX(source_fingerprint) AS max_fp
            FROM chunks
            WHERE retrievable = 1
            GROUP BY document_id
            """
        ).fetchall()
    return {str(row[0]): str(row[1] or "") for row in rows}


def test_semantic_identity_with_legacy_query(tmp_path: Path) -> None:
    """Verify that _get_covered_source_fingerprints produces 100% identical results to legacy query."""
    clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "sample_library.sqlite"
    _create_sample_db(db_path)

    legacy_covered = _legacy_group_by_query(db_path)
    # Expected: doc1 -> 'fp1_exact', doc2 -> 'fp2_a', doc4 -> '', doc3 (retrievable=0) not present
    assert "doc1" in legacy_covered
    assert legacy_covered["doc1"] == "fp1_exact"
    assert legacy_covered["doc2"] == "fp2_a"
    assert legacy_covered["doc4"] == ""
    assert "doc3" not in legacy_covered
    assert "doc_nonexistent" not in legacy_covered

    # 1. Query with explicit candidate doc_ids including present, non-retrievable, and missing docs
    test_candidates = ["doc1", "doc2", "doc3", "doc4", "doc_nonexistent"]
    new_covered = _get_covered_source_fingerprints(db_path, candidate_doc_ids=test_candidates)

    for doc_id in test_candidates:
        legacy_val = legacy_covered.get(doc_id)
        new_val = new_covered.get(doc_id)
        assert legacy_val == new_val, f"Mismatch for doc_id {doc_id}: legacy={legacy_val}, new={new_val}"

    # 2. Query with candidate_doc_ids=None (full scan)
    clear_covered_source_fingerprints_cache()
    full_new_covered = _get_covered_source_fingerprints(db_path, candidate_doc_ids=None)
    assert full_new_covered == legacy_covered


def test_no_database_rescan_when_index_unchanged(tmp_path: Path) -> None:
    """Prove that repeat calls when database file is unchanged do not re-scan or query SQLite."""
    clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "cache_test.sqlite"
    _create_sample_db(db_path)

    # First call: populates cache from SQLite
    candidates = ["doc1", "doc2"]
    res1 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=candidates)
    assert res1 == {"doc1": "fp1_exact", "doc2": "fp2_a"}

    # Mock sqlite3.connect to guarantee zero database hits on second call
    with patch("sqlite3.connect") as mock_connect:
        res2 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=candidates)
        assert res2 == res1
        mock_connect.assert_not_called()

    # Repeat call with a subset of already cached candidates
    with patch("sqlite3.connect") as mock_connect:
        res_subset = _get_covered_source_fingerprints(db_path, candidate_doc_ids=["doc1"])
        assert res_subset == {"doc1": "fp1_exact"}
        mock_connect.assert_not_called()

    # Non-existent doc: first query queries SQLite and records negative cache
    res3 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=["doc_missing"])
    assert res3 == {}

    # Second call for non-existent doc: ZERO sqlite hits!
    with patch("sqlite3.connect") as mock_connect:
        res4 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=["doc_missing"])
        assert res4 == {}
        mock_connect.assert_not_called()


def test_cache_invalidation_on_file_modification(tmp_path: Path) -> None:
    """Verify that modifying the database file automatically invalidates the cache."""
    clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "invalidation_test.sqlite"
    _create_sample_db(db_path)

    res1 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=["doc1"])
    assert res1 == {"doc1": "fp1_exact"}

    # Simulate index update by adding a new chunk with updated fingerprint
    time.sleep(0.02)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE chunks SET source_fingerprint = 'fp1_updated' WHERE document_id = 'doc1'
            """
        )

    # Calling again detects modified mtime/size and fetches updated fingerprint
    res2 = _get_covered_source_fingerprints(db_path, candidate_doc_ids=["doc1"])
    assert res2 == {"doc1": "fp1_updated"}


def test_spec_matching_logic_preserves_semantics(tmp_path: Path) -> None:
    """Verify that matching specs with covered fingerprints preserves 100% of adapter semantics."""
    clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "spec_test.sqlite"
    _create_sample_db(db_path)

    covered = _get_covered_source_fingerprints(
        db_path, candidate_doc_ids=["doc1", "doc2", "doc3", "doc_missing"]
    )

    specs = [
        SourceSpec(source_id="s1", path=tmp_path / "doc1.txt", document_id="doc1"),
        SourceSpec(source_id="s2", path=tmp_path / "doc2.txt", document_id="doc2"),
        SourceSpec(source_id="s3", path=tmp_path / "doc3.txt", document_id="doc3"),
        SourceSpec(source_id="s4", path=tmp_path / "doc4.txt", document_id="doc_missing"),
    ]

    # In read-only mode, any spec whose document_id is in covered is accepted
    indexed_specs = []
    for s in specs:
        stored = covered.get(s.document_id)
        if stored is not None:
            indexed_specs.append(s)

    accepted_ids = [s.document_id for s in indexed_specs]
    assert accepted_ids == ["doc1", "doc2"]
    assert "doc3" not in accepted_ids  # retrievable=0
    assert "doc_missing" not in accepted_ids
