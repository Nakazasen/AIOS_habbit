# AIOS Source Router and Synthesizer Design

## 1. Goal
Apply proven RAG architecture patterns (like source-type routing and specialized synthesis) to the AIOS final answer composer. This will fix issues where process questions are answered with table-mapping templates, and screenshot evidence is treated like text documents.

## 2. Hard Constraints
- **Do not replace AIOS** with another framework (LlamaIndex, Haystack, etc.). Only borrow patterns.
- **Maintain "local_only" privacy**. No external API calls for local_only packs.
- **Do not open P1.0**.
- **Do not claim AIOS replaces NotebookLM**. We are improving local AIOS to be *closer* to NotebookLM, not claiming global parity yet.
- **Do not commit `local_runs` data**.

## 3. Architecture Patterns Borrowed
1. **Source-Type Aware Routing** (from Haystack/RAGFlow): Analyze the evidence pack's file types (e.g., mostly `xlsx` vs `png` vs `pdf`) and route to a specialized prompt template.
2. **Query-Profile Aware Synthesis** (from LlamaIndex/GraphRAG): Distinguish between question intents (e.g., process troubleshooting vs. data mapping) to select the correct analytical framework.
3. **Strict Evaluator Constraints** (from RAGAS): Cap evaluation scores if the synthesis uses an mismatched template or hallucinates evidence types.

## 4. Implementation Details

### A. `src/aios_habit/source_router.py` (New File)
- **Function:** `determine_dominant_source_type(evidence_pack) -> str`
- **Logic:**
  - Count file types in the `evidence_pack.items`.
  - Return the dominant type out of `xlsx`/`csv`, `screenshot`/`png`/`jpg`, `pdf`/`pptx`, or fallback to `mixed`.

### B. `src/aios_habit/final_answer_composer.py` (Modifications)
- **Current State:** Relies heavily on a generic template and naive `_question_kind`.
- **Changes:**
  - Import `determine_dominant_source_type` from `aios_habit.source_router`.
  - Refine `_question_kind` to accurately classify questions into `troubleshooting` (process/flow), `data_mapping` (fields/tables), `visual_analysis` (images), and `general`.
  - **Template Selection:** Combine `target_source_type` (from router) and `_question_kind` to select specific synthesis rules.
    - If `troubleshooting` + `excel`: Don't just dump a table mapping; synthesize a timeline or step-by-step path.
    - If `visual_analysis` + `screenshot`: Explicitly separate "What is visible" from "What is inferred".
  - Ensure local_only safety checks remain intact.

### C. `src/aios_habit/notebooklm_compare.py` (Modifications)
- **Function:** `_score_pair(q_id, question, pair)`
- **Changes:** Add strict caps to the `aios_score`.
  - Cap at 2.0 if the AIOS answer uses a data mapping template (e.g., "bảng map", "cấu trúc", "trường dữ liệu") for a troubleshooting/process question (like Q04/Q05).
  - Cap at 2.0 if the question targets screenshots but the answer acts like it's reading a database ERD.

## 5. Validation Plan
1. Run `pytest tests/test_final_answer_composer.py` and `pytest tests/test_notebooklm_compare.py`.
2. Perform a 4Q rerun (Q04, Q06, Q10, Q12) locally.
3. Analyze results and generate `.ai/AIOS_ROUTER_SYNTHESIZER_4Q_RERUN_REPORT.md`.
