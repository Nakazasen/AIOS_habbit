# Handoff Report: R1 Survey (MOM Local Index & Search Hardcode Removal)

**Agent**: `teamwork_preview_explorer_survey_1`  
**Role**: Explorer / Survey Specialist  
**Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_1`  
**Target Milestone**: Survey R1 - MOM Search Hardcode Removal  

---

## 1. Observation

1. **Hardcoded Keyword Lists in `src/aios_habit/mom_local_index.py:304-310`**:
   ```python
   # Q1 target terms (MES/MOM comparison)
   q1_terms = ["mes", "mom", "mes_mom", "momデータ連携", "実行", "製造", "traceability", "scheduling", "quality", "inventory"]
   # Q2 target terms (Production History system)
   q2_terms = ["生産履歴", "着完工", "ラインアウト", "復帰登録", "修理内容入力", "部品供給停止", "再開登録", "工程在庫修正", "戻入", "分割入庫", "製造人員登録"]
   # Q3 target terms (Manual Shipping Excel metadata)
   q3_terms = ["manualshipping_existinglineauto_inbounddownload", "item_code", "item_rev", "sup_line", "process_id", "oricon_id", "containername", "kdcrenameshipchangeqty"]
   ```

2. **Query Overfitting & Artificial Boosts in `src/aios_habit/mom_local_index.py:312-367`**:
   - Query intent detection via `query_has_q1 = any(t in q for t in q1_terms)`, `query_has_q2`, `query_has_q3` (lines 312–314).
   - Artificial boosts of `+15.0 * len(matched_q1)` + `10.0` for PDF + `15.0` for filename substrings (lines 333–340).
   - Artificial boosts of `+15.0 * len(matched_q2)` + `10.0` for PDF + `15.0` for filename substrings (lines 343–350).
   - Targeted penalty `score -= 50.0` explicitly on `erd_kho_van_new.html` (lines 353–356).
   - Artificial boosts of `+20.0 * len(matched_q3)` + `10.0` for Excel + `15.0` for sheet/filename substrings (lines 359–366).

3. **Existing Retrieval Implementations in Codebase**:
   - `src/aios_habit/rag_search.py:215-232`: Implements SQLite FTS5 `bm25(chunk_fts)` with score inversion (`-fts_score` or `1.0 / (1.0 + fts_score)`).
   - `src/aios_habit/rag_v2/index.py:2999-3130`: Implements generic deterministic candidate scoring (`_score_candidate`) featuring CJK n-grams (`_CJK_RE`), token frequency capping (`min(5.0, raw)`), exact phrase bonuses (`+4.0` text, `+3.0` source), metadata weighting (`+2.0` source tokens, `+1.0` structure tokens), and domain-neutral intent analysis.

4. **Callers and Dependents Across Codebase**:
   - `src/aios_habit/mom_coverage.py`: Imports `MomChunk, build_mom_local_index, load_mom_chunks` (lines 10, 107, 108).
   - `src/aios_habit/mom_benchmark.py`: `generate_mom_grounded_answer` consumes search hits with `.score`, `.matched_terms`, `.chunk` (lines 186–240).
   - `scripts/audit_mom_corpus.py`: Calls `summarize_mom_coverage` (line 33), which invokes `build_mom_local_index`.
   - `tests/test_mom_local_pilot.py`: Invokes `build_mom_local_index`, `search_mom_index`, `build_mom_qa_prompt`, `create_mom_case_from_hit`, `generate_safe_benchmark_questions`.
   - `tests/test_mom_pdf_ingestion_retrieval.py`: Invokes `build_mom_local_index`, `search_mom_index` across 4 test cases.
   - `tests/test_rag_v2_hardcode_guard.py:40`: Quarantines `aios_habit.mom_local_index` from `rag_v2` imports.

5. **Existing MOM Search Tests**:
   - `tests/test_mom_local_pilot.py`: 8 test functions exercise `search_mom_index` on synthetic text, html, pptx, xlsm, draft case creation, and prompt packing.
   - `tests/test_mom_pdf_ingestion_retrieval.py`: Tests Q1 MES/MOM retrieval, Q2 Production History retrieval vs ERD, and Q3 Manual Shipping schema retrieval.

---

## 2. Logic Chain

1. **Step 1 (Observation 1 & 2)**: The presence of static term sets (`q1_terms`, `q2_terms`, `q3_terms`), query intent flags, artificial +15/+20 point multipliers, and the `-50.0` penalty on `erd_kho_van_new.html` directly confirms that `mom_local_index.py` contains hardcoded retrieval heuristics tailored to specific benchmark questions.
2. **Step 2 (Observation 3)**: An objective, generic BM25 / TF-IDF ranking algorithm (with IDF, length normalization, CJK n-gram sub-tokenization, metadata token weighting, and exact phrase matching) can rank relevant chunks naturally based on term overlap and density without any query-specific logic.
3. **Step 3 (Observation 4 & 5)**: All existing tests in `tests/test_mom_local_pilot.py` and `tests/test_mom_pdf_ingestion_retrieval.py` evaluate queries where target documents contain relevant keyword matches (e.g. `MES_MOM_Linkage.pdf` for MES/MOM query; Japanese spec for Japanese query; `ManualShippingSpec.xlsx` for manual shipping query; `ERD_Kho_Van_NEW.html` for ERD query).
4. **Step 4 (Step 2 + Step 3)**: Standardizing `search_mom_index` to in-memory BM25 / TF-IDF with exact phrase and metadata boosts will naturally pass 100% of the existing tests while simultaneously generalizing to any unseen query and eliminating all hardcoded heuristics.
5. **Step 5 (Observation 4)**: Maintaining the existing function signature `search_mom_index(query: str, limit: int = 5, index_path: str | Path = INDEX_FILE) -> list[MomSearchHit]` and dataclass structures guarantees zero breaking changes across all callers (`mom_coverage.py`, `mom_benchmark.py`, `test_mom_local_pilot.py`, `test_mom_pdf_ingestion_retrieval.py`).

---

## 3. Caveats

- **Scope Boundary**: This report focuses on Requirement 1 (surveying `mom_local_index.py` hardcoding and ranking). Excel extraction limits (>1000 rows streaming chunking) belong to Requirement 2, and `POLISHED_ANSWERS` canned response removal in scripts belongs to Requirement 3.
- **RAG v2 Integration**: While `rag_v2` provides full SQLite FTS5 + BGE-M3 vector search, `mom_local_index.py` is quarantined from `rag_v2` and operates over flat JSONL files (`mom_local_index.jsonl`). An in-memory BM25 ranker inside `mom_local_index.py` maintains this decoupled architecture without requiring vector models or SQLite schema migrations for the MOM pilot.

---

## 4. Conclusion

- `src/aios_habit/mom_local_index.py` lines 304–367 must be refactored:
  1. Delete `q1_terms`, `q2_terms`, `q3_terms`.
  2. Delete `query_has_q1`, `query_has_q2`, `query_has_q3`.
  3. Delete all artificial `score += 15.0 * ...`, `score += 20.0 * ...`, and `score -= 50.0` statements.
  4. Replace the ranking loop with a clean, objective BM25 / TF-IDF algorithm supporting CJK n-grams, document length normalization, metadata token matching, and exact phrase boosts.
- All callers and existing tests are fully mapped and will continue to function seamlessly post-refactoring.

---

## 5. Verification Method

To independently verify these findings:
1. Inspect `src/aios_habit/mom_local_index.py` lines 304–367 to confirm verbatim hardcoded terms and penalty.
2. Inspect `tests/test_mom_pdf_ingestion_retrieval.py` lines 74–207 to verify test expectations on Q1, Q2, and Q3 queries.
3. Inspect `tests/test_rag_v2_hardcode_guard.py` line 40 to verify `aios_habit.mom_local_index` quarantine.
4. Run pytest test suite once implemented:
   `pytest tests/test_mom_local_pilot.py tests/test_mom_pdf_ingestion_retrieval.py tests/test_rag_v2_hardcode_guard.py`
