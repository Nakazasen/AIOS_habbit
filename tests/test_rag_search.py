import sqlite3
import pytest
from dataclasses import asdict
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import (
    create_rag_search_schema,
    clear_rag_search_index,
    index_rag_chunks,
    search_rag_chunks,
    get_rag_search_stats,
    RAGSearchFilter,
    sanitize_fts_query
)
from aios_habit.notebook_index import SourceChunk, build_rag_chunks_from_notebook_chunks

@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    yield conn
    conn.close()

def _create_test_chunks():
    c1 = RAGChunk(
        chunk_id="C1",
        document_id="D1",
        element_ids=[],
        text="The quick brown fox jumps over the lazy dog.",
        source_title="Fox Story",
        source_path="fox.txt",
        relative_path="fox.txt",
        citation_label="fox.txt",
        file_type=".txt",
        element_types=["text"],
        page_numbers=[1],
        sheet_names=[],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="local_only",
        source_hash="h1"
    )
    c2 = RAGChunk(
        chunk_id="C2",
        document_id="D2",
        element_ids=[],
        text="A fast rabbit runs away from the wolf.",
        source_title="Rabbit Story",
        source_path="rabbit.txt",
        relative_path="rabbit.txt",
        citation_label="rabbit.txt",
        file_type=".txt",
        element_types=["text"],
        page_numbers=[2],
        sheet_names=[],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="cloud_safe",
        source_hash="h2"
    )
    c3 = RAGChunk(
        chunk_id="C3",
        document_id="D3",
        element_ids=[],
        text="Top secret company mật document about financial plans.",
        source_title="Secret Doc",
        source_path="C:/docs/secret.txt",
        relative_path="secret.txt",
        citation_label="secret.txt",
        file_type=".txt",
        element_types=["text"],
        page_numbers=[],
        sheet_names=["Sheet1"],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="local_only",
        source_hash="h3"
    )
    return [c1, c2, c3]

def test_schema_and_stats(memory_db):
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)
    stats = get_rag_search_stats(memory_db)
    
    assert stats.document_count == 3
    assert stats.chunk_count == 3
    assert stats.privacy_modes == ["cloud_safe", "local_only"]
    assert stats.file_types == [".txt"]
    
def test_basic_search_and_phrase_boost(memory_db):
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)
    
    # Exact phrase "brown fox"
    results = search_rag_chunks(memory_db, "brown fox")
    assert len(results) >= 1
    assert results[0].chunk_id == "C1"
    
    # Exact phrase "financial plans"
    results2 = search_rag_chunks(memory_db, "financial plans")
    assert len(results2) >= 1
    assert results2[0].chunk_id == "C3"

def test_metadata_filters(memory_db):
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)
    
    # filter by page_number
    res = search_rag_chunks(memory_db, "", filters=RAGSearchFilter(page_numbers=[2]))
    assert len(res) == 1
    assert res[0].chunk_id == "C2"
    
    # filter by sheet_name
    res2 = search_rag_chunks(memory_db, "", filters=RAGSearchFilter(sheet_names=["Sheet1"]))
    assert len(res2) == 1
    assert res2[0].chunk_id == "C3"
    
    # filter by title
    res3 = search_rag_chunks(memory_db, "dog", filters=RAGSearchFilter(source_titles=["Fox Story"]))
    assert len(res3) == 1

def test_privacy_filters_and_safety(memory_db):
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)
    
    # cloud_safe only
    res = search_rag_chunks(memory_db, "", filters=RAGSearchFilter(privacy_modes=["cloud_safe"]))
    assert len(res) == 1
    assert res[0].chunk_id == "C2"
    
    # C3 is local_only despite being called "secret.txt"
    res2 = search_rag_chunks(memory_db, "financial plans", filters=RAGSearchFilter(privacy_modes=["cloud_safe"]))
    assert len(res2) == 0
    
    # check path safety
    res3 = search_rag_chunks(memory_db, "secret company", filters=RAGSearchFilter(privacy_modes=["local_only"]))
    assert len(res3) > 0
    # ensure "C:/docs" does not leak in citation_label or relative_path
    assert res3[0].citation_label == "secret.txt"
    assert res3[0].relative_path == "secret.txt"

