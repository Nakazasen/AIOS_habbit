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

