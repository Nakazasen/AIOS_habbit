## 2026-08-20T06:47:49Z
You are teamwork_preview_worker_m1.
Your working directory is: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_m1
Workspace root: d:\Sandbox\AIOS_habbit
Original user request path: d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md
Survey Handoff to read: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_1\handoff.md and analysis.md
Project blueprint: d:\Sandbox\AIOS_habbit\PROJECT.md

MANDATORY FIRST STEP: Read d:\Sandbox\AIOS_habbit\.agents\ORIGINAL_REQUEST.md and d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
- `src/aios_habit/mom_local_index.py`

Task Objective (Milestone 1 Implementation):
1. Completely remove all hardcoded keyword lists (`q1_terms`, `q2_terms`, `q3_terms`), intent flags (`query_has_q1`, `query_has_q2`, `query_has_q3`), artificial score multipliers (`+15.0 * ...`, `+20.0 * ...`), and the targeted score penalty `-50.0` on `erd_kho_van_new.html` from `src/aios_habit/mom_local_index.py`.
2. Implement an objective in-memory BM25 / TF-IDF ranker with:
   - CJK n-gram sub-tokenization (e.g. 2-grams for Japanese / CJK characters) and standard word tokenization.
   - Standard BM25 IDF: `log(1 + (N - df + 0.5) / (df + 0.5))`.
   - Document length normalization: `tf / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))` (e.g., k1=1.5, b=0.75).
   - Domain-neutral exact phrase boost and metadata / title weighting (e.g. source filename or section match).
   - Non-negative score calculation.
3. Ensure exact preservation of public function signatures and return types:
   - `search_mom_index(query: str, limit: int = 5, index_path: str | Path = INDEX_FILE) -> list[MomSearchHit]`
   - `MomSearchHit(score: float, matched_terms: list[str], chunk: MomChunk)`
4. Execute test validation: run relevant pytest tests (e.g. `tests/test_mom_local_pilot.py`, `tests/test_mom_pdf_ingestion_retrieval.py`, `tests/test_rag_v2_hardcode_guard.py`).

Deliverables:
- Write `handoff.md` in your working directory (.agents/teamwork_preview_worker_m1/handoff.md) documenting: Observation, Logic Chain, Caveats, Conclusion, Verification Method (with test commands and outputs).
- Update `progress.md`.
- Send completion message to parent via `send_message`.
