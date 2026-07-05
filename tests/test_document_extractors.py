import zipfile
from pathlib import Path
import openpyxl

from aios_habit.document_extractors import _extract_excel


def test_extract_excel_with_shapes(tmp_path):
    file_path = tmp_path / "mock.xlsx"
    
    # Create valid base workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "Cell Text"
    wb.save(file_path)
    wb.close()
    
    # Append drawing XML to the existing zip
    drawing_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
        <xdr:twoCellAnchor>
            <xdr:sp>
                <xdr:txBody>
                    <a:p>
                        <a:r>
                            <a:t>Mock Shape Text</a:t>
                        </a:r>
                    </a:p>
                </xdr:txBody>
            </xdr:sp>
        </xdr:twoCellAnchor>
    </xdr:wsDr>
    """
    with zipfile.ZipFile(file_path, "a") as archive:
        archive.writestr("xl/drawings/drawing1.xml", drawing_xml)
        
    results = _extract_excel(file_path)
    assert any("Cell Text" in r.text for r in results)
    assert any("Mock Shape Text" in r.text for r in results)

import fitz
from aios_habit.document_extractors import _extract_pdf, extract_text_chunks_from_file

def test_extract_pdf_with_text(tmp_path):
    file_path = tmp_path / "mock.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), "Hello from fake PDF page 1")
    doc.save(str(file_path))
    doc.close()
    
    results = _extract_pdf(file_path)
    assert len(results) == 1
    assert "Hello from fake PDF page 1" in results[0].text
    assert results[0].page in {"1", ""}
    assert results[0].extraction_status == "extracted"
    assert results[0].element_type in {"pdf_page_text", "pdf_markdown_page"}

def test_extract_pdf_empty_scanned(tmp_path):
    file_path = tmp_path / "mock_empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(file_path))
    doc.close()

    results = _extract_pdf(file_path)
    assert len(results) == 1
    assert results[0].text == ""
    assert results[0].extraction_status == "empty_text"

def test_extract_text_chunks_from_pdf(tmp_path):
    file_path = tmp_path / "mock.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), "Hello from fake PDF chunking")
    doc.save(str(file_path))
    doc.close()

    chunks = extract_text_chunks_from_file(file_path, root=tmp_path)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["text"] == "Hello from fake PDF chunking"
    assert chunk["page"] in {"1", ""}
    assert chunk["extraction_status"] == "extracted"
    assert chunk["element_type"] in {"pdf_page_text", "pdf_markdown_page"}
    assert chunk.get("privacy_level") == "local_only"

def test_extract_pdf_missing_dependency(monkeypatch, tmp_path):
    import sys
    monkeypatch.setitem(sys.modules, "pymupdf4llm", None)
    monkeypatch.setitem(sys.modules, "fitz", None)

    file_path = tmp_path / "mock.pdf"
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n")

    results = _extract_pdf(file_path)
    assert len(results) == 1
    assert results[0].text == ""
    assert results[0].extraction_status == "dependency_missing"
    assert "not installed" in results[0].warning



from aios_habit.document_extractors import _extract_docx, _extract_html, _extract_pptx, normalize_extracted_text, local_capabilities
from aios_habit.extractor_registry import adapter_status, extract_with_registry, metadata_only_fallback, registered_extensions


def _write_zip(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)


def test_pptx_adapter_extracts_slide_text_and_notes(tmp_path):
    pptx = tmp_path / "deck.pptx"
    _write_zip(pptx, {
        "ppt/slides/slide1.xml": "<a:t>Slide Title</a:t><a:t>ManualShipping table text</a:t>",
        "ppt/notesSlides/notesSlide1.xml": "<a:t>Speaker note safe text</a:t>",
    })
    res = _extract_pptx(pptx)
    assert res.extraction_status == "extracted_success"
    assert "Slide Title" in res.text
    assert "Speaker note" in res.text


def test_docx_adapter_extracts_paragraphs_and_tables(tmp_path):
    docx = tmp_path / "doc.docx"
    _write_zip(docx, {"word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Heading Text</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell Value</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'})
    res = _extract_docx(docx)
    assert res.extraction_status == "extracted_success"
    assert "Heading Text" in res.text
    assert "Cell Value" in res.text


def test_html_adapter_keeps_mermaid_and_removes_script(tmp_path):
    html_path = tmp_path / "diagram.html"
    html_path.write_text("<html><head><title>ERD</title><style>.x{}</style><script>secret()</script></head><body><h1>Diagram</h1><pre class='mermaid'>A-->B</pre><table><tr><td>Order</td></tr></table></body></html>", encoding="utf-8")
    res = _extract_html(html_path)
    assert res.extraction_status == "extracted_success"
    assert "Diagram" in res.text
    assert "A-->B" in res.text
    assert "secret" not in res.text


def test_registry_routes_and_fallback_metadata_only(tmp_path):
    assert ".pdf" in registered_extensions()
    status = adapter_status(".pdf")
    assert status.status == "available"
    unknown = tmp_path / "x.unknown"
    unknown.write_text("ignored", encoding="utf-8")
    elements = extract_with_registry(unknown, root=tmp_path)
    assert elements[0].extraction_status == "dependency_missing"
    assert elements[0].text == ""
    assert elements[0].metadata["_is_metadata_only"] == "True"


def test_metadata_only_fallback_schema(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"abc")
    el = metadata_only_fallback(p, tmp_path, status="parse_failed")[0]
    assert el.relative_path == "x.bin"
    assert el.element_type == "metadata_only"
    assert el.extraction_status == "parse_failed"


def test_image_metadata_or_ocr_safe(tmp_path):
    from PIL import Image
    img = tmp_path / "img.png"
    Image.new("RGB", (20, 10), "white").save(img)
    chunks = extract_text_chunks_from_file(img, root=tmp_path)
    assert chunks[0]["file_type"] == ".png"
    assert chunks[0]["extraction_status"] in {"unsupported_no_local_ocr", "ocr_partial", "ocr_success", "failed_with_reason"}
    assert local_capabilities()["cloud_ocr_used"] is False


def test_normalization_reduces_coordinate_garbage_and_preserves_multilingual():
    text = "10 20 30 40 50\nThiết kế 変更 ManualShipping\n   nhiều   khoảng trắng   "
    cleaned = normalize_extracted_text(text)
    assert "10 20 30 40 50" not in cleaned
    assert "Thiết kế 変更 ManualShipping" in cleaned
