"""Unit tests for Excel sub-header chunking and sub-table extraction.

Verifies:
1. Float precision normalization removes IEEE-754 precision artifacts.
2. Section header row identification (_is_section_header_row).
3. Section path propagation to DocumentElement and DocumentChunk.
4. Identification of sub-table blocks by sub-header rows without cutting across numerical data blocks.
5. Every table block in a sheet has a representative retrievable chunk.
"""
from pathlib import Path
import openpyxl
import pytest

from aios_habit.excel_extractors import (
    _is_section_header_row,
    normalize_cell_value,
    extract_excel,
)
from aios_habit.rag_v2.adapters import ConversionContext
from aios_habit.rag_v2.converters import ExcelDocumentConverterAdapter
from aios_habit.rag_v2.chunking import StructureAwareChunker


def test_normalize_cell_value_float_precision():
    """Verify IEEE-754 floating point precision noise is cleaned."""
    assert normalize_cell_value(0.0020000000000024443) == "0.002"
    assert normalize_cell_value(0.015000000000000568) == "0.015"
    assert normalize_cell_value(44.0) == "44"
    assert normalize_cell_value(43.956) == "43.956"
    assert normalize_cell_value("  hello  ") == "hello"
    assert normalize_cell_value(None) == ""


def test_is_section_header_row():
    """Verify sub-header rows are distinguished from multi-column data/header rows."""
    # Section header: single prominent label spanning the row
    row_sub = ["LDブラケット測定/ Đo độ lệch Bracket", None, None, None, None]
    assert _is_section_header_row(row_sub) is True

    # Multi-column table header: should NOT be a section header
    row_tbl_hdr = ["No.", "Unit", "CO (X)", "Bracket (Y)", "Diff"]
    assert _is_section_header_row(row_tbl_hdr) is False

    # Numerical data row: should NOT be a section header
    row_data = [1, "OK", 43.956, 44.030, 0.002]
    assert _is_section_header_row(row_data) is False

    # Empty row
    assert _is_section_header_row([None, None, "", "   "]) is False


def test_excel_sub_header_extraction_and_chunking(tmp_path: Path):
    """Create a multi-table workbook with sub-headers and verify chunking."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Measurement"

    # Main table 1: CO measurement
    ws.append(["CO測定結果 / Kết quả đo CO"])  # Row 1: Section 1
    ws.append(["Sample", "Val A", "Val B"])     # Row 2: Table header
    ws.append(["S1", 10.123, 20.456])          # Row 3: Data
    ws.append(["S2", 10.234, 20.567])          # Row 4: Data
    ws.append([])                               # Row 5: Blank
    ws.append([])                               # Row 6: Blank

    # Sub-table 2: Bracket measurement
    ws.append(["LDブラケット測定/ Đo độ lệch Bracket"])  # Row 7: Section 2
    ws.append(["Sample", "Diff X", "Diff Y"])            # Row 8: Table header
    ws.append(["B1", 0.0020000000000024443, 0.015])     # Row 9: Data with float noise
    ws.append(["B2", 0.003, 0.014])                     # Row 10: Data

    file_path = tmp_path / "test_sub_tables.xlsx"
    wb.save(file_path)

    # 1. Test Excel extract_excel
    extraction = extract_excel(file_path)
    regions = extraction.regions
    assert len(regions) >= 2, f"Expected at least 2 table regions, got {len(regions)}"

    bracket_regions = [r for r in regions if "LDブラケット測定" in r.section_name or "Bracket" in r.section_name]
    assert len(bracket_regions) >= 1, "Expected Bracket section table region"
    b_region = bracket_regions[0]
    cell_texts = [c.text for c in b_region.cells]
    assert "0.002" in cell_texts
    assert "0.015" in cell_texts
    # Float precision noise should not be present
    assert "0.0020000000000024443" not in cell_texts

    # 2. Test Converter adapter
    adapter = ExcelDocumentConverterAdapter()
    context = ConversionContext(document_id="doc-test-sub-table")
    elements = adapter.convert(file_path, context)
    assert len(elements) >= 2

    bracket_elements = [e for e in elements if any("LDブラケット測定" in p or "Bracket" in p for p in e.section_path)]
    assert len(bracket_elements) >= 1, "Expected section_path to be propagated to DocumentElement"

    # 3. Test StructureAwareChunker
    chunker = StructureAwareChunker()
    chunks = chunker.chunk_elements(elements)
    assert len(chunks) >= 2

    # Verify every table block in the sheet has a representative retrievable chunk
    retrievable_chunks = [c for c in chunks if c.retrievable]
    assert len(retrievable_chunks) >= 2

    bracket_chunks = [c for c in retrievable_chunks if "0.002" in c.text and "0.015" in c.text]
    assert len(bracket_chunks) >= 1, "Expected retrievable chunk containing Bracket data (0.002, 0.015)"
    target_chunk = bracket_chunks[0]
    assert "Section:" in target_chunk.text
    assert "Bracket" in target_chunk.text
