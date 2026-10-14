"""Tests for LSU structured lane CSV document coverage exemption.

Ticket: DESKTOP-SPEED-LSU-COVERAGE-EXEMPTION-FIX-HOME
Verifies that all structured CSV documents in the LSU block are exempt from
semantic dense/sparse embedding coverage requirements in RagV2Index.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Set

import pytest

from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    STRUCTURED_LANE_DOCUMENT_IDS,
)
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend
from aios_habit.rag_v2.structured_query import LSU_STRUCTURED_FILENAMES


EXPECTED_CANONICAL_DOCUMENT_IDS = frozenset({
    "wsc-8eb2a5d21b75fa88307223b1",  # 2026_08_Error_BowOverAdjust.csv
    "wsc-03bf475fc208c02f741d4013",  # 2026_08_Error.csv
    "wsc-4bd2e353e19864fe786358c5",  # 2026_08_UnitTest.csv
    "wsc-d4df39c14101e40ebad88a91",  # 2026_08_Spec.csv
})

LSU_PRODUCTION_INDEX_PATH = Path(
    r"C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\lsu\library.sqlite"
)


def _find_lsu_index_path() -> Path | None:
    """Resolve the LSU index path from known production locations or configuration."""
    if LSU_PRODUCTION_INDEX_PATH.exists():
        return LSU_PRODUCTION_INDEX_PATH
    try:
        from aios_habit.workspace_chat_rag_v2_adapter import (
            _pipeline_config,
            WorkspaceChatRagV2CanaryConfig,
        )
        cfg = WorkspaceChatRagV2CanaryConfig.from_env()
        p = _pipeline_config(cfg, cfg.requested_profile, read_only=True, collection_id="lsu")
        candidate = Path(p.index_path)
        if candidate.exists():
            return candidate
    except Exception:
        pass
    return None


def test_canonical_structured_lane_document_ids_present():
    """Verify that all 4 canonical structured CSV document IDs are in STRUCTURED_LANE_DOCUMENT_IDS."""
    for doc_id in EXPECTED_CANONICAL_DOCUMENT_IDS:
        assert doc_id in STRUCTURED_LANE_DOCUMENT_IDS, (
            f"Document ID '{doc_id}' is missing from STRUCTURED_LANE_DOCUMENT_IDS"
        )


def test_verify_selected_document_coverage_exempts_structured_lane_mock(tmp_path: Path):
    """Synthetic unit test: structured lane documents do not require dense/sparse embeddings to pass coverage."""
    db_path = tmp_path / "test_coverage.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=8)

    exempt_doc_id = "wsc-03bf475fc208c02f741d4013"
    regular_doc_id = "wsc-regular-text-document-12345"

    chunker = StructureAwareChunker(max_chars=200)

    exempt_element = DocumentElement(
        element_id="el-01",
        document_id=exempt_doc_id,
        source_path="C:/tmp/missing5_staging/2026_08_Error.csv",
        source_name="2026_08_Error.csv",
        file_type="csv",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TABLE,
        text="Error table log row with code C7620",
        privacy_labels=("internal",),
        source_fingerprint="fp-exempt-01",
        page=1,
    )
    exempt_chunk = chunker.chunk_elements([exempt_element])[0]

    regular_element = DocumentElement(
        element_id="el-02",
        document_id=regular_doc_id,
        source_path="C:/docs/regular_manual.pdf",
        source_name="regular_manual.pdf",
        file_type="pdf",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text="Regular document content manual guide",
        privacy_labels=("internal",),
        source_fingerprint="fp-reg-02",
        page=1,
    )
    regular_chunk = chunker.chunk_elements([regular_element])[0]

    with LocalChunkIndex(db_path, embedding_backend=backend) as index:
        index.upsert_chunks([exempt_chunk, regular_chunk])

        # Delete embeddings to simulate documents without dense/sparse embeddings
        index._conn.execute("DELETE FROM chunk_embeddings")
        index._conn.execute("DELETE FROM chunk_sparse_embeddings")
        index._conn.commit()

        # regular_doc_id has no embeddings -> coverage fails
        reg_cov = index.verify_selected_document_coverage(
            [regular_doc_id],
            sparse_required=False,
        )
        assert reg_cov["valid"] is False
        assert reg_cov["dense_complete"] is False

        # exempt_doc_id is in STRUCTURED_LANE_DOCUMENT_IDS -> coverage succeeds even with 0 embeddings
        exempt_cov = index.verify_selected_document_coverage(
            [exempt_doc_id],
            sparse_required=False,
        )
        assert exempt_cov["valid"] is True
        assert exempt_cov["dense_complete"] is True
        assert exempt_cov["sparse_complete"] is True

        # When queried together, missing embeddings on regular document still fails the batch
        batch_cov = index.verify_selected_document_coverage(
            [exempt_doc_id, regular_doc_id],
            sparse_required=False,
        )
        assert batch_cov["valid"] is False
        assert batch_cov["dense_complete"] is False


def test_lsu_production_index_structured_csvs_all_exempt():
    """Live index test: query LSU index for all structured CSV documents and assert they are exempt.

    Guards against omissions when new structured CSV tables are added to the LSU index.
    """
    lsu_path = _find_lsu_index_path()
    if lsu_path is None:
        pytest.skip("LSU production index not present in current environment")

    conn = sqlite3.connect(f"file:{lsu_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT document_id, source_name, source_path
            FROM chunks
            WHERE lower(source_name) LIKE '%.csv'
               OR lower(source_path) LIKE '%.csv'
            """
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) > 0, "No CSV documents found in LSU index"

    # Identify structured lane CSVs by matching known structured filenames or staging directory
    structured_csv_doc_ids: Set[str] = set()
    for row in rows:
        name = str(row["source_name"]).strip().lower()
        path = str(row["source_path"]).strip().lower()
        if name in LSU_STRUCTURED_FILENAMES or "missing5_staging" in path or name.startswith("2026_08_"):
            structured_csv_doc_ids.add(str(row["document_id"]))

    if not structured_csv_doc_ids:
        pytest.skip("No structured CSV documents found in LSU index in current environment")

    # Verify every structured CSV document is in STRUCTURED_LANE_DOCUMENT_IDS
    missing = structured_csv_doc_ids - STRUCTURED_LANE_DOCUMENT_IDS
    assert not missing, (
        f"LSU structured CSV document IDs missing from STRUCTURED_LANE_DOCUMENT_IDS: {missing}"
    )

    # Verify coverage check passes for all discovered structured CSV documents
    backend = DeterministicEmbeddingBackend(dimension=1024)
    with LocalChunkIndex(lsu_path, embedding_backend=backend, read_only=True) as index:
        report = index.verify_selected_document_coverage(
            list(structured_csv_doc_ids),
            sparse_required=True,
        )
        assert report["valid"] is True, f"Coverage validation failed for structured CSVs: {report}"
        assert report["dense_complete"] is True
        assert report["sparse_complete"] is True
