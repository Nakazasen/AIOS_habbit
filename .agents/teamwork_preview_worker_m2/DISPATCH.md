## 2026-08-20T06:47:49Z

You are teamwork_preview_worker_m2.
Your working directory is: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_m2
Workspace root: d:\Sandbox\AIOS_habbit
Original user request path: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Survey Handoff to read: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_2\handoff.md and analysis.md
Project blueprint: d:\Sandbox\AIOS_habbit\PROJECT.md

MANDATORY FIRST STEP: Read d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md and d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_2\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- `src/aios_habit/excel_extractors.py`
- `src/aios_habit/document_extractors.py`

Task Objective (Milestone 2 Implementation):
1. In `src/aios_habit/excel_extractors.py`:
   - Update `ExcelExtractionConfig`: remove the hardcoded limits by setting `max_rows_per_sheet: int | None = None` and `max_non_empty_cells: int | None = None` (allowing unlimited rows/cells unless explicitly bounded). Add parameters `chunk_row_size: int = 500`, `enable_row_chunking: bool = True`, `repeat_headers_in_chunks: bool = True`.
   - Update `ExcelTableRegion`: add fields `chunk_index: int = 0`, `total_chunks: int = 1`.
   - Implement streaming row-chunking in `_regions()` (and xls / openpyxl extractors): partition large tables exceeding `chunk_row_size` into consecutive chunks of rows (e.g. rows 1-500, 501-1000, etc.), repeating the hierarchical `header_rows` and `headers` on every chunk so context is never lost.
   - Populate chunk metadata (`chunk_index`, `total_chunks`, accurate `row_range`, `cell_range`).
2. In `src/aios_habit/document_extractors.py`:
   - Ensure `_extract_excel` correctly consumes chunked `ExcelTableRegion`s, emitting `ExtractionResult` records with chunk indicators in section titles and full row ranges.
3. Execute test validation: run existing excel extraction tests (e.g. `tests/test_document_extractors.py`, `tests/test_rag_v2_converters.py`, `tests/test_workspace_chat_excel_ingest.py`).

Deliverables:
- Write `handoff.md` in your working directory (.agents/teamwork_preview_worker_m2/handoff.md) documenting: Observation, Logic Chain, Caveats, Conclusion, Verification Method (with test commands and outputs).
- Update `progress.md`.
- Send completion message to parent via `send_message`.
