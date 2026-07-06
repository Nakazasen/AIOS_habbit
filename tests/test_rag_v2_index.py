from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import LocalChunkIndex


def make_chunk(text="alpha beta beta", labels=("private",)):
    element = DocumentElement(
        element_id="e1",
        document_id="doc1",
        source_path="/tmp/source.txt",
        source_name="source.txt",
        file_type="txt",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=labels,
        source_fingerprint="fp1",
        page=5,
    )
    return StructureAwareChunker(max_chars=120).chunk_elements([element])[0]


def test_local_index_add_and_search_chunks(tmp_path):
    db_path = tmp_path / "rag_chunks.sqlite"
    chunk = make_chunk()
    with LocalChunkIndex(db_path) as index:
        assert index.upsert_chunks([chunk]) == 1
        results = index.search("beta")
        assert len(results) == 1
        assert results[0].chunk_id == chunk.chunk_id
        assert results[0].score == 2.0
        assert results[0].metadata["page_range"] == [5, 5]
    assert db_path.exists()


def test_upsert_does_not_duplicate_same_chunk_id(tmp_path):
    chunk = make_chunk()
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([chunk])
        index.upsert_chunks([chunk])
        assert index.count() == 1


def test_search_returns_metadata_and_privacy_labels(tmp_path):
    chunk = make_chunk(labels=("private", "review"))
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([chunk])
        result = index.search("alpha")[0]
        assert result.document_id == "doc1"
        assert result.source_name == "source.txt"
        assert result.file_type == "txt"
        assert result.privacy_labels == ("private", "review")
        assert result.metadata["element_ids"] == ["e1"]


def test_empty_query_is_safe(tmp_path):
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([make_chunk()])
        assert index.search("") == []
        assert index.search("   ") == []
        assert index.search("alpha", limit=0) == []


def test_clear_removes_chunks(tmp_path):
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks([make_chunk()])
        assert index.count() == 1
        index.clear()
        assert index.count() == 0
