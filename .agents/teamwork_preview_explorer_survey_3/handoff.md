# Handoff Report: Survey of R3 (ClaimGuard Dynamic Abstention & Canned Answers Removal) and R4 (Test Suite Infrastructure)

**Author:** `teamwork_preview_explorer_survey_3`  
**Working Directory:** `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_3`  
**Timestamp:** 2026-08-20T06:48:30Z  
**Handoff Type:** Hard (Complete)

---

## 1. Observation

1. **`scripts/generate_ai_grounded_report.py` (lines 16–251 & 268–279)**:
   - Verbatim code defines static dictionary `POLISHED_ANSWERS = {"BQ01": {...}, ... "BQ12": {...}}` with 100% pre-written answers, titles, summaries, and citations.
   - Verbatim code defines static `scores = {"BQ01": "4.8 / 5.0", ...}` and `latencies = {"BQ01": "1.16s", ...}`.
   - Lines 281–296 write `docs/reports/workspace_chat_full_12_questions_polished_report.md` by directly iterating over `POLISHED_ANSWERS`.
2. **`scripts/run_workspace_chat_12_questions.py` (lines 89–101 & 120–131)**:
   - Verbatim code in lines 89–101 injects manual query expansion variants specifically for `"BQ02"` and `"BQ07"`.
   - Verbatim code in lines 122–127 bypasses evidence synthesis for abstention categories:
     ```python
     is_abstention_q = cat == "abstention"
     if is_abstention_q:
         answer_text = (
             "Based on the provided factory operations, MOM/WMS architecture, and production manuals, "
             "there is no information or protocol regarding this topic in the company documentation. "
             "The factory system does not utilize quantum computing or blockchain technology."
         )
     else:
         synth_res = synthesize_evidence(pack)
         answer_text = synth_res.answer
     ```
3. **`src/aios_habit/rag_v2/evidence.py` (lines 464–475 & 676–751)**:
   - `build_evidence_pack` evaluates `final_evidence_coverage`, semantic support score, and obligation coverage.
   - When evidence is insufficient (e.g. `final_evidence_coverage < 0.6` and no target matches), it sets `pack.answer_mode = EvidenceAnswerMode.ABSTAIN` with hard insufficiency reasons (`no_target_query_evidence`, `no_direct_query_evidence`, `all_required_obligations_missing`).
4. **`src/aios_habit/rag_v2/synthesis.py` (lines 731–740 & 1378–1397)**:
   - `synthesize_evidence` checks `if pack.answer_mode == EvidenceAnswerMode.ABSTAIN:` and calls `_abstention(pack, reasons)`.
   - `_abstention` produces a structured, grounded refusal with `"KHÔNG ĐỦ BẰNG CHỨNG:"` and explicit `LIMITATIONS: <reasons>`, returning `LocalSynthesisResult(abstained=True, grounded=False, citation_ids=())`.
5. **`tests/` Test Suite Structure**:
   - `pyproject.toml` (lines 64–67) configures `[tool.pytest.ini_options]` with `pythonpath = ["src", "."]` and `testpaths = ["tests"]`.
   - 116 test files exist in `tests/`, including `test_claim_guard.py` (8 tests), `test_rag_v2_synthesis.py` (30+ tests), `test_mom_local_pilot.py`, `test_workspace_chat_excel_ingest.py`, and `test_adaptive_retrieval.py`.

---

## 2. Logic Chain

1. From **Observation 1**, `generate_ai_grounded_report.py` is entirely decoupled from the actual retrieval/synthesis pipeline and outputs purely hardcoded mock data (`POLISHED_ANSWERS`). To satisfy R3, this dictionary must be removed and replaced with dynamic data loading from live pipeline execution.
2. From **Observation 2**, `run_workspace_chat_12_questions.py` uses hardcoded metadata checks (`cat == "abstention"`) and a canned string mentioning quantum computing/blockchain instead of letting the underlying retrieval and synthesis engine determine whether to answer or abstain.
3. From **Observations 3 & 4**, the RAG v2 engine (`evidence.py` and `synthesis.py`) already contains a fully functional, fail-closed dynamic abstention mechanism (`EvidenceAnswerMode.ABSTAIN` and `_abstention()`). When unanswerable questions (like BQ11 and BQ12) are routed through `synthesize_evidence(pack)`, the engine automatically returns a compliant, dynamic abstention response with `abstained=True` and `grounded=False`.
4. Therefore, connecting all 12 questions in `run_workspace_chat_12_questions.py` to `synthesize_evidence(pack)` without any canned bypasses will cleanly achieve dynamic abstention and eliminate all hardcoded answers.
5. From **Observation 5**, the test suite in `tests/` is well-structured and comprehensive. Adding targeted tests for R1 (MOM search without hardcodes), R2 (Excel streaming chunking > 1500 rows), and R3 (dynamic abstention without canned answers) will provide full verification and guarantee 100% pytest pass with zero regression for R4.

---

## 3. Caveats

1. The test environment in Windows PowerShell had an interactive permission prompt for `run_command` (pytest collection). Static analysis of all 116 test files, `pyproject.toml`, and source files was conducted instead.
2. Live BGE-M3 dense embedding requires the local model weights in `local_runs/` or config path when running end-to-end embedding tests; unit tests in `tests/test_rag_v2_synthesis.py` and `tests/test_claim_guard.py` use mocks and synthetic fixtures to run deterministically and fast without GPU or external models.

---

## 4. Conclusion

- **Requirement 3 is clearly scoped and ready for implementation**:
  - Delete `POLISHED_ANSWERS`, static `scores`, and `latencies` from `scripts/generate_ai_grounded_report.py`.
  - Delete hardcoded expansions and the canned abstention string from `scripts/run_workspace_chat_12_questions.py`.
  - Pass all queries through `synthesize_evidence(pack)` and check `synth_res.abstained` dynamically.
- **Requirement 4 has concrete test specifications**:
  - Unit tests to be added:
    1. `test_mom_search_no_hardcoded_heuristics_or_penalties` (verifies no `q1_terms`, `q2_terms`, `q3_terms`, `-50.0` in MOM search).
    2. `test_excel_streaming_chunking_large_file_over_1500_rows` (verifies complete streaming chunking of >1500 row Excel spreadsheets).
    3. `test_no_canned_answers_in_reporting_scripts` (verifies absence of `POLISHED_ANSWERS` and canned text).
    4. `test_workspace_chat_dynamic_abstention_on_unanswerable_queries` (verifies dynamic refusal generation for out-of-scope queries).
  - All existing 116 test files in `tests/` must pass with 100% success rate.

---

## 5. Verification Method

1. **Verify Canned Removal in `scripts/generate_ai_grounded_report.py`**:
   - Inspect lines 16–280 of `scripts/generate_ai_grounded_report.py` to confirm `POLISHED_ANSWERS` is removed.
2. **Verify Dynamic Abstention in `scripts/run_workspace_chat_12_questions.py`**:
   - Inspect lines 120–135 of `scripts/run_workspace_chat_12_questions.py` to confirm `is_abstention_q` canned text branch is removed and `synthesize_evidence(pack)` is called for all questions.
3. **Verify Dynamic Abstention in Tests**:
   - Inspect `tests/test_rag_v2_synthesis.py:924-934` (`test_abstention_explains_scope_and_required_evidence_without_facts`).
4. **Execute Pytest Suite**:
   - Run `pytest tests/` and verify all tests pass with 0 failures and 0 errors.
