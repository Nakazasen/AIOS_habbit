# Requirement 2 (R2) Technical Survey & Architecture Specification: Excel Extractor Streaming Row-Chunking Upgrade

**Explorer Agent**: `teamwork_preview_explorer_survey_2`  
**Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_2`  
**Scope**: Requirement 2 (Excel Extractor Streaming Row-Chunking Upgrade) from `ORIGINAL_REQUEST.md`  
**Date**: 2026-08-20  

---

## 1. Executive Summary

This report delivers a comprehensive technical investigation of Requirement 2 (R2) for the `AIOS_habbit` system. The core objective is removing all hardcoded truncation limits (1,000 rows/sheet, 20,000 cells) in `src/aios_habit/excel_extractors.py` and implementing a robust **streaming row-chunking engine** that preserves hierarchical column headers, exact row-range metadata, and chunk sequence indices across large enterprise spreadsheets (e.g. manufacturing BOMs, production schedules, master parts lists > 1,500 rows) without memory spikes or data truncation.

---

## 2. Forensic Codebase Audit of Excel Extraction

### 2.1. File Locations and Modules
The Excel extraction subsystem spans the following components:
1. **Core Extractor Engine**: `src/aios_habit/excel_extractors.py` (444 lines) — Defines `ExcelExtractionConfig`, `ExcelTableRegion`, `ExcelCell`, `ExcelEmbeddedImage`, `ExcelChartMetadata`, `ExcelExtraction`, `extract_excel()`, `_extract_openpyxl()`, and `_extract_xls()`.
2. **Unified Document Extraction Adapter**: `src/aios_habit/document_extractors.py:366-473` (`_extract_excel`) & lines 807-853 (`extract_text_chunks_from_file`) — Converts `ExcelTableRegion` objects into standardized `ExtractionResult` records with text formatting, drawing ML shape extraction, and OCR for embedded images.
3. **RAG v2 Converter Pipeline**: `src/aios_habit/rag_v2/converters.py:371-491` (`ExcelDocumentConverterAdapter`) — Maps `ExcelTableRegion` objects into `TableData` and `DocumentElement(element_type=ElementType.TABLE)`.
4. **RAG v2 Chunking Pipeline**: `src/aios_habit/rag_v2/chunking.py:345-450` (`_chunk_table`) — Downstream table chunker grouping table rows with schema representation chunks.
5. **MOM Local Indexing**: `src/aios_habit/mom_local_index.py:152-169` (`_excel_chunks`) — Legacy pandas-based extractor with a 25-row cap.
6. **Workspace Chat Upload Extractor**: `src/aios_habit/workspace_chat_excel.py` — Specialized ephemeral chat upload extractor with strict 32KB/50KB text limits.

---

## 3. Detailed Identification of Hardcoded Limits & Truncation Flaws

### 3.1. Identified Hardcoded Limits in `src/aios_habit/excel_extractors.py`

| Code Location | Variable / Parameter | Current Hardcoded Value | Defect & Operational Impact |
|---|---|---|---|
| `excel_extractors.py:18` | `ExcelExtractionConfig.max_rows_per_sheet` | `1000` | Any spreadsheet with > 1,000 rows (e.g., BOM with 2,500 rows) has rows 1,001+ dropped silently. |
| `excel_extractors.py:19` | `ExcelExtractionConfig.max_non_empty_cells` | `20_000` | Cumulative counter across the entire workbook. A workbook with 30 columns and 700 rows (21,000 cells) halts prematurely. |
| `excel_extractors.py:17` | `ExcelExtractionConfig.max_sheets` | `12` | Sheets 13+ are completely ignored. |
| `excel_extractors.py:15` | `ExcelExtractionConfig.max_file_bytes` | `10 * 1024 * 1024` (10MB) | Rejects valid enterprise workbooks between 10MB and 50MB. |
| `excel_extractors.py:16` | `ExcelExtractionConfig.max_uncompressed_bytes` | `50 * 1024 * 1024` (50MB) | Rejects decompressed XML payloads > 50MB. |

### 3.2. Truncation Control Flow in `_extract_openpyxl` & `_extract_xls`
1. **Global Cell Accumulator Bug (`excel_extractors.py:322, 340-348`)**:
   ```python
   cell_count = image_bytes = 0
   for sheet_index, sheet_name in enumerate(workbook.sheetnames):
       ...
       for cell in row:
           cell_count += 1
           if cell_count > config.max_non_empty_cells:
               result.truncated_reasons.append(f"cell limit: {config.max_non_empty_cells}")
               stop = True
               break
       ...
       if stop:
           break  # Aborts all subsequent worksheets!
   ```
   **Root Cause**: `cell_count` is not reset per sheet and acts as a global breaker, aborting the entire workbook when 20,000 cells are reached.

2. **Monolithic Table Region Memory Accumulation (`excel_extractors.py:328, 346`)**:
   ```python
   rows: list[tuple[int, dict[int, str]]] = []
   for row_number, row in enumerate(sheet.iter_rows(), 1):
       ...
       rows.append((row_number, values))
   result.regions.extend(_regions(sheet_name, rows, list(sheet.merged_cells.ranges), config))
   ```
   **Root Cause**: All extracted rows for a sheet are appended into a single in-memory list `rows` before calling `_regions()`. For a 50,000-row sheet, this builds an enormous tuple matrix and thousands of `ExcelCell` objects in a single `ExcelTableRegion`, causing high peak memory allocation and producing a single monolithic text block downstream.

---

## 4. Analysis of Excel Parsing & Upstream Dependencies

### 4.1. OpenPyXL Parsing (.xlsx, .xlsm)
- **Workbook Loading**:
  - `openpyxl.load_workbook(BytesIO(data), read_only=False, data_only=False, keep_links=False, keep_vba=False)`
  - `read_only=False` is necessary to retain access to `sheet.merged_cells.ranges`, `sheet._charts`, and `sheet._images`.
- **Row Iteration**:
  - `sheet.iter_rows()` yields tuples of `openpyxl.cell.Cell` objects.
  - Normalization via `normalize_cell_value(cell.value)` handles dates, timestamps, strings, and whitespace collapsing.
- **Header & Region Detection**:
  - `_header_depth(rows, first, last, merges, limit)` evaluates the top `limit` rows (default 3) to detect multi-level / merged headers.
  - `_headers(header_rows, width)` resolves composite headers (e.g. `"Lệnh sản xuất > Mã vật tư"`) and handles deduplication (`"Cột (2)"`).

### 4.2. xlrd Parsing (.xls)
- **Workbook Loading**:
  - `xlrd.open_workbook(file_contents=data, on_demand=True, formatting_info=True)`
  - Iterates `sheet.nrows` and `sheet.ncols` using `sheet.cell_value()`.
  - Merged ranges extracted via `sheet.merged_cells`.

---

## 5. Architecture Specification for Streaming Row-Chunking

### 5.1. Core Design Goals
1. **Zero Truncation**: Completely eliminate the 1,000-row and 20,000-cell hard limits.
2. **Streaming Windowed Chunking**: Chunk large sheets into deterministic batches of $K$ data rows (default $K = 500$ rows, configurable).
3. **Repeated Header Context**: Every chunk must carry the full hierarchical `header_rows` and computed `headers` so that each chunk is semantically self-contained for embedding and RAG retrieval.
4. **Rich Provenance Metadata**: Each chunk region must include `chunk_index`, `total_chunks`, exact `row_range` (e.g., `(1, 500)`, `(501, 1000)`), and `cell_range` (e.g., `A1:F500`, `A501:F1000`).
5. **Memory Safety**: Process rows in streaming batches to prevent memory spikes on multi-megabyte worksheets.
6. **Zero Regression**: Preserve exact compatibility with `document_extractors.py`, `rag_v2/converters.py`, and `rag_v2/chunking.py`.

### 5.2. Proposed Data Structure Changes

#### A. Updated `ExcelExtractionConfig` (`src/aios_habit/excel_extractors.py`)
```python
@dataclass(frozen=True)
class ExcelExtractionConfig:
    max_file_bytes: int = 50 * 1024 * 1024            # 50 MB file limit
    max_uncompressed_bytes: int = 200 * 1024 * 1024   # 200 MB uncompressed guard
    max_sheets: int = 30                              # Expanded sheet ceiling
    max_rows_per_sheet: int | None = None             # None = UNLIMITED
    max_non_empty_cells: int | None = None            # None = UNLIMITED
    max_columns_per_region: int = 256
    max_images: int = 24
    max_image_bytes: int = 8 * 1024 * 1024
    max_total_image_bytes: int = 24 * 1024 * 1024
    max_image_pixels: int = 24_000_000
    max_charts: int = 48
    max_header_rows: int = 3
    # New Streaming Row-Chunking Controls
    chunk_row_size: int = 500                         # Target data rows per chunk
    enable_row_chunking: bool = True                  # Activate streaming chunking
    repeat_headers_in_chunks: bool = True             # Repeat header rows on every chunk
