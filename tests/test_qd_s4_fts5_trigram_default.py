"""Tests for QD-S4: Standardize FTS5 Trigram as Deterministic Lexical CJK Prefilter (QD-10).

Covers:
- Deterministic creation of chunks_fts_trigram table & triggers upon index creation.
- Trigger-based synchronization on chunk insert, update, delete.
- Decommissioning of 3 environment flags:
  AIOS_RAG_V2_CJK_PREFILTER, AIOS_RAGV2_LEX_V2_CJK_TRIGRAM, AIOS_RAGV2_LEX_V2_TEMP_TABLE.
- FTS5 Trigram as the default deterministic engine for CJK queries.
- Transparent safety fallback to LIKE prefilter when table is absent (legacy read-only index).
- Transparent safety fallback for CJK terms < 3 characters (where 3-grams cannot be formed).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    cjk_prefilter_enabled,
    _lexical_v2_flags,
)
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

pytestmark = pytest.mark.slow


def make_chunk(
    chunk_id: str,
    text: str,
    *,
    source_name: str = "source.txt",
    source_path: str = "source.txt",
    metadata: dict | None = None,
    labels: tuple[str, ...] = ("allowed",),
    fingerprint: str = "v1",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_path=source_path,
        source_name=source_name,
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        metadata=metadata or {},
    )


def test_trigram_table_created_deterministically(tmp_path: Path) -> None:
    """chunks_fts_trigram and triggers are created deterministically upon index creation."""
    db_path = tmp_path / "test_trigram.sqlite"
    with LocalChunkIndex(str(db_path)) as index:
        # Verify chunks_fts_trigram table exists
        row = index._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'chunks_fts_trigram'"
        ).fetchone()
        assert row is not None, "chunks_fts_trigram virtual table must exist"

        # Verify triggers exist
        triggers = {
            r[0]
            for r in index._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'chunks_fts_trigram%'"
            ).fetchall()
        }
        assert "chunks_fts_trigram_insert" in triggers
        assert "chunks_fts_trigram_delete" in triggers
        assert "chunks_fts_trigram_update" in triggers


def test_trigram_triggers_sync_on_mutation(tmp_path: Path) -> None:
    """Insert, update, delete on chunks keep chunks_fts_trigram table in sync."""
    db_path = tmp_path / "test_sync.sqlite"
    chunk1 = make_chunk("c1", "サーボモータ過負荷エラー E302 対処方法", source_name="servo.txt")
    chunk2 = make_chunk("c2", "治具組立手順 歪み検査方法", source_name="jig.txt")

    with LocalChunkIndex(str(db_path)) as index:
        # Insert
        index.upsert_chunks([chunk1, chunk2])
        count = index._conn.execute("SELECT COUNT(*) FROM chunks_fts_trigram").fetchone()[0]
        assert count == 2

        # Verify trigram query matches
        match = index._conn.execute(
            "SELECT chunk_id FROM chunks_fts_trigram WHERE chunks_fts_trigram MATCH '\"サーボ\"'"
        ).fetchall()
        assert [r[0] for r in match] == ["c1"]

        # Update chunk1
        updated_c1 = make_chunk("c1", "ベルトコンベア定期メンテナンス", source_name="belt.txt")
        index.upsert_chunks([updated_c1])
        match_old = index._conn.execute(
            "SELECT chunk_id FROM chunks_fts_trigram WHERE chunks_fts_trigram MATCH '\"サーボ\"'"
        ).fetchall()
        assert len(match_old) == 0
        match_new = index._conn.execute(
            "SELECT chunk_id FROM chunks_fts_trigram WHERE chunks_fts_trigram MATCH '\"コンベア\"'"
        ).fetchall()
        assert [r[0] for r in match_new] == ["c1"]

        # Delete (via replace_document_chunks)
        index.replace_document_chunks("doc-c2", [])
        count_after = index._conn.execute("SELECT COUNT(*) FROM chunks_fts_trigram").fetchone()[0]
        assert count_after == 1


def test_env_flags_decommissioned(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Changing decommissioned flags has zero effect on behavior."""
    # 1. AIOS_RAG_V2_CJK_PREFILTER
    monkeypatch.setenv("AIOS_RAG_V2_CJK_PREFILTER", "0")
    assert cjk_prefilter_enabled() is True

    monkeypatch.setenv("AIOS_RAG_V2_CJK_PREFILTER", "1")
    assert cjk_prefilter_enabled() is True

    # 2. AIOS_RAGV2_LEX_V2_CJK_TRIGRAM
    monkeypatch.setenv("AIOS_RAGV2_LEX_V2_CJK_TRIGRAM", "0")
    flags = _lexical_v2_flags()
    assert flags is not None
    assert flags["CJK_TRIGRAM"] is True

    # 3. AIOS_RAGV2_LEX_V2_TEMP_TABLE (decommissioned / ignored)
    monkeypatch.setenv("AIOS_RAGV2_LEX_V2_TEMP_TABLE", "0")
    db_path = tmp_path / "test_temp_table_flag.sqlite"
    with LocalChunkIndex(str(db_path)) as index:
        index.upsert_chunks([make_chunk("c1", "サーボモータ過負荷エラー", source_name="s.txt")])
        res = index.search_with_summary("サーボモータ", limit=2)
        assert len(res.results) > 0


