# Project: AIOS_habbit MOM System Upgrade & Standardization

## Architecture
AIOS_habbit is an enterprise AI assistant and knowledge retrieval system for factory and operations management (MOM / MES / WMS).
The architecture comprises:
- **MOM Search & Retrieval Engine** (`src/aios_habit/mom_local_index.py`, `src/aios_habit/mom_coverage.py`): In-memory indexing and BM25 / TF-IDF ranking over local operational documents (PDFs, HTML ERDs, Excel specifications).
- **Multi-Format Extraction Pipeline** (`src/aios_habit/excel_extractors.py`, `src/aios_habit/document_extractors.py`): Deep tabular and document extractors supporting streaming row-chunking, multi-level headers, and OCR/image extraction.
- **Dynamic Evidence & Synthesis Subsystem** (`src/aios_habit/rag_v2/evidence.py`, `src/aios_habit/rag_v2/synthesis.py`, `src/aios_habit/claim_guard.py`): Fail-closed dynamic evidence evaluation and abstention without fact leakage or canned templates.
- **Reporting & Evaluation Workflows** (`scripts/generate_ai_grounded_report.py`, `scripts/run_workspace_chat_12_questions.py`): Live benchmark evaluation over 12 standard operational queries.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| F1 | MOM Search Hardcode Removal | Remove `q1_terms`, `q2_terms`, `q3_terms`, artificial query boosts, and `-50.0` score penalty on `erd_kho_van_new.html` | M1 | ORIGINAL_REQUEST §R1 |
| F2 | BM25 / TF-IDF Hybrid Search | Implement objective in-memory BM25 ranker with CJK sub-tokenization, document length normalization, and exact phrase bonus | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Excel Hard Limit Removal | Remove `max_rows_per_sheet = 1000` and `max_non_empty_cells = 20_000` hard caps in `ExcelExtractionConfig` | M2 | ORIGINAL_REQUEST §R2 |
| F4 | Streaming Row-Chunking | Implement table partitioning into 500-row chunks with repeated hierarchical headers, `chunk_index`, and exact `row_range` | M2 | ORIGINAL_REQUEST §R2 |
| F5 | Remove Canned Answer Dictionaries | Remove `POLISHED_ANSWERS`, static scores, and latencies from `scripts/generate_ai_grounded_report.py` | M3 | ORIGINAL_REQUEST §R3 |
| F6 | Dynamic Abstention Integration | Replace canned refusal strings and query overrides in `scripts/run_workspace_chat_12_questions.py` with dynamic `synthesize_evidence()` abstention | M3 | ORIGINAL_REQUEST §R3 |
| F7 | MOM Search Integrity Tests | Test MOM search without hardcoded heuristics and verify objective ranking across queries | M4 | ORIGINAL_REQUEST §R4 |
| F8 | Large Excel Chunking Tests | Automated tests verifying >1,500 row Excel spreadsheets are extracted across chunks with repeated headers and zero data loss | M4 | ORIGINAL_REQUEST §R4 |
| F9 | Dynamic Abstention Verification Tests | Automated tests verifying dynamic refusal generation and lack of static `POLISHED_ANSWERS` | M4 | ORIGINAL_REQUEST §R4 |
| F10 | 100% Pytest Pass Rate | Verify zero failures and zero errors across the entire repository test suite | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | M1: MOM Search Standardization | Refactor `src/aios_habit/mom_local_index.py` to remove hardcodes and implement objective BM25 | none | PLANNED |
| 2 | M2: Excel Streaming Row-Chunking | Refactor `src/aios_habit/excel_extractors.py` and `src/aios_habit/document_extractors.py` | none | PLANNED |
| 3 | M3: Dynamic Abstention & Script Cleanup | Refactor `scripts/generate_ai_grounded_report.py` and `scripts/run_workspace_chat_12_questions.py` | none | PLANNED |
| 4 | M4: Comprehensive E2E & Regression Suite | Add new unit/integration tests in `tests/` and verify full suite passes 100% | M1, M2, M3 | PLANNED |

## Interface Contracts
### `mom_local_index.py` ↔ Callers (`mom_coverage.py`, `mom_benchmark.py`, `tests/`)
- Function: `search_mom_index(query: str, limit: int = 5, index_path: str | Path = INDEX_FILE) -> list[MomSearchHit]`
- Structure: `MomSearchHit(score: float, matched_terms: list[str], chunk: MomChunk)`
- Scoring semantics: Non-negative BM25 / TF-IDF score based strictly on query term overlap, term frequency, inverse document frequency, and exact phrase bonus.

### `excel_extractors.py` ↔ Callers (`document_extractors.py`, `rag_v2/converters.py`)
- Dataclass: `ExcelTableRegion(sheet: str, cell_range: str, headers: list[str], header_rows: list[list[str]], row_range: tuple[int, int], rows: list[list[Any]], chunk_index: int = 0, total_chunks: int = 1)`
- Dataclass: `ExcelExtractionConfig(..., max_rows_per_sheet: int | None = None, max_non_empty_cells: int | None = None, chunk_row_size: int = 500, enable_row_chunking: bool = True, repeat_headers_in_chunks: bool = True)`

### `run_workspace_chat_12_questions.py` & `generate_ai_grounded_report.py` ↔ `rag_v2`
- Function: `synthesize_evidence(pack: EvidencePack) -> LocalSynthesisResult`
- Behavior: Queries with insufficient ground truth produce `LocalSynthesisResult(abstained=True, grounded=False)` with structured `"KHÔNG ĐỦ BẰNG CHỨNG:"` output.

## Code Layout
- `src/aios_habit/mom_local_index.py`: In-memory MOM document indexing and BM25 search.
- `src/aios_habit/excel_extractors.py`: Excel workbook extractor with streaming row-chunking.
- `src/aios_habit/document_extractors.py`: Unified multi-modal document extraction adapter.
- `scripts/generate_ai_grounded_report.py`: Grounded benchmark report generator.
- `scripts/run_workspace_chat_12_questions.py`: End-to-end evaluation runner.
- `tests/test_mom_local_pilot.py`: MOM local index pilot tests.
- `tests/test_mom_pdf_ingestion_retrieval.py`: MOM retrieval ingestion tests.
- `tests/test_document_extractors.py`: Document & Excel extractor unit tests.
- `tests/test_workspace_chat_excel_ingest.py`: Workspace chat excel ingestion tests.
- `tests/test_mom_upgrade_acceptance.py`: Comprehensive acceptance test suite for R1–R4.