def test_fallback_search(memory_db):
    # Disable FTS artificially
    memory_db.execute("UPDATE fts_enabled SET enabled = 0")
    memory_db.commit()
    
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)
    
    # BM25 FTS5 won't be used, fallback regex/LIKE will be used
    results = search_rag_chunks(memory_db, "brown fox")
    assert len(results) >= 1
    assert results[0].chunk_id == "C1"
    
    results2 = search_rag_chunks(memory_db, "rabbit")
    assert len(results2) >= 1
    assert results2[0].chunk_id == "C2"

def test_sanitize_fts_query():
    assert sanitize_fts_query('hello "world"') == 'hello world'
    assert sanitize_fts_query("it's test") == "it s test"
    assert sanitize_fts_query("dog OR 1=1; DROP TABLE chunk_metadata; --") == "dog or 1 1 drop table chunk_metadata"

def test_compatibility():
    sc1 = SourceChunk(
        chunk_id="sc1",
        notebook_id="n1",
        source_id="s1",
        chunk_index=0,
        text="this is old format",
        keywords=["old"],
        privacy_level="local_only",
        source_title="Old format test",
        original_filename="old.txt",
        created_at="2026-01-01"
    )
    rag_chunks = build_rag_chunks_from_notebook_chunks([sc1])
    
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, rag_chunks)
    
    res = search_rag_chunks(conn, "old format")
    assert len(res) == 1
    assert res[0].citation_label == "old.txt"
    assert res[0].privacy_mode == "local_only"


def test_deterministic_ordering_and_extra_filters(memory_db):
    chunks = _create_test_chunks()
    chunks.append(RAGChunk(
        chunk_id="C0",
        document_id="D0",
        element_ids=[],
        text="same token",
        source_title="Tie A",
        source_path="slides.pptx",
        relative_path="slides.pptx",
        citation_label="slides.pptx",
        file_type=".pptx",
        element_types=["slide_text"],
        page_numbers=[],
        sheet_names=[],
        slide_numbers=[7],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="cloud_safe",
        source_hash="h0"
    ))
    chunks.append(RAGChunk(
        chunk_id="C9",
        document_id="D9",
        element_ids=[],
        text="same token",
        source_title="Tie B",
        source_path="slides2.pptx",
        relative_path="slides2.pptx",
        citation_label="slides2.pptx",
        file_type=".pptx",
        element_types=["slide_text"],
        page_numbers=[],
        sheet_names=[],
        slide_numbers=[7],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="cloud_safe",
        source_hash="h9"
    ))
    index_rag_chunks(memory_db, chunks)

    run1 = [r.chunk_id for r in search_rag_chunks(memory_db, "same token")]
    run2 = [r.chunk_id for r in search_rag_chunks(memory_db, "same token")]
    assert run1 == run2
    assert run1[:2] == ["C0", "C9"]

    by_slide = search_rag_chunks(memory_db, "", filters=RAGSearchFilter(slide_numbers=[7]))
    assert [r.chunk_id for r in by_slide] == ["C0", "C9"]

    by_element = search_rag_chunks(memory_db, "", filters=RAGSearchFilter(element_types=["slide_text"]))
    assert [r.chunk_id for r in by_element] == ["C0", "C9"]


def test_injection_like_query_does_not_execute_sql(memory_db):
    chunks = _create_test_chunks()
    index_rag_chunks(memory_db, chunks)

    results = search_rag_chunks(memory_db, "dog OR 1=1; DROP TABLE chunk_metadata; --")
    assert isinstance(results, list)
    stats = get_rag_search_stats(memory_db)
    assert stats.chunk_count == 3


def test_old_search_notebook_chunks_behavior(monkeypatch):
    from aios_habit import notebook_index

    chunks = [
        SourceChunk("s1", "n1", "src1", 0, "alpha beta", ["alpha"], "local_only", "Alpha", "alpha.txt", "2026"),
        SourceChunk("s2", "n1", "src2", 1, "gamma", ["gamma"], "cloud_safe", "Gamma", "gamma.txt", "2026"),
    ]
    monkeypatch.setattr(notebook_index, "load_chunks", lambda notebook_id=None: chunks)

    hits = notebook_index.search_notebook_chunks("n1", "alpha")
    assert len(hits) == 1
    assert hits[0].chunk.chunk_id == "s1"
