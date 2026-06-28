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
    assert results[0].page == "1"
    assert results[0].extraction_status == "extracted"
    assert results[0].element_type == "pdf_page_text"

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
    assert chunk["page"] == "1"
    assert chunk["extraction_status"] == "extracted"
    assert chunk["element_type"] == "pdf_page_text"
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

