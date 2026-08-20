# E2E Test Infra: AIOS_habbit MOM System Upgrade

## Test Philosophy
- Opaque-box, requirement-driven, zero-regression.
- Tiered testing strategy:
  - **Tier 1: Feature Coverage** (MOM BM25 Search, Excel streaming chunking, Dynamic Abstention, Script live execution).
  - **Tier 2: Boundary & Corner Cases** (>1,500 rows spreadsheets, empty sheets, single-row tables, multilingual Japanese/Vietnamese CJK queries, zero-match out-of-domain questions).
  - **Tier 3: Cross-Feature Combinations** (Excel extraction -> RAG v2 converter -> Evidence packaging -> Dynamic synthesis).
  - **Tier 4: Real-World Workload Scenarios** (12 benchmark questions execution, MOM pilot end-to-end question answering).

## Feature Inventory Mapping
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | MOM BM25 Search without Hardcodes | ORIGINAL_REQUEST §R1 | ✓ | ✓ | ✓ | ✓ |
| 2 | Excel Streaming Row-Chunking (>1500 rows) | ORIGINAL_REQUEST §R2 | ✓ | ✓ | ✓ | ✓ |
| 3 | Dynamic Abstention & Canned Answers Removal | ORIGINAL_REQUEST §R3 | ✓ | ✓ | ✓ | ✓ |
| 4 | 100% Pytest Pass Rate (Zero Regression) | ORIGINAL_REQUEST §R4 | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- Framework: `pytest`
- Execution: `pytest tests/ -v`
- New Dedicated Acceptance Test File: `tests/test_mom_upgrade_acceptance.py`
  - `test_r1_mom_search_no_hardcoded_heuristics()`
  - `test_r1_mom_search_objective_ranking_and_cjk_support()`
  - `test_r2_excel_streaming_chunking_over_1500_rows()`
  - `test_r2_excel_repeated_headers_on_all_chunks()`
  - `test_r3_no_canned_answers_in_generate_ai_grounded_report()`
  - `test_r3_dynamic_abstention_on_unanswerable_queries()`
  - `test_r4_full_regression_suite_integrity()`
