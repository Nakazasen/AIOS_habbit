## 2026-08-19T23:54:21Z

<USER_REQUEST>
You are teamwork_preview_test_writer_m4.
Your working directory is: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_m4
Workspace root: d:\Sandbox\AIOS_habbit
Original user request path: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Project blueprint: d:\Sandbox\AIOS_habbit\PROJECT.md
Test infra: d:\Sandbox\AIOS_habbit\TEST_INFRA.md

MANDATORY FIRST STEP: Read d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md, d:\Sandbox\AIOS_habbit\PROJECT.md, and d:\Sandbox\AIOS_habbit\TEST_INFRA.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations and tests must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- `tests/test_mom_upgrade_acceptance.py`

Task Objective (Milestone 4 Implementation):
Create a comprehensive acceptance test suite in `tests/test_mom_upgrade_acceptance.py` and run full test suite verification:
1. Test R1 Acceptance:
   - Verify that `src/aios_habit/mom_local_index.py` source code contains 0 occurrences of `q1_terms`, `q2_terms`, `q3_terms`, artificial `score += 15.0`, `score += 20.0`, or `-50.0` score penalty.
   - Verify `search_mom_index` computes non-negative BM25 scores, supports CJK tokenization (Japanese & Chinese), handles length normalization, and ranks relevant documents accurately on unseen and standard queries.
2. Test R2 Acceptance:
   - Create a test generating a large synthetic spreadsheet with >1,500 rows (e.g. 1,600 or 2,000 data rows) and multiple columns.
   - Verify `extract_excel_workbook` and `_extract_excel` in `document_extractors.py` extract ALL data rows without truncation.
   - Verify that chunks have repeated `headers` and `header_rows`, correct `chunk_index` (0, 1, 2, ...), `total_chunks`, and valid `row_range`.
   - Verify `ExcelExtractionConfig` defaults allow unlimited rows (`max_rows_per_sheet is None`) and cells (`max_non_empty_cells is None`).
3. Test R3 Acceptance:
   - Verify that `scripts/generate_ai_grounded_report.py` source code contains 0 occurrences of `POLISHED_ANSWERS`, static `scores` dictionary, and static `latencies` dictionary.
   - Verify `scripts/run_workspace_chat_12_questions.py` does not contain canned refusal strings.
   - Verify that dynamic abstention via `synthesize_evidence` properly returns `abstained=True` and `grounded=False` with `"KHÔNG ĐỦ BẰNG CHỨNG:"` on out-of-domain queries without sufficient ground truth.
4. Execute Pytest Test Execution:
   - Run tests across `tests/` to verify 100% pass rate with zero failures and zero errors.

Deliverables:
- Write `tests/test_mom_upgrade_acceptance.py`.
- Write `handoff.md` in your working directory (`d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_m4\handoff.md`) with Observation, Logic Chain, Caveats, Conclusion, and Verification Method.
- Update `progress.md`.
- Send completion message to parent via `send_message`.
</USER_REQUEST>
