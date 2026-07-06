import os
import tempfile
import pytest
import zipfile
import openpyxl
from typing import List

from aios_habit.rag_v2.schema import DocumentElement, ExtractionStatus, ElementType
from aios_habit.rag_v2.adapters import ConversionContext
from aios_habit.rag_v2.converters import (
    TextDocumentConverterAdapter,
    HTMLDocumentConverterAdapter,
    PDFDocumentConverterAdapter,
    ExcelDocumentConverterAdapter,
    WordDocumentConverterAdapter,
    PowerPointDocumentConverterAdapter,
)
from aios_habit.rag_v2.registry import ConverterRegistry


def test_adapter_capabilities():
    registry = ConverterRegistry()
    caps = registry.list_capabilities()
    assert len(caps) == 6
    names = {c["adapter_name"] for c in caps}
    assert "TextDocumentConverterAdapter" in names
    assert "HTMLDocumentConverterAdapter" in names
    assert "PDFDocumentConverterAdapter" in names
    assert "ExcelDocumentConverterAdapter" in names
    assert "WordDocumentConverterAdapter" in names
    assert "PowerPointDocumentConverterAdapter" in names


def test_text_document_converter_success():
    adapter = TextDocumentConverterAdapter()
    
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write("# Heading 1\n\nParagraph 1.\nParagraph 1 line 2.\n\n# Heading 2\n\nParagraph 2.")
        txt_path = f.name

    try:
        ctx = ConversionContext(
            document_id="doc-text",
            privacy_labels=("internal",),
            fail_soft=True
        )
        elements = adapter.convert(txt_path, ctx)
        
        assert len(elements) == 4
        assert elements[0].element_type == ElementType.HEADING
        assert elements[0].text == "# Heading 1"
        assert elements[0].privacy_labels == ("internal",)
        assert elements[0].source_name == os.path.basename(txt_path)
        assert elements[0].file_type == "txt"
        assert elements[0].extractor == "TextDocumentConverterAdapter"
        assert elements[0].extraction_status == ExtractionStatus.SUCCESS

        assert elements[1].element_type == ElementType.TEXT
        assert elements[1].text == "Paragraph 1.\nParagraph 1 line 2."

        assert elements[2].element_type == ElementType.HEADING
        assert elements[2].text == "# Heading 2"

        assert elements[3].element_type == ElementType.TEXT
        assert elements[3].text == "Paragraph 2."

    finally:
        os.remove(txt_path)


def test_html_document_converter_success():
    adapter = HTMLDocumentConverterAdapter()
    
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
        f.write("<html><head><title>Test</title><style>body {color: red;}</style></head><body><h1>Header</h1><p>Para 1</p></body></html>")
        html_path = f.name

    try:
        ctx = ConversionContext(document_id="doc-html")
        elements = adapter.convert(html_path, ctx)
        
        assert len(elements) >= 2
        texts = [e.text for e in elements]
        assert "Header" in texts
        assert "Para 1" in texts
        assert all(e.extraction_status == ExtractionStatus.SUCCESS for e in elements)
    finally:
        os.remove(html_path)


def test_pdf_document_converter_success():
    adapter = PDFDocumentConverterAdapter()
    
    # Try importing fitz to see if we can create a real PDF, otherwise mock
    try:
        import fitz
        has_fitz = True
    except ImportError:
        has_fitz = False

    if has_fitz:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello PDF World\n\nSecond Paragraph")
        doc.save(pdf_path)
        doc.close()

        try:
            ctx = ConversionContext(document_id="doc-pdf")
            elements = adapter.convert(pdf_path, ctx)
            assert len(elements) >= 1
            assert "Hello PDF World" in elements[0].text
            assert "Second Paragraph" in elements[0].text
            assert elements[0].page == 1
            assert elements[0].extraction_status == ExtractionStatus.SUCCESS
        finally:
            os.remove(pdf_path)
    else:
        # Mocking test
        ctx = ConversionContext(document_id="doc-pdf", fail_soft=True)
        elements = adapter.convert("non_existent_file.pdf", ctx)
        assert len(elements) == 1
        assert elements[0].extraction_status == ExtractionStatus.FAILED


