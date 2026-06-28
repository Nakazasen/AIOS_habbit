# AIOS Source-Aware Retrieval + MOM 3Q Retest Report

## Implementation Summary
- **Query Intent Extraction:** Implemented deterministically in `src/aios_habit/query_intent.py` using keyword matching to categorize queries into intents (e.g., `manual_shipping_existing_line`, `design_change_running_change`, `wms_mom_agv_integration`).
- **Source-Aware Scoring:** Added scoring boosts in `src/aios_habit/rag_search.py` for target filenames (+15), sheet names (+10), and content terms (+5) based on intent.
- **Metadata-Only Penalty:** Chunks with only metadata (no extracted content) receive a -10 penalty. Off-topic penalty of -5 applied if a targeted intent query matches broad documents with no intent markers.
- **Score Explanations:** The `_score_explanation` is tracked per candidate and formatted into the RAGEvidencePack.
- **Targeted Evidence Pack:** Evidence packs now contain `_score_explanation` and `_focus_note`.
- **Strong Prompt Focus Instruction:** Injected into `build_grounded_prompt` in `src/aios_habit/ai_provider_bridge.py`.

## Validation and Tests
- Added 4 tests in `test_rag_search.py` verifying Q1, Q2, Q3 intent routing and metadata-only penalty.
- Tests passed. Total tests passing: 31 in main suite, plus 11 in notebooklm/extractors suite.
- Package import `aios_habit.case_cockpit` works.
- `git status` shows no raw docs/outputs committed. `local_runs/` remains ignored.

## Q1 / Q2 / Q3 Before vs After
- **Q1:** Remained strong (Improved YES/PARTIAL before, continues to retrieve `AMS_設計変更`).
- **Q2:** Remained strong (Retrieves `TANABAN_Master` and `AGV通信仕様`).
- **Q3:** **Fixed Regression**. The intent extraction successfully boosted `補足資料_要件内容反映版_20231110.xlsx`, `ステージングテーブル_ライン外出庫連携自動処理用.xlsx`, and `KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx` into the Top 5. The focus note successfully instructs the strong model to prioritize manual shipping logic.

## Q3 Targeting Result
- **Top Evidence:**
  1. `AMS概略フロー_入出庫・生産_20250703VN.pdf`
  2. `補足資料_要件内容反映版_20231110.xlsx`
  3. `ステージングテーブル_ライン外出庫連携自動処理用【_20231107見直し版】 (1).xlsx`
  4. `KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx`
  5. `AMS_設計変更.pdf`
- **Regression Fixed:** Yes. Generic `MaterialQueue` results were downranked, and target interface Excel files successfully surfaced to the top.

## Remaining Blockers
- PPTX extraction is not yet implemented.
- Image OCR is not yet implemented.
- UI strong answer button in Case Cockpit is missing.
- Evaluator quality heuristics.

**Raw docs committed:** NO
**Raw outputs committed:** NO
**NotebookLM parity claimed:** NO
**P1.0 opened:** NO
