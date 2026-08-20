## 2026-08-19T23:43:52Z

Investigate Requirement 2: Excel Extractor Streaming Row-Chunking Upgrade.
1. Inspect `src/aios_habit/excel_extractors.py` (and any related extraction modules in `src/aios_habit/`).
2. Identify where hardcoded limits (1,000 rows/sheet, 20,000 cells) and truncation mechanisms reside.
3. Analyze how Excel files (.xlsx, .xls) are parsed (e.g., openpyxl, iter_rows, pandas, etc.).
4. Design the streaming row-chunking specification: how to chunk large spreadsheets (>1,000 or >1,500 rows) with repeated header rows per chunk, chunk metadata (sheet name, row range, chunk index), memory safety, and seamless integration into the indexing/RAG pipeline.
5. Identify all callers of `excel_extractors.py` across `src/`, `scripts/`, and `tests/`.
6. Identify all existing excel extractor tests in `tests/`.
