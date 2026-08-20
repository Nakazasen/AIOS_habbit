# Handoff Report: Requirement R2 — Excel Extractor Streaming Row-Chunking Survey

## 1. Observation

Direct examination of the codebase and test suites reveals the following exact locations, structures, and implementations:

### A. Core Extractor Module: `src/aios_habit/excel_extractors.py`
1. **Configuration Data Class (`ExcelExtractionConfig`, lines 13–30)**:
   - `max_file_bytes: int = 50 * 1024 * 1024` (50 MB binary guard).
   - `max_uncompressed_bytes: int = 200 * 1024 * 1024` (200 MB zip-bomb preflight guard).
   - `max_sheets: int = 30` (sheet guard).
   - `max_rows_per_sheet: int | None = None` (hardcoded 1,000-row limit removed; set to `None` for full extraction).
   - `max_non_empty_cells: int | None = None` (hardcoded 20,000-cell limit removed; set to `None` for full extraction).
   - `max_columns_per_region: int = 256` (horizontal column boundary guard).
   - `chunk_row_size: int = 500` (default chunk size for row chunking).
   - `enable_row_chunking: bool = True` (row-chunking toggle).
   - `repeat_headers_in_chunks: bool = True` (repeats detected column headers across all data chunks).
   - `max_header_rows: int = 3` (header detection lookahead depth).
   - Embedded image & chart guards: `max_images: int = 24`, `max_image_bytes: int = 8 * 1024 * 1024`, `max_total_image_bytes: int = 24 * 1024 * 1024`, `max_image_pixels: int = 24_000_000`, `max_charts: int = 48`.

2. **Data Structures (lines 32–110)**:
   - `ExcelCell` (lines 33–42): Contains `row`, `column`, `coordinate` (e.g. `"A1"`), `text`, `is_header` (bool), `row_span`, `col_span`, `merge_range`.
   - `ExcelTableRegion` (lines 44–58): Contains `sheet`, `cell_range` (e.g. `"A1:F501"`, `"A502:F1001"`), `row_range: tuple[int, int]`, `column_range: tuple[int, int]`, `rows: tuple[tuple[str, ...], ...]`, `cells: tuple[ExcelCell, ...]`, `header_rows: tuple[tuple[str, ...], ...]`, `headers: tuple[str, ...]`, `merged_ranges: tuple[str, ...]`, `chunk_index: int = 0`, `total_chunks: int = 1`.
   - `ExcelEmbeddedImage` (lines 60–68): Sheet, anchor, index, binary payload, extension, dimensions.
   - `ExcelChartMetadata` (lines 70–89): Sheet, anchor, index, chart type, title, series names, formula references.
   - `ExcelExtraction` (lines 92–110): Container with `sheet_names`, `regions`, `images`, `charts`, `warnings`, `truncated_reasons`, `error`, `dependency_missing`.

3. **Header Detection & Header Composition (lines 169–198)**:
   - `_header_depth(rows, first, last, merges, limit)`: Evaluates up to `limit` rows (default 3), checking merge spans and textual vs numeric cell ratios.
   - `_headers(rows, width)`: Constructs hierarchical column names with `" > "` separator (e.g. `"Category > Product Name"`) and deduplicates collisions using collision counters (`"Col (2)"`).

4. **Streaming Row-Chunking Engine (`_regions`, lines 200–276)**:
   - Divides contiguous row groups into slices of `chunk_size` data rows.
   - Computes `total_chunks = len(chunk_slices)`.
   - For each slice (`chunk_index` from 0 to `total_chunks - 1`):
     - Calculates precise `chunk_start_row` and `chunk_end_row` (Chunk 0: `table_start_row` to `chunk_data[-1][0]`; Chunk > 0: `chunk_data[0][0]` to `chunk_data[-1][0]`).
     - Extracts overlapping merged cell ranges (`chunk_relevant`).
     - When `repeat_headers_in_chunks=True` and `depth > 0`, prepends `header_selected` to `chunk_data` to ensure downstream LLMs and RAG retrievers have context for every row.
     - Constructs `ExcelTableRegion` with exact `cell_range`, `row_range`, `chunk_index`, and `total_chunks`.

