# Handoff Report: Requirement 2 (Excel Extractor Streaming Row-Chunking Upgrade)

**Agent**: `teamwork_preview_explorer_survey_2`  
**Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_2`  
**Handoff Type**: Hard (Investigation & Specification Complete)  
**Target Milestone**: R2 (Excel Extractor Streaming Row-Chunking Upgrade)  

---

## 1. Observation

Direct code inspection of the Excel extraction subsystem in `AIOS_habbit` revealed the following exact facts:

1. **Hardcoded Row and Cell Limits in `src/aios_habit/excel_extractors.py:14-27`**:
   ```python
   @dataclass(frozen=True)
   class ExcelExtractionConfig:
       max_file_bytes: int = 10 * 1024 * 1024
       max_uncompressed_bytes: int = 50 * 1024 * 1024
       max_sheets: int = 12
       max_rows_per_sheet: int = 1000
       max_non_empty_cells: int = 20_000
       max_columns_per_region: int = 256
       max_images: int = 24
       max_image_bytes: int = 8 * 1024 * 1024
       max_total_image_bytes: int = 24 * 1024 * 1024
       max_image_pixels: int = 24_000_000
       max_charts: int = 48
       max_header_rows: int = 3
   ```

2. **Truncation and Premature Loop Termination in `src/aios_habit/excel_extractors.py:322-349`**:
   - `cell_count` is initialized at line 322 before the sheet loop.
   - At lines 331–333:
     ```python
     if row_number > config.max_rows_per_sheet:
         result.truncated_reasons.append(f"row limit on {sheet_name}: {config.max_rows_per_sheet}")
         break
     ```
   - At lines 340–348:
     ```python
     cell_count += 1
     if cell_count > config.max_non_empty_cells:
         result.truncated_reasons.append(f"cell limit: {config.max_non_empty_cells}")
         stop = True
         break
     ...
     if stop:
         break  # Aborts all subsequent sheets!
     ```

3. **Legacy XLS Truncation in `src/aios_habit/excel_extractors.py:417-430`**:
   - `for row_index in range(min(sheet.nrows, config.max_rows_per_sheet)):`
   - `if cell_count > config.max_non_empty_cells:` breaks out and flags truncation.

4. **Caller Contract in `src/aios_habit/document_extractors.py:366-403` (`_extract_excel`)**:
   - Consumes `extracted.regions` where each `ExcelTableRegion` provides `region.sheet`, `region.cell_range`, `region.headers`, `region.header_rows`, `region.row_range`, and `region.rows`.
   - Generates formatted `ExtractionResult` records with `sheet`, `section`, `row_range`, and text formatted as:
     `Columns: ...\nRow X: ... | ...`.

5. **Caller Contract in `src/aios_habit/rag_v2/converters.py:371-444` (`ExcelDocumentConverterAdapter`)**:
   - Consumes `extracted.regions` to build `TableData` and `DocumentElement(element_type=ElementType.TABLE)`.
   - Passes `headers`, `rows`, `cells`, `header_rows`, `merged_ranges`, `region_id`.

6. **Downstream Table Chunking in `src/aios_habit/rag_v2/chunking.py:345-440` (`_chunk_table`)**:
   - Automatically segments `TableData.rows` into chunks of `table_rows_per_chunk` rows, repeating `headers` and generating `representation_role="table_rows"` and `"table_schema"`.

---

## 2. Logic Chain

1. **Premise**: Enterprise spreadsheets (e.g. manufacturing BOMs, inventory lists, ERP production orders) frequently exceed 1,000 rows (e.g. 1,500 to 50,000 rows) and 20,000 non-empty cells.
2. **Current Failure Mode**:
   - Because `max_rows_per_sheet = 1000`, any data beyond row 1,000 is discarded (Observation 1 & 2).
   - Because `max_non_empty_cells = 20_000` accumulates across all sheets without resetting, multi-sheet workbooks or sheets with > 20 columns are prematurely terminated (Observation 2).
3. **Chunking Requirement**:
   - Simply removing the limits without chunking would create single monolithic table regions with tens of thousands of rows. Downstream flat-text chunking (`document_extractors.py:_chunk_result`) would chop lines without header context.
   - Therefore, chunking must happen at the extractor level by partitioning large row groups into discrete `ExcelTableRegion` chunks (e.g. 500 data rows per chunk) while repeating the original `header_rows` and `headers` on every chunk.
4. **Contract Preservation**:
   - `ExcelTableRegion` is extended with `chunk_index: int = 0` and `total_chunks: int = 1`.
   - `ExcelExtractionConfig` defaults `max_rows_per_sheet = None` and `max_non_empty_cells = None`, introducing `chunk_row_size = 500`.
   - Callers (`document_extractors.py`, `rag_v2/converters.py`) receive a sequence of `ExcelTableRegion` objects representing successive row slices of the table, perfectly preserving existing property names and types.

---

## 3. Caveats

1. **OpenPyXL Memory Profile**: `openpyxl.load_workbook` loads the XML DOM into memory when `read_only=False` (needed to parse charts, merged cells, images). For extremely massive workbooks (> 100,000 rows), memory consumption is higher than `read_only=True`. However, windowed chunking of the extracted rows prevents multi-gigabyte text copies in memory.
2. **Workspace Chat Upload Scope**: `src/aios_habit/workspace_chat_excel.py` has its own UI preview text size limit (`WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES` = 32KB). This is intentional for single-prompt ephemeral chat uploads, whereas full file extraction and indexing use `excel_extractors.py`.

---

## 4. Conclusion

1. Requirement 2 is clearly bounded, fully scoped, and technically straightforward to implement.
2. The hardcoded caps `max_rows_per_sheet = 1000` and `max_non_empty_cells = 20_000` in `src/aios_habit/excel_extractors.py` must be replaced with `None` (unlimited).
3. Streaming row chunking (default 500 rows per chunk) with repeated hierarchical headers, `chunk_index`, and exact `row_range` metadata must be added to `_regions()` / `_extract_openpyxl()` / `_extract_xls()`.
4. Detailed specifications and implementation steps are recorded in `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_2\analysis.md`.

---

## 5. Verification Method

### 5.1. Files to Inspect
1. `src/aios_habit/excel_extractors.py`: Verify `ExcelExtractionConfig` has `max_rows_per_sheet = None`, `max_non_empty_cells = None`, and `chunk_row_size = 500`. Verify `_regions` yields chunked `ExcelTableRegion`s with repeated headers.
2. `src/aios_habit/document_extractors.py`: Verify `_extract_excel` creates chunked `ExtractionResult` records with chunk indicators.
3. `tests/test_document_extractors.py` & `tests/test_rag_v2_converters.py`: Verify test cases pass.

### 5.2. Test Commands to Execute (Post-Implementation)
```powershell
pytest tests/test_document_extractors.py tests/test_rag_v2_converters.py tests/test_workspace_chat_excel_ingest.py -v
```

### 5.3. Invalidation Conditions
- Any test where an Excel file with > 1,500 rows has `truncated_reasons` populated or drops rows beyond 1,000.
- Any chunk after chunk 0 that fails to include the column header names.