```

#### B. Updated `ExcelTableRegion` (`src/aios_habit/excel_extractors.py`)
```python
@dataclass(frozen=True)
class ExcelTableRegion:
    sheet: str
    cell_range: str
    row_range: tuple[int, int]
    column_range: tuple[int, int]
    rows: tuple[tuple[str, ...], ...]
    cells: tuple[ExcelCell, ...]
    header_rows: tuple[tuple[str, ...], ...] = ()
    headers: tuple[str, ...] = ()
    merged_ranges: tuple[str, ...] = ()
    chunk_index: int = 0                              # 0-indexed chunk number
    total_chunks: int = 1                             # Total chunks for this table
```

### 5.3. Chunking Algorithm Details

Let a table region have $D$ header rows ($\text{header\_rows} = H$) and $N$ data rows ($R_1, R_2, \dots, R_N$) spanning columns $C_{\text{first}} \dots C_{\text{last}}$.

1. **Header Phase**:
   - Extract the first $D$ rows ($D \in [0, \text{max\_header\_rows}]$).
   - Build `header_rows = tuple(H)` and compute `headers = _headers(H, width)`.
   - Create `header_cells = tuple(...)` for the header rows.

2. **Chunk Partitioning**:
   - If $N \le \text{chunk\_row\_size}$ or `not enable_row_chunking`:
     - Construct a single `ExcelTableRegion` with `chunk_index = 0, total_chunks = 1`, `rows = H + (R_1..R_N)`, `row_range = (start_row, end_row)`.
   - If $N > \text{chunk\_row\_size}$:
     - Partition data rows into $M = \lceil N / \text{chunk\_row\_size} \rceil$ slices.
     - For slice $i \in [0, M-1]$:
       - Data row slice: $S_i = (R_{i \cdot K + 1}, \dots, R_{\min((i+1) \cdot K, N)})$.
       - `chunk_start_row` = original row number of first data row in $S_i$ (or table start row if $i=0$).
       - `chunk_end_row` = original row number of last data row in $S_i$.
       - `chunk_row_range` = `(chunk_start_row, chunk_end_row)`.
       - `chunk_cell_range` = `f"{_coordinate(chunk_start_row, C_first)}:{_coordinate(chunk_end_row, C_last)}"`.
       - `chunk_rows` = `H + tuple(S_i_matrix)` (headers repeated at top of each chunk).
       - `chunk_cells` = `header_cells + chunk_data_cells`.
       - `chunk_index` = $i$.
       - `total_chunks` = $M$.

3. **Format in `document_extractors.py`**:
   - In `_extract_excel()`, format each chunk as:
     ```
     Excel sheet: {region.sheet}
     Table range: {region.cell_range} (Chunk {region.chunk_index + 1}/{region.total_chunks})
     Columns: {col_1} | {col_2} | ...
     Row {N_1}: {val_1} | {val_2} | ...
     Row {N_2}: {val_1} | {val_2} | ...
     ```
   - Set metadata:
     - `section = f"table {region.cell_range} (chunk {region.chunk_index + 1}/{region.total_chunks})"`
     - `sheet = region.sheet`
     - `row_range = f"{region.row_range[0]}-{region.row_range[1]}"`
     - `element_type = "excel_table_region"`

---

## 6. Comprehensive Caller Inventory & Downstream Integration

```
                                  ┌────────────────────────┐
                                  │   extract_excel()      │
                                  │ (excel_extractors.py)  │
                                  └───────────┬────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
        ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
        │   _extract_excel()    │ │ExcelDocConverterAdapt.│ │  _extract_xls_text()  │
        │(document_extractors)  │ │ (rag_v2/converters)   │ │(workspace_chat_excel) │
        └───────────┬───────────┘ └───────────┬───────────┘ └───────────────────────┘
                    │                         │
        ┌───────────▼───────────┐ ┌───────────▼───────────┐
        │extract_text_chunks_...│ │    rag_v2/chunking    │
        │ (MOM Index / Search)  │ │  (Parent-Child RAG)   │
        └───────────────────────┘ └───────────────────────┘