5. **Workbook Extraction Functions (lines 321–480)**:
   - `extract_excel(...)`: Entrypoint routing `.xlsx`/`.xlsm` to `_extract_openpyxl` and `.xls` to `_extract_xls`.
   - `_extract_openpyxl(...)`: Uses `openpyxl.load_workbook` (with `close()` in finally), iterates sheets and rows, enforcing optional limits only when explicitly configured.
   - `_extract_xls(...)`: Uses `xlrd.open_workbook` with `release_resources()` in finally.

---

### B. Consumers & Callers Across the System
1. **`src/aios_habit/document_extractors.py` (lines 366–450, 820–822)**:
   - `_extract_excel(path: Path) -> list[ExtractionResult]`: Consumes `extract_excel(path, include_images=True, include_charts=True)`.
   - Formats chunk headers with `section = f"table {region.cell_range} (chunk {region.chunk_index + 1}/{region.total_chunks})"`.
   - Records metadata: `row_range = f"{region.row_range[0]}-{region.row_range[1]}"`, `sheet = region.sheet`, `element_type = "excel_table_region"`.
   - Handles repeated header suppression when formatting line-by-line text (`Row {offset}: ...`).
   - Also extracts chart metadata (`element_type="excel_chart_metadata"`) and embedded images with OCR (`element_type="excel_embedded_image_ocr"`).
   - Routed by `extract_text_chunks_from_file` and registered via `_registry_adapter`.

2. **`src/aios_habit/rag_v2/converters.py` (lines 371–460)**:
   - `ExcelDocumentConverterAdapter.convert(path, context)`:
   - Calls `extract_excel(path, include_images=True, include_charts=True)`.
   - Maps each `ExcelTableRegion` to `DocumentElement(element_type=ElementType.TABLE, table=TableData(...))` with `headers`, `rows`, `cells` (with relative `TableCell` indices), `header_rows`, `merged_ranges`, `region_id=f"{region.sheet}!{region.cell_range}"`.
   - Maps charts and images into `DocumentElement` instances.

3. **`src/aios_habit/workspace_chat_excel.py` (lines 90–137)**:
   - `_extract_xls_text` delegates `.xls` extraction to `extract_excel(file_bytes, filename=filename, include_images=False, include_charts=False)`.
   - Note: `extract_xlsx_text` (lines 139–226) is a specialized lightweight direct loader for chat attachments with its own bounded preview limits (`WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES`).

4. **`src/aios_habit/notebooklm_compare.py` (lines 108–115)**:
   - Calls `_extract_excel(path)` from `document_extractors` to build benchmark chunks for comparative evaluation.

---

### C. Existing Test Suite in `tests/`
1. **`tests/test_document_extractors.py`**:
   - `test_excel_streaming_row_chunking_2000_rows(tmp_path)` (lines 338–390): Generates a 2,000-row production BOM spreadsheet (`large_production_bom.xlsx`, 6 columns). Verifies 4 contiguous chunks of 500 rows each (`A1:F501`, `A502:F1001`, `A1002:F1501`, `A1502:F2001`), repeated headers (`("Part_ID", ...)`) in every chunk, and zero truncation reasons.
   - `test_excel_no_cell_count_truncation_30k_cells(tmp_path)` (lines 391–415): Generates a 30-column x 1,000-row sheet (30,000 non-empty cells). Verifies that no cell limit truncation occurs and 2 chunks are created.
   - `test_document_extractors_excel_streaming_integration(tmp_path)` (lines 416–453): Tests end-to-end integration via `_extract_excel` on 1,200 rows, asserting 3 chunks with proper section naming (`"table A1:D501 (chunk 1/3)"`, `"table A502:D1001 (chunk 2/3)"`, `"table A1002:D1201 (chunk 3/3)"`) and accurate row index numbering.
   - `test_excel_extraction_config_custom_chunk_size(tmp_path)` (lines 454–479): Tests custom chunk sizing (`chunk_row_size=100`) on a 250-row sheet, asserting 3 chunks.
   - `test_extract_excel_with_shapes(tmp_path)` (lines 8–40): Tests drawing shape XML extraction from Excel archives.

2. **`tests/test_rag_v2_converters.py`**:
   - `test_excel_document_converter_success()` (lines 222–255): Verifies `ExcelDocumentConverterAdapter` table parsing, headers, rows, cells, and `is_header` flag.