def test_excel_document_converter_success():
    adapter = ExcelDocumentConverterAdapter()
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        xlsx_path = f.name

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SheetTest"
    ws["A1"] = "ColA"
    ws["B1"] = "ColB"
    ws["A2"] = "ValA"
    ws["B2"] = "ValB"
    wb.save(xlsx_path)
    wb.close()

    try:
        ctx = ConversionContext(document_id="doc-excel")
        elements = adapter.convert(xlsx_path, ctx)
        assert len(elements) == 1
        elem = elements[0]
        assert elem.element_type == ElementType.TABLE
        assert elem.sheet == "SheetTest"
        assert elem.table is not None
        assert elem.table.headers == ["ColA", "ColB"]
        assert elem.table.rows == [["ColA", "ColB"], ["ValA", "ValB"]]
        assert len(elem.table.cells) == 4
        assert elem.table.cells[0].text == "ColA"
        assert elem.table.cells[0].is_header is True
    finally:
        os.remove(xlsx_path)


def test_word_document_converter_success():
    adapter = WordDocumentConverterAdapter()
    
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        docx_path = f.name

    with zipfile.ZipFile(docx_path, "w") as z:
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello Docx</w:t></w:r></w:p><w:p><w:r><w:t>World Docx</w:t></w:r></w:p></w:body></w:document>'
        )

    try:
        ctx = ConversionContext(document_id="doc-docx")
        elements = adapter.convert(docx_path, ctx)
        assert len(elements) == 2
        assert elements[0].text == "Hello Docx"
        assert elements[1].text == "World Docx"
    finally:
        os.remove(docx_path)


def test_powerpoint_document_converter_success():
    adapter = PowerPointDocumentConverterAdapter()
    
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        pptx_path = f.name

    with zipfile.ZipFile(pptx_path, "w") as z:
        z.writestr(
            "ppt/slides/slide1.xml",
            '<?xml version="1.0" encoding="UTF-8"?><p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Hello Slide 1</a:t></p:sld>'
        )
        z.writestr(
            "ppt/slides/slide2.xml",
            '<?xml version="1.0" encoding="UTF-8"?><p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Hello Slide 2</a:t></p:sld>'
        )

    try:
        ctx = ConversionContext(document_id="doc-pptx")
        elements = adapter.convert(pptx_path, ctx)
        assert len(elements) == 2
        assert elements[0].text == "Hello Slide 1"
        assert elements[0].slide == 1
        assert elements[1].text == "Hello Slide 2"
        assert elements[1].slide == 2
    finally:
        os.remove(pptx_path)


def test_unsupported_and_missing_files():
    registry = ConverterRegistry()
    ctx_soft = ConversionContext(fail_soft=True)
    ctx_hard = ConversionContext(fail_soft=False)

    # Unsupported format
    elems = registry.convert_document("test.unsupported", ctx_soft)
    assert len(elems) == 1
    assert elems[0].extraction_status == ExtractionStatus.FAILED
    assert "No supported adapter found" in elems[0].extraction_warning

    with pytest.raises(ValueError, match="No supported adapter found"):
        registry.convert_document("test.unsupported", ctx_hard)

    # Missing file
    elems = registry.convert_document("missing_file.txt", ctx_soft)
    assert len(elems) == 1
    assert elems[0].extraction_status == ExtractionStatus.FAILED
    assert "File not found" in elems[0].extraction_warning

    with pytest.raises(FileNotFoundError):
        registry.convert_document("missing_file.txt", ctx_hard)


def test_deterministic_failed_element_id():
    registry = ConverterRegistry()
    ctx = ConversionContext(fail_soft=True)
    
    elems1 = registry.convert_document("missing_file.txt", ctx)
    elems2 = registry.convert_document("missing_file.txt", ctx)
    
    assert elems1[0].element_id == elems2[0].element_id
    assert elems1[0].element_id.startswith("failed_")


def test_from_dict_ignores_unknown_future_fields():
    d = {
        "element_id": "test-future-1",
        "document_id": "doc-future",
        "source_path": "test.txt",
        "source_name": "test.txt",
        "file_type": "txt",
        "extractor": "future",
        "extraction_status": "success",
        "element_type": "text",
        "text": "Future Proof",
        "future_field_xyz": "ignored_value",
        "nested_unsupported": {"a": 1}
    }
    
    elem = DocumentElement.from_dict(d)
    assert elem.element_id == "test-future-1"
    assert elem.text == "Future Proof"
    assert not hasattr(elem, "future_field_xyz")
