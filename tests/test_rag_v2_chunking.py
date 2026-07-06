import pytest

from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus, TableCell, TableData
from aios_habit.rag_v2.chunking import StructureAwareChunker


def make_element(**overrides):
    data = {
        "element_id": "e1",
        "document_id": "doc1",
        "source_path": "/tmp/source.txt",
        "source_name": "source.txt",
        "file_type": "txt",
        "extractor": "unit",
        "extraction_status": ExtractionStatus.SUCCESS,
        "element_type": ElementType.TEXT,
        "text": "alpha beta gamma",
        "privacy_labels": ("private",),
        "source_fingerprint": "fp1",
        "section_path": ("Intro",),
    }
    data.update(overrides)
    return DocumentElement(**data)


def test_text_element_chunks_with_metadata():
    chunks = StructureAwareChunker(max_chars=120).chunk_elements([make_element(page=2)])
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text == "alpha beta gamma"
    assert chunk.document_id == "doc1"
    assert chunk.page_range == (2, 2)
    assert chunk.element_ids == ("e1",)
    assert chunk.element_types == ("text",)
    assert chunk.privacy_labels == ("private",)
    assert chunk.source_fingerprint == "fp1"
    assert chunk.section_path == ("Intro",)


def test_long_element_splits_deterministically():
    text = " ".join(f"word{i}" for i in range(80))
    element = make_element(text=text)
    chunker = StructureAwareChunker(max_chars=100)
    first = chunker.chunk_elements([element])
    second = chunker.chunk_elements([element])
    assert len(first) > 1
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.text for chunk in first] == [chunk.text for chunk in second]
    assert all(len(chunk.text) <= 100 for chunk in first)


def test_table_cell_metadata_preserved():
    table = TableData(
        headers=["Name", "Value"],
        rows=[["A", "10"], ["B", "20"]],
        cells=[TableCell(row_index=1, column_index=2, text="10")],
    )
    element = make_element(
        element_type=ElementType.TABLE,
        table=table,
        text=None,
        file_type="xlsx",
        sheet="Sheet1",
        row_range=(1, 3),
        column_range=(1, 2),
        cell_range="A1:B3",
    )
    chunk = StructureAwareChunker(max_chars=120).chunk_elements([element])[0]
    assert "Name | Value" in chunk.text
    assert "A | 10" in chunk.text
    assert chunk.sheet_names == ("Sheet1",)
    assert chunk.row_range == (1, 3)
    assert chunk.column_range == (1, 2)
    assert chunk.cell_range == "A1:B3"


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"page": 3}, {"page_range": (3, 3)}),
        ({"slide": 4}, {"slide_range": (4, 4)}),
        ({"sheet": "Data"}, {"sheet_names": ("Data",)}),
    ],
)
def test_page_slide_sheet_metadata_preserved(overrides, expected):
    chunk = StructureAwareChunker(max_chars=120).chunk_elements([make_element(**overrides)])[0]
    for key, value in expected.items():
        assert getattr(chunk, key) == value


def test_failed_and_empty_elements_do_not_crash():
    failed = make_element(element_id="failed", extraction_status=ExtractionStatus.FAILED)
    empty = make_element(element_id="empty", text="   ")
    chunks = StructureAwareChunker(max_chars=120).chunk_elements([failed, empty])
    assert chunks == []


def test_chunk_round_trip_keeps_tuple_fields():
    chunk = StructureAwareChunker(max_chars=120).chunk_elements([make_element(page=1)])[0]
    restored = type(chunk).from_dict(chunk.to_dict())
    assert restored == chunk
    assert restored.page_range == (1, 1)
