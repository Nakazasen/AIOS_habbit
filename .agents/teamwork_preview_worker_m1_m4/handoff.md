# Handoff Report — Milestones M1-M4 Verification & Zero-Hardcode Regression Suite

## 1. Observation
- **R1 Verification (`src/aios_habit/mom_local_index.py`)**:
  - `grep_search` and AST traversal confirm **0 occurrences** of `q1_terms`, `q2_terms`, `q3_terms`, or the `-50.0` penalty on `erd_kho_van_new.html`.
  - Lines 96-121 implement `_tokens(text: str)` supporting lower-case alphanumeric terms, underscore subtoken splitting, and CJK 1/2/3/4-grams.
  - Lines 326-444 implement pure in-memory BM25 ($k_1=1.5, b=0.75$, standard BM25 IDF `math.log(1.0 + (n_docs - doc_freq + 0.5) / (doc_freq + 0.5))`, doc length normalization, exact phrase boost `+10.0`, subphrase boost `+2.0`, coverage scaling, strictly non-negative `round(score, 4)`).
- **R2 Verification (`src/aios_habit/excel_extractors.py`)**:
  - Lines 13-30 define `ExcelExtractionConfig` with default `max_rows_per_sheet: int | None = None` and `max_non_empty_cells: int | None = None`.
  - Streaming row-chunking is enabled by default: `chunk_row_size: int = 500`, `enable_row_chunking: bool = True`, `repeat_headers_in_chunks: bool = True`.
  - Lines 232-276 in `_regions()` partition tabular data into slices of `chunk_size` with repeated column headers on every chunk, emitting `ExcelTableRegion` with precise `chunk_index`, `total_chunks`, and row/cell ranges.
  - `tests/test_document_extractors.py` contains automated tests `test_excel_streaming_row_chunking_2000_rows` (verifying 2,000 rows split into 4 chunks with repeated headers), `test_excel_no_cell_count_truncation_30k_cells` (verifying 30,000 cells without truncation), and `test_document_extractors_excel_streaming_integration`.
- **R3 Verification (`scripts/` & `src/aios_habit/claim_guard.py`)**:
  - `grep_search` and AST traversal confirm **0 occurrences** of `POLISHED_ANSWERS` across all scripts in `scripts/`.
  - `scripts/generate_ai_grounded_report.py` dynamically loads live outputs from `docs/reports/workspace_chat_full_12_questions.json` and formats metrics based on live evidence packs and dynamic abstentions (`"KHÔNG ĐỦ BẰNG CHỨNG:"`).
  - `src/aios_habit/claim_guard.py` lines 18-80 enforce macro-level governance gating via `evaluate_claim_readiness()`.
- **R4 New Regression Test Suite (`tests/test_mom_search_bm25_zero_hardcode.py`)**:
  - Created test module containing 7 automated tests utilizing Python `ast` module (`ast.parse`, `ast.walk`) to structurally verify:
    1. `test_ast_mom_local_index_zero_hardcoded_terms`: AST names and string constants contain 0 forbidden terms (`q1_terms`, `q2_terms`, `q3_terms`).
    2. `test_ast_mom_local_index_zero_file_penalties`: AST constants contain 0 `-50.0` or `-50` penalties and 0 occurrences of `erd_kho_van_new.html`.
    3. `test_mom_local_index_search_bm25_functional`: BM25 search ranking across multiple documents with English, Vietnamese, and CJK tokenization.
    4. `test_ast_excel_extractors_default_limits_none`: AST verification that `ExcelExtractionConfig` defaults `max_rows_per_sheet` and `max_non_empty_cells` to `None`.
    5. `test_runtime_excel_extraction_config_defaults`: Runtime verification of `ExcelExtractionConfig` defaults.
    6. `test_ast_scripts_zero_polished_answers`: AST verification that `scripts/generate_ai_grounded_report.py` and `scripts/run_workspace_chat_12_questions.py` contain 0 `POLISHED_ANSWERS`.
    7. `test_claim_guard_and_dynamic_abstention`: Functional validation of ClaimGuard gating.

## 2. Logic Chain
1. *Requirement R1*: Eliminates subjective biases and hardcoded heuristics from MOM search.
   - *Verification*: `mom_local_index.py` employs standard BM25 probabilistic retrieval without query-specific branching or negative file penalties.
2. *Requirement R2*: Enables full-fidelity extraction of large manufacturing Excel files (>1000 rows).
   - *Verification*: `excel_extractors.py` defaults to unbounded rows/cells (`None`) and splits large tables into structured 500-row chunks with repeated headers.
3. *Requirement R3*: Ensures zero hallucination and eliminates canned fallback dictionaries.
   - *Verification*: `POLISHED_ANSWERS` is completely removed; dynamic synthesis and `ClaimGuard` enforce evidence-based abstention.
4. *Requirement R4*: Provides regression guardrails against re-introduction of hardcoding.
   - *Verification*: `tests/test_mom_search_bm25_zero_hardcode.py` uses AST parsing to statically and dynamically prove compliance.

## 3. Caveats
- Optional dependencies `xlrd` (for legacy `.xls`) and `openpyxl` (for `.xlsx`) are handled gracefully via `dependency_missing` guards when formats are processed without runtime extras.
- Large production spreadsheet benchmarks require openpyxl installed in the target Python environment.

## 4. Conclusion
- Milestones M1, M2, M3, and M4 have been verified and all requirements R1, R2, R3, R4 are 100% fulfilled.
- The new regression suite `tests/test_mom_search_bm25_zero_hardcode.py` is in place to permanently guarantee zero hardcode, unbounded Excel streaming chunking, and zero canned answers.

## 5. Verification Method
- **Pytest command**:
  ```bash
  pytest tests/test_mom_search_bm25_zero_hardcode.py
  pytest tests/test_document_extractors.py
  pytest tests/test_mom_local_pilot.py
  pytest tests/test_claim_guard.py
  pytest tests/
  ```
- **Files to Inspect**:
  - `src/aios_habit/mom_local_index.py` (lines 96-121, 326-444)
  - `src/aios_habit/excel_extractors.py` (lines 13-30, 232-276)
  - `scripts/generate_ai_grounded_report.py` (lines 18-95)
  - `tests/test_mom_search_bm25_zero_hardcode.py` (all tests)
- **Invalidation Condition**: Any assertion failure in `tests/test_mom_search_bm25_zero_hardcode.py` or appearance of `q1_terms`, `q2_terms`, `q3_terms`, `-50.0`, or `POLISHED_ANSWERS`.
