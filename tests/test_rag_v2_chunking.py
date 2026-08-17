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


def test_long_element_splits_into_deterministic_children_and_local_parent():
    text = " ".join(f"word{i}" for i in range(80))
    element = make_element(text=text)
    chunker = StructureAwareChunker(max_chars=100)
    first = chunker.chunk_elements([element])
    second = chunker.chunk_elements([element])
    children = [chunk for chunk in first if chunk.retrievable]
    parents = [chunk for chunk in first if not chunk.retrievable]

    assert len(children) > 1
    assert len(parents) == 1
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.text for chunk in first] == [chunk.text for chunk in second]
    assert all(len(chunk.text) <= 100 for chunk in children)
    assert parents[0].metadata["representation_role"] == "parent"
    assert all(parents[0].element_ids[0] in chunk.parent_element_ids for chunk in children)


def test_table_creates_schema_row_groups_and_local_parent_with_provenance():
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
    chunks = StructureAwareChunker(max_chars=120).chunk_elements([element])
    by_role = {chunk.metadata["representation_role"]: chunk for chunk in chunks}
    schema = by_role["table_schema"]
    rows = by_role["table_rows"]
    parent = by_role["table_parent"]

    assert "Columns: Name | Value" in schema.text
    assert "Row 2: A | 10" in rows.text
    assert "Row 3: B | 20" in rows.text
    assert rows.sheet_names == ("Sheet1",)
    assert rows.row_range == (2, 3)
    assert rows.column_range == (1, 2)
    assert rows.cell_range == "A2:B3"
    assert schema.row_range == (1, 1)
    assert schema.cell_range == "A1:B1"
    assert parent.retrievable is False
    assert parent.element_ids[0] in schema.parent_element_ids
    assert parent.element_ids[0] in rows.parent_element_ids


def test_short_excel_regions_are_compacted_without_dropping_table_parents():
    elements = []
    for index, start_row in enumerate((1, 4, 7), start=1):
        elements.append(make_element(
            element_id=f"excel-region-{index}",
            element_type=ElementType.TABLE,
            table=TableData(headers=["Name"], rows=[[f"row-{index}"]]),
            text=None,
            file_type="xlsx",
            source_path="/tmp/form.xlsx",
            source_name="form.xlsx",
            sheet="Form",
            row_range=(start_row, start_row + 1),
            column_range=(1, 1),
            cell_range=f"A{start_row}:A{start_row + 1}",
        ))

    chunks = StructureAwareChunker(max_chars=1000).chunk_elements(elements)
    compacted = [
        chunk for chunk in chunks
        if chunk.metadata["representation_role"] == "table_region_compacted"
    ]
    parents = [
        chunk for chunk in chunks
        if chunk.metadata["representation_role"] == "table_parent"
    ]

    assert len(compacted) == 2  # schema and row values retain separate roles
    assert sum(chunk.metadata["compacted_child_count"] for chunk in compacted) == 6
    assert any("row-1" in chunk.text for chunk in compacted)
    assert any("row-3" in chunk.text for chunk in compacted)
    assert all(chunk.row_range is None for chunk in compacted)  # regions had gaps
    assert len(parents) == 3


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


def test_oversized_table_row_splits_into_bounded_provenance_preserving_children():
    long_cell = " ".join(f"value{i}" for i in range(80))
    table = TableData(headers=["Details"], rows=[[long_cell]])
    element = make_element(
        element_type=ElementType.TABLE,
        table=table,
        text=None,
        file_type="xlsx",
        sheet="Data",
        row_range=(1, 2),
        column_range=(1, 1),
        cell_range="A1:A2",
    )
    chunker = StructureAwareChunker(max_chars=120)
    first = chunker.chunk_elements([element])
    second = chunker.chunk_elements([element])
    children = [
        chunk for chunk in first
        if chunk.retrievable and chunk.metadata["representation_role"] == "table_rows"
    ]

    assert len(children) > 1
    assert all(len(chunk.text) <= 120 for chunk in children)
    assert all(chunk.sheet_names == ("Data",) for chunk in children)
    assert all(chunk.row_range == (2, 2) for chunk in children)
    assert all(chunk.column_range == (1, 1) for chunk in children)
    assert all(chunk.cell_range == "A2:A2" for chunk in children)
    assert all("e1::table-parent" in chunk.parent_element_ids for chunk in children)
    assert " ".join(chunk.text for chunk in children).endswith(long_cell)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.text for chunk in first] == [chunk.text for chunk in second]
