import pytest
from aios_habit.rag_v2.schema import (
    DocumentElement,
    ExtractionStatus,
    ElementType,
    TableData,
    TableCell
)

def test_document_element_round_trip():
    elem = DocumentElement(
        element_id="test-123",
        document_id="doc-1",
        source_path="/path/to/test.pdf",
        source_name="test.pdf",
        file_type="pdf",
        extractor="test_extractor",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text="Hello World",
        page=1,
        privacy_labels=("internal", "confidential")
    )

    d = elem.to_dict()
    assert d["element_id"] == "test-123"
    assert d["extraction_status"] == "success"
    assert d["element_type"] == "text"
    assert d["privacy_labels"] == ("internal", "confidential")
    assert d["checksum"] is not None
    assert d["created_at"] is not None

    elem2 = DocumentElement.from_dict(d)
    assert elem2.element_id == elem.element_id
    assert elem2.extraction_status == ExtractionStatus.SUCCESS
    assert elem2.element_type == ElementType.TEXT
    assert elem2.text == "Hello World"
    assert elem2.privacy_labels == ("internal", "confidential")
    assert elem2.checksum == elem.checksum

def test_table_data_round_trip():
    cell1 = TableCell(row_index=0, column_index=0, text="Header1", is_header=True)
    cell2 = TableCell(row_index=1, column_index=0, text="Data1")
    table = TableData(
        headers=["Header1"],
        rows=[["Data1"]],
        cells=[cell1, cell2]
    )

    elem = DocumentElement(
        element_id="table-123",
        document_id="doc-2",
        source_path="/path/to/test.xlsx",
        source_name="test.xlsx",
        file_type="xlsx",
        extractor="test_extractor",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TABLE,
        table=table,
        sheet="Sheet1"
    )

    d = elem.to_dict()
    assert d["table"]["headers"] == ["Header1"]
    assert len(d["table"]["cells"]) == 2

    elem2 = DocumentElement.from_dict(d)
    assert elem2.table is not None
    assert elem2.table.headers == ["Header1"]
    assert len(elem2.table.cells) == 2
    assert elem2.table.cells[0].is_header is True
    assert elem2.table.cells[1].text == "Data1"

def test_optional_fields_defaults():
    # Only required fields
    elem = DocumentElement(
        element_id="min-1",
        document_id="doc-min",
        source_path="fake.txt",
        source_name="fake.txt",
        file_type="txt",
        extractor="min_extractor",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT
    )

    d = elem.to_dict()
    elem2 = DocumentElement.from_dict(d)

    assert elem2.privacy_labels == tuple()
    assert elem2.table is None
    assert elem2.text is None
    assert elem2.checksum is not None