```

### 6.1. Inventory of Callers across Codebase

| Caller File & Line | Function / Class | Call Signature & Purpose |
|---|---|---|
| `src/aios_habit/document_extractors.py:367, 369` | `_extract_excel(path: Path)` | Calls `extract_excel(path, include_images=True, include_charts=True)`. Formats table chunks, charts, drawingML shapes, and OCRs embedded images into `list[ExtractionResult]`. |
| `src/aios_habit/rag_v2/converters.py:376, 387` | `ExcelDocumentConverterAdapter.convert()` | Calls `extract_excel(path, include_images=True, include_charts=True)`. Converts each `ExcelTableRegion` into a `TableData` element and `DocumentElement`. |
| `src/aios_habit/rag_v2/converters.py:481` | `ExcelDocumentConverterAdapter.capabilities()` | Calls `legacy_xls_available()` to report capability. |
| `src/aios_habit/workspace_chat_excel.py:96, 98` | `_extract_xls_text()` | Calls `extract_excel(file_bytes, filename=filename, include_images=False, include_charts=False)` for legacy XLS chat upload. |
| `src/aios_habit/notebooklm_compare.py:15, 108` | `build_chunks_from_folder()` | Calls `_extract_excel(path)` from `document_extractors.py`. |
| `src/aios_habit/mom_local_index.py:251-256` | `build_mom_local_index()` | Routes table files. When aligned with `document_extractors`, it indexes streaming row chunks. |

---

## 7. Test Inventory & Verification Plan

### 7.1. Existing Excel Tests
1. `tests/test_document_extractors.py:8-40` (`test_extract_excel_with_shapes`): Tests DrawingML shapes and cell extraction via `_extract_excel`.
2. `tests/test_rag_v2_converters.py:222-254` (`test_excel_document_converter_success`): Tests `ExcelDocumentConverterAdapter` TableData creation.
3. `tests/test_workspace_chat_excel_ingest.py` (367 lines): Tests chat Excel ingestion, sheet limits, formula normalization, merged cells, and error handling.
4. `tests/test_rag_v2_structured_query.py`: Tests structured SQL execution on Excel tables.
5. `tests/test_notebooklm_compare.py:66-84`: Tests Excel extraction in folder chunking.

### 7.2. New Test Suite to Implement for R2 (Zero Regression & Large File Guarantee)
1. **`test_excel_streaming_row_chunking_2000_rows`**:
   - Generates an openpyxl workbook with 1 header row + 2,000 data rows (e.g. columns: `Part_ID`, `Part_Name`, `Quantity`, `Unit_Cost`, `Total_Value`, `Status`).
   - Runs `extract_excel(path)`.
   - **Assert**:
     - `result.succeeded is True`, `result.error == ""`, `len(result.truncated_reasons) == 0`.
     - `len(result.regions) == 4` (with default `chunk_row_size=500`).
     - Chunk 0: `row_range == (1, 500)`, `chunk_index == 0`, `total_chunks == 4`.
     - Chunk 1: `row_range == (501, 1000)`, `chunk_index == 1`, `total_chunks == 4`.
     - Chunk 2: `row_range == (1001, 1500)`, `chunk_index == 2`, `total_chunks == 4`.
     - Chunk 3: `row_range == (1501, 2001)`, `chunk_index == 3`, `total_chunks == 4`.
     - Every chunk region has identical `headers == ('Part_ID', 'Part_Name', 'Quantity', 'Unit_Cost', 'Total_Value', 'Status')`.
     - Every chunk contains its corresponding data rows verbatim.

2. **`test_excel_no_cell_count_truncation_30k_cells`**:
   - Generates a workbook with 30 columns and 1,000 rows (30,000 non-empty cells).
   - Runs `extract_excel(path)`.
   - **Assert**:
     - No `"cell limit"` truncation warning.
     - All 30,000 cells are extracted across chunks.

3. **`test_document_extractors_excel_streaming_integration`**:
   - Runs `_extract_excel(large_file_path)` and `extract_text_chunks_from_file(large_file_path)`.
   - **Assert**:
     - Returns multiple `ExtractionResult` chunks.
     - Each chunk contains header lines + row lines.
     - `ExtractionResult.extraction_status == "extracted_success"`.

4. **`test_rag_v2_converters_excel_streaming_integration`**:
   - Runs `ExcelDocumentConverterAdapter.convert(large_file_path, context)`.
   - **Assert**:
     - Returns multiple `DocumentElement` table elements with correct `TableData` and `row_range`.

---

## 8. Conclusion & Implementation Checklist

The design outlined in this survey completely eliminates the 1,000-row and 20,000-cell bottlenecks while maintaining clean encapsulation, memory safety, and seamless integration into MOM search and RAG v2 pipelines.

### Implementation Checklist for Developer Agent:
- [ ] In `src/aios_habit/excel_extractors.py`:
  - [ ] Set `max_rows_per_sheet: int | None = None` and `max_non_empty_cells: int | None = None` in `ExcelExtractionConfig`.
  - [ ] Add `chunk_row_size: int = 500`, `enable_row_chunking: bool = True`, `repeat_headers_in_chunks: bool = True` to `ExcelExtractionConfig`.
  - [ ] Add `chunk_index: int = 0` and `total_chunks: int = 1` to `ExcelTableRegion`.
  - [ ] Update `_regions()` and `_extract_openpyxl()` / `_extract_xls()` to perform streaming windowed chunking with repeated headers.
- [ ] In `src/aios_habit/document_extractors.py`:
  - [ ] Update `_extract_excel()` to format chunk metadata (`Chunk X/Y`) in `lines` and `section`.
- [ ] In `tests/`:
  - [ ] Add `test_excel_streaming_row_chunking_2000_rows`, `test_excel_no_cell_count_truncation_30k_cells`, and integration tests.