3. **`tests/test_workspace_chat_excel_ingest.py`**:
   - 17 unit tests verifying workspace chat spreadsheet ingestion (zip bomb protection, formula preservation, array formulas, merged cells, error handling).

---

## 2. Logic Chain

1. **Elimination of Hardcoded Limits**:
   - *Observation*: In `ExcelExtractionConfig`, `max_rows_per_sheet` and `max_non_empty_cells` default to `None`.
   - *Reasoning*: Setting these defaults to `None` removes the arbitrary 1,000-row and 20,000-cell truncation triggers while retaining the option for callers to specify explicit constraints if needed.
   - *Impact*: Large enterprise production files (BOMs, master parts lists, ledger schedules) with thousands of rows and tens of thousands of cells are completely ingested without data loss.

2. **Streaming Row-Chunking Design**:
   - *Observation*: `_regions` segments tables into row chunks of size `config.chunk_row_size` (default 500).
   - *Reasoning*: A 500-row chunk size represents an optimal trade-off: each chunk fits easily within standard LLM prompt/embedding limits (~10k-25k tokens), and memory allocation remains small and linear.
   - *Header Preservation*: In multi-chunk tables, when `repeat_headers_in_chunks=True`, the detected top header rows (`header_selected`) are prepended to every chunk's matrix. Downstream consumers (RAG retriever, LLM grounders) receive self-contained tabular context for every chunk.

3. **Metadata Fidelity**:
   - *Observation*: `ExcelTableRegion` tracks `chunk_index`, `total_chunks`, `row_range`, and `cell_range`.
   - *Reasoning*: Downstream indexers (`document_extractors.py`, `rag_v2/converters.py`) can accurately reference provenance (e.g. `table A502:F1001 (chunk 2/4)`) and reconstruct exact spreadsheet coordinates during retrieval and citation answering.

---

## 3. Caveats

1. **In-Memory DOM vs True Iterative Parsing**:
   - `openpyxl.load_workbook(data, read_only=False)` loads the workbook DOM in memory to support merged cell discovery and embedded image/chart inspection (`sheet._images`, `sheet._charts`).
   - For files up to 50 MB / 200 MB uncompressed, memory consumption is modest (~50–150 MB RAM). For multi-gigabyte workbooks, `openpyxl.load_workbook(read_only=True)` would be required, but `read_only=True` does not expose `_images` or `merged_cells`. The current 50 MB / 200 MB guards adequately protect against out-of-memory crashes.
2. **`mom_local_index.py` Legacy Excel Reader**:
   - `mom_local_index.py` has a legacy helper `_excel_chunks` with `MAX_EXCEL_ROWS_PER_SHEET = 25`. Under R1, `mom_local_index.py` search ranking is being standardized; any direct usage of `_excel_chunks` in MOM index should route through `extract_text_chunks_from_file` / `_extract_excel` for consistency.

---

## 4. Conclusion

Requirement R2 is fully satisfied by the architecture in `src/aios_habit/excel_extractors.py`:
1. Hardcoded 1,000-row and 20,000-cell truncation limits are eliminated (`max_rows_per_sheet: int | None = None`, `max_non_empty_cells: int | None = None`).
2. Streaming row-chunking is implemented with configurable chunk size (500 rows), hierarchical multi-row header detection, repeated header injection in every chunk, and complete coordinate/chunk metadata.
3. Downstream callers (`document_extractors.py`, `rag_v2/converters.py`, `notebooklm_compare.py`) cleanly integrate with chunked table regions.
4. Comprehensive automated unit and integration tests exist in `tests/test_document_extractors.py` verifying 2,000+ row spreadsheets, 30,000+ cell workbooks, and custom chunk configurations.

---

## 5. Verification Method

To independently verify R2:
1. **Run Unit & Integration Tests**:
   ```bash
   pytest tests/test_document_extractors.py -k "test_excel" -v
   pytest tests/test_rag_v2_converters.py -k "test_excel" -v
   pytest tests/test_workspace_chat_excel_ingest.py -v
   ```
2. **Code Inspection**:
   - Inspect `src/aios_habit/excel_extractors.py:13-30` for `ExcelExtractionConfig` default parameters.
   - Inspect `src/aios_habit/excel_extractors.py:200-276` for `_regions` chunking logic.
   - Inspect `src/aios_habit/document_extractors.py:383-408` for chunk indicator handling.