def test_trigram_is_default_cjk_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Trigram is the default engine used during retrieval for CJK queries."""
    monkeypatch.setenv("AIOS_RAGV2_LEXICAL_V2", "1")
    db_path = tmp_path / "test_default.sqlite"
    chunks = [
        make_chunk("c1", "サーボモータ過負荷エラー E302 対処方法", source_name="servo.txt"),
        make_chunk("c2", "治具組立手順 歪み検査方法", source_name="jig.txt"),
        make_chunk("c3", "Bảo trì định kỳ băng tải", source_name="belt.txt"),
    ]
    with LocalChunkIndex(str(db_path)) as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary("サーボモータ 過負荷エラー", limit=5)

    breakdown = dict(response.summary.lexical_breakdown_ms)
    assert len(response.results) > 0
    assert response.results[0].chunk_id == "c1"
    assert breakdown.get("trigram_match_ms", 0.0) > 0.0
    assert "like_prefilter_ms" not in breakdown


def test_safe_fallback_on_legacy_index_missing_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy indexes opened read-only without chunks_fts_trigram safely fall back to LIKE."""
    monkeypatch.setenv("AIOS_RAGV2_LEXICAL_V2", "1")
    db_path = tmp_path / "test_legacy.sqlite"
    chunks = [
        make_chunk("c1", "サーボモータ過負荷エラー E302 対処方法", source_name="servo.txt"),
        make_chunk("c2", "治具組立手順 歪み検査方法", source_name="jig.txt"),
    ]
    with LocalChunkIndex(str(db_path)) as index:
        index.upsert_chunks(chunks)

    # Simulate legacy DB by dropping the trigram table
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks_fts_trigram")
        conn.commit()

    # Open with read_only=True
    with LocalChunkIndex(str(db_path), read_only=True) as index:
        response = index.search_with_summary("サーボモータ 過負荷エラー", limit=5)

    breakdown = dict(response.summary.lexical_breakdown_ms)
    assert len(response.results) > 0
    assert response.results[0].chunk_id == "c1"
    assert breakdown.get("like_prefilter_ms", 0.0) > 0.0
    assert "trigram_match_ms" not in breakdown


def test_safe_fallback_for_short_cjk_terms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CJK queries with terms < 3 chars safely fall back to LIKE prefilter (QD-10)."""
    monkeypatch.setenv("AIOS_RAGV2_LEXICAL_V2", "1")
    db_path = tmp_path / "test_short_cjk.sqlite"
    chunks = [
        make_chunk("c1", "Beam径がNGの場合は清掃してください", source_name="beam.txt"),
        make_chunk("c2", "Không liên quan đến máy móc", source_name="other.txt"),
    ]
    with LocalChunkIndex(str(db_path)) as index:
        index.upsert_chunks(chunks)
        # Single-kanji CJK query: "径" has length 1 (< 3 chars, cannot form 3-gram)
        response = index.search_with_summary("径", limit=5)

    breakdown = dict(response.summary.lexical_breakdown_ms)
    assert len(response.results) > 0
    assert response.results[0].chunk_id == "c1"
    # Verify fallback to LIKE prefilter was triggered
    assert breakdown.get("like_prefilter_ms", 0.0) > 0.0
    assert "trigram_match_ms" not in breakdown
