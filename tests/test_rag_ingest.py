import json
from dataclasses import asdict
from aios_habit.rag_ingest import (
    RAGDocumentElement,
    RAGChunk,
    compute_source_hash,
    stable_document_id,
    stable_element_id,
    stable_chunk_id,
    normalize_privacy_mode,
    build_elements_from_extracted_payload,
    build_chunks_from_elements
)
from aios_habit.notebook_index import SourceChunk, build_rag_chunks_from_notebook_chunks

def test_stable_ids():
    path = "C:/docs/my_doc.txt"
    content1 = "Hello world"
    content2 = "Hello world!"
    
    hash1 = compute_source_hash(content1)
    hash2 = compute_source_hash(content2)
    
    doc_id1 = stable_document_id(path, hash1)
    doc_id1_dup = stable_document_id(path, hash1)
    doc_id2 = stable_document_id(path, hash2)
    
    assert doc_id1 == doc_id1_dup
    assert doc_id1 != doc_id2
    
    chunk_id1 = stable_chunk_id(doc_id1, 0, hash1)
    chunk_id1_dup = stable_chunk_id(doc_id1, 0, hash1)
    chunk_id1_next = stable_chunk_id(doc_id1, 1, hash1)
    
    assert chunk_id1 == chunk_id1_dup
    assert chunk_id1 != chunk_id1_next
    
    element_id1 = stable_element_id(doc_id1, 0, "text")
    element_id1_dup = stable_element_id(doc_id1, 0, "text")
    element_id1_next = stable_element_id(doc_id1, 1, "text")
    
    assert element_id1 == element_id1_dup
    assert element_id1 != element_id1_next

def test_privacy_default():
    assert normalize_privacy_mode(None) == "local_only"
    assert normalize_privacy_mode("") == "local_only"
    assert normalize_privacy_mode("company") == "local_only"
    assert normalize_privacy_mode("mật") == "local_only"
    assert normalize_privacy_mode("private") == "local_only"
    assert normalize_privacy_mode("local_only") == "local_only"
    assert normalize_privacy_mode("cloud_safe") == "cloud_safe"
    assert normalize_privacy_mode("public") == "cloud_safe"
    assert normalize_privacy_mode("normal") == "cloud_safe"
    assert normalize_privacy_mode("unknown_val") == "local_only"

def test_metadata_preservation():
    element = RAGDocumentElement(
        element_id="E1",
        document_id="D1",
        source_title="Excel File",
        source_path="C:/docs/file.xlsx",
        relative_path="file.xlsx",
        file_type=".xlsx",
        element_type="table",
        text="col1 | col2\nval1 | val2",
        sheet_name="Sheet1",
        row_start=1,
        row_end=2,
        cell_range="A1:B2"
    )
    assert element.sheet_name == "Sheet1"
    assert element.row_start == 1
    assert element.row_end == 2
    assert element.cell_range == "A1:B2"
    assert element.privacy_mode == "local_only"

def test_chunk_building_and_json_serialization():
    chunk = RAGChunk(
        chunk_id="C1",
        document_id="D1",
        element_ids=["E1", "E2"],
        text="chunk content",
        source_title="My title",
        source_path="C:/docs/file.txt",
        relative_path="file.txt",
        citation_label="file.txt",
        file_type=".txt",
        element_types=["text"],
        page_numbers=[1],
        sheet_names=[],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[],
        privacy_mode="cloud_safe",
        source_hash="abcd",
        chunk_index=0
    )
    
    d = asdict(chunk)
    j = json.dumps(d)
    d2 = json.loads(j)
    
    assert d2["chunk_id"] == "C1"
    assert d2["element_ids"] == ["E1", "E2"]
    assert d2["page_numbers"] == [1]

def test_path_safety():
    chunk = RAGChunk(
        chunk_id="C1",
        document_id="D1",
        element_ids=[],
        text="test",
        source_title="Title",
        source_path="C:/secret/company/path/file.txt",
        relative_path="file.txt",
        citation_label="file.txt",
        file_type=".txt",
        element_types=["text"],
        page_numbers=[],
        sheet_names=[],
        slide_numbers=[],
        section_labels=[],
        row_ranges=[],
        cell_ranges=[]
    )
    assert chunk.citation_label == "file.txt"
    assert chunk.relative_path == "file.txt"
    assert "C:/secret" not in chunk.citation_label

def test_compatibility():
    sc1 = SourceChunk(
        chunk_id="sc1",
        notebook_id="n1",
        source_id="s1",
        chunk_index=0,
        text="text 1",
        keywords=["t1"],
        privacy_level="local_only",
        source_title="Test 1",
        original_filename="C:/docs/test1.txt",
        created_at="2026-01-01"
    )
    sc2 = SourceChunk(
        chunk_id="sc2",
        notebook_id="n1",
        source_id="s1",
        chunk_index=1,
        text="text 2",
        keywords=["t2"],
        privacy_level="cloud_safe",
        source_title="Test 1",
        original_filename="C:/docs/test1.txt",
        created_at="2026-01-01"
    )
    
    rag_chunks = build_rag_chunks_from_notebook_chunks([sc1, sc2])
    
    assert len(rag_chunks) == 2
    assert rag_chunks[0].text == "text 1"
    assert rag_chunks[0].privacy_mode == "local_only"
    assert rag_chunks[0].citation_label == "test1.txt"
    assert "C:/docs" not in rag_chunks[0].citation_label
    
    assert rag_chunks[1].text == "text 2"
    assert rag_chunks[1].privacy_mode == "cloud_safe"
    
    assert rag_chunks[0].next_chunk_id == rag_chunks[1].chunk_id
    assert rag_chunks[1].previous_chunk_id == rag_chunks[0].chunk_id
    assert rag_chunks[0].document_id == rag_chunks[1].document_id


def test_builders_preserve_page_slide_ocr_metadata():
    elements = build_elements_from_extracted_payload(
        source_path="D:/Sandbox/AIOS_habbit/secret/doc.pdf",
        text="page text",
        source_title="Doc",
        relative_path="doc.pdf",
        file_type=".pdf",
        privacy_mode="unknown",
        extractor_name="test",
        element_type="ocr_text",
        metadata={"kind": "image_ocr"},
    )
    elements[0].page_number = 3
    elements[0].slide_number = 2
    chunks = build_chunks_from_elements(elements)

    assert len(elements) == 1
    assert elements[0].warnings == []
    assert elements[0].privacy_mode == "local_only"
    assert elements[0].element_type == "ocr_text"
    assert elements[0].metadata == {"kind": "image_ocr"}
    assert len(chunks) == 1
    assert chunks[0].page_numbers == [3]
    assert chunks[0].slide_numbers == [2]
    assert chunks[0].element_types == ["ocr_text"]
    assert chunks[0].citation_label == "Doc"
    assert "D:/Sandbox" not in chunks[0].citation_label
    json.dumps(asdict(elements[0]))
    json.dumps(asdict(chunks[0]))


def test_empty_extracted_payload_warns_and_filters_chunk():
    elements = build_elements_from_extracted_payload(
        source_path="empty.txt",
        text="   ",
        privacy_mode=None,
    )
    chunks = build_chunks_from_elements(elements)

    assert elements[0].warnings == ["empty_text"]
    assert elements[0].privacy_mode == "local_only"
    assert chunks == []
