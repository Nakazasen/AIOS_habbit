# Comprehensive Survey Report: ClaimGuard Dynamic Abstention, Canned Answers Removal, and Test Infrastructure (R3 & R4)

**Agent ID:** `teamwork_preview_explorer_survey_3`  
**Working Directory:** `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_survey_3`  
**Timestamp:** 2026-08-20T06:48:00Z  
**Target Requirements:** R3 (Dynamic Abstention & Canned Answers Removal) and R4 (Test Suite Infrastructure & Zero Regression)

---

## 1. Executive Summary

This survey provides an in-depth technical analysis of **Requirement 3 (R3)** and **Requirement 4 (R4)** for the AIOS MOM / Workspace Chat system. 

### Key Findings:
1. **`scripts/generate_ai_grounded_report.py`**: Contains a 100% static, hardcoded dictionary `POLISHED_ANSWERS` (lines 16–251) with pre-written answers, fake evaluation scores (lines 268–273), and fake latencies (lines 274–279) for benchmark questions BQ01–BQ12. It has zero live integration with retrieval backends or ClaimGuard.
2. **`scripts/run_workspace_chat_12_questions.py`**: Contains hardcoded query variants for BQ02 and BQ07 (lines 90–101) and hardcoded canned abstention text for BQ11/BQ12 (lines 122–127) explicitly mentioning *"quantum computing or blockchain technology"*, bypassing dynamic evidence evaluation.
3. **ClaimGuard & Dynamic Abstention Architecture**:
   - `src/aios_habit/claim_guard.py`: Enforces macro-level claim gating (e.g., blocking NotebookLM replacement claims without multi-domain evidence or human review).
   - `src/aios_habit/rag_v2/evidence.py` (`build_evidence_pack`): Computes lexical/semantic coverage, obligation coverage, and determines operational `answer_mode` (`EvidenceAnswerMode.ABSTAIN`, `ANSWER_WITH_LIMITS`, or `ANSWER`).
   - `src/aios_habit/rag_v2/synthesis.py` (`synthesize_evidence` / `_abstention`): Generates dynamic, citable extractive answers or fail-closed refusals (`"KHÔNG ĐỦ BẰNG CHỨNG:"` + specific `LIMITATIONS`).
4. **Test Suite Status & Architecture**:
   - Test framework: `pytest` configured via `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["src", "."]`).
   - 116 test files covering all modules: adaptive retrieval, RAG v2 synthesis, workspace chat adapters, document extractors, claim guard, case stores, and MOM local index.
   - Comprehensive test specifications are defined for R1–R4 to guarantee 100% test pass and zero regression.

---

## 2. Deep Dive: Inspection of Reporting & Evaluation Scripts

### 2.1 `scripts/generate_ai_grounded_report.py`

#### Exact Locations of Hardcoded Artifacts:
- **Lines 16–251 (`POLISHED_ANSWERS`)**:
  ```python
  POLISHED_ANSWERS = {
      "BQ01": {
          "title": "Kiến Trúc Tổng Thể Đăng Ký Lịch Sử Sản Xuất...",
          "summary": "...",
          "citations": [...]
      },
      ...
      "BQ11": {
          "title": "Giao Thức Tích Hợp Điện Toán Lượng Tử...",
          "summary": "🛡️ XÁC NHẬN TỪ CHỐI AN TOÀN...",
          "citations": [...]
      },
      "BQ12": {
          "title": "Cơ Chế Đảm Bảo Chất Lượng Bằng Blockchain...",
          "summary": "🛡️ XÁC NHẬN TỪ CHỐI AN TOÀN...",
          "citations": [...]
      }
  }
  ```
- **Lines 268–279 (`scores` & `latencies`)**:
  ```python
  scores = {
      "BQ01": "4.8 / 5.0", "BQ02": "4.7 / 5.0", ...
  }
  latencies = {
      "BQ01": "1.16s", "BQ02": "1.15s", ...
  }
  ```
- **Lines 281–296 (Direct loop over `POLISHED_ANSWERS`)**:
  Generates `docs/reports/workspace_chat_full_12_questions_polished_report.md` purely by dumping dictionary entries.

#### Remediation Plan for `generate_ai_grounded_report.py`:
- Remove `POLISHED_ANSWERS`, static `scores`, and static `latencies`.
- Dynamically ingest results from `docs/reports/workspace_chat_full_12_questions.json` (or invoke the live pipeline if missing).
- Dynamically format the Markdown report with real execution metrics, extracted claims, actual retrieved citations, and dynamic abstention status.

---

### 2.2 `scripts/run_workspace_chat_12_questions.py`

#### Exact Locations of Hardcoded Artifacts:
- **Lines 89–102 (Hardcoded Query Expansions)**:
  ```python
  variants = []
  if qid == "BQ02":
      variants = [
          {"text": "warehouse management WMS system architecture", "origin": "expansion", "target_equivalent": False},
          {"text": "production management MES integration", "origin": "expansion", "target_equivalent": False},
          {"text": "WMS to MES data connection interface", "origin": "expansion", "target_equivalent": False},
      ]
  elif qid == "BQ07":
      variants = [
          {"text": "MOM data flow connected systems", "origin": "expansion", "target_equivalent": False},
          {"text": "operator verification failures MOM", "origin": "expansion", "target_equivalent": False},
          {"text": "system architecture error handling flow", "origin": "expansion", "target_equivalent": False},
      ]
  ```
- **Lines 122–131 (Bypass of Synthesis via Hardcoded Canned String)**:
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

#### Remediation Plan for `run_workspace_chat_12_questions.py`:
- Remove question-specific `if qid == "BQ02"` / `if qid == "BQ07"` expansion branches. Use generic query planning via `aios_habit.rag_v2.query_planning` or adaptive routing.
- Remove `is_abstention_q = cat == "abstention"` and the canned text string.
- Route **all 12 questions** through `synthesize_evidence(pack)` (or `generate_workspace_ai_answer` / `synthesize_with_provider`).
- For unanswerable queries (BQ11 and BQ12), `build_evidence_pack` naturally flags `pack.answer_mode = EvidenceAnswerMode.ABSTAIN`, and `synthesize_evidence` dynamically generates the fail-closed abstention response:
  ```text
  KHÔNG ĐỦ BẰNG CHỨNG:
  - Corpus được truy xuất không thiết lập được sự kiện hoặc quan hệ mà câu hỏi yêu cầu.
  - Cần nguồn trực tiếp (ví dụ: tài liệu quy trình, bản ghi hệ thống hoặc hàng dữ liệu có mục tiêu) trước khi có thể trả lời an toàn.
  LIMITATIONS: no_target_query_evidence, no_direct_query_evidence, ...
  ```
- Track `synth_res.abstained` directly to record `status = "🛡️ Dynamic Abstention (Zero Hallucination)"` in JSON and Markdown reports.

---

## 3. ClaimGuard & Dynamic Abstention Architecture in `src/aios_habit/`

The codebase already contains a sophisticated, multi-layer evidence evaluation and abstention pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Retrieval & Filtering (BM25 / SQLite FTS5 / BGE-M3)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ SearchResponse
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Evidence Pack Builder (rag_v2/evidence.py)              │
│    - Lexical Term Coverage Check (>= 60%)                   │
│    - Semantic Support Score Check (>= 0.55)                 │
│    - Obligation & Facet Coverage Assessment                │
│    - Classifies Hard vs Soft Insufficiency Reasons          │
│    - Computes answer_mode: ABSTAIN | ANSWER_WITH_LIMITS    │
└──────────────────────────────┬──────────────────────────────┘
                               │ EvidencePack
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Synthesis & ClaimGuard (rag_v2/synthesis.py)            │
│    - If answer_mode == ABSTAIN -> _abstention() fail-closed │
│    - Validates grounded claims against citation IDs         │
│    - If Provider called -> validate_provider_synthesis      │
│      Rejects ungrounded facts / invented literals           │
└──────────────────────────────┬──────────────────────────────┘
                               │ LocalSynthesisResult
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Macro Claim Readiness (claim_guard.py)                  │
│    - Evaluates replacement claims vs domain scope & review  │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Gating Rules Summary:
| Mechanism | Module & Function | Decision Criteria | Outcome if Failed |
|---|---|---|---|
| **Lexical Coverage Gate** | `evidence.py:676-700` | Term coverage `< 0.6` and no semantic support | Adds `final_evidence_query_coverage_below_threshold` |
| **Direct Target Gate** | `evidence.py:709-720` | Query has `>=2` target terms and none found | Adds `no_target_query_evidence`, `no_direct_query_evidence` |
| **Obligation Gate** | `evidence.py:736-746` | Planned obligations not covered | Adds `all_required_obligations_missing` |
| **Operational Answer Mode** | `evidence.py:464-475` | Any hard reason present | Sets `answer_mode = EvidenceAnswerMode.ABSTAIN` |
| **Extractive Synthesis Gate** | `synthesis.py:731-740` | `pack.answer_mode == ABSTAIN` | Returns `_abstention()` with `abstained=True`, `grounded=False` |
| **Citation Validation Gate** | `synthesis.py:112-136` | Claims cite non-existent evidence IDs | Drops invalid claims or triggers `_abstention()` |
| **Provider Validation Gate** | `synthesis.py:823-840` | External model invents uncited facts | Hard stop: provider answer rejected, falls back to local synthesis |

---

## 4. Test Suite Survey & Analysis

### 4.1 Test Infrastructure Overview
- **Runner Configuration**: Pytest 8.x, configured in `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["src", "."]
  testpaths = ["tests"]
  ```
- **Total Test Files**: 116 files in `tests/`.
- **Existing Coverage of Key Components**:
  - `tests/test_claim_guard.py`: 8 test cases validating `evaluate_claim_readiness`.
  - `tests/test_rag_v2_synthesis.py`: 30+ test cases validating structured synthesis, citation validation, and dynamic abstention.
  - `tests/test_mom_local_pilot.py` & `tests/test_mom_pdf_ingestion_retrieval.py`: Tests MOM local indexing, search, and prompt construction.
  - `tests/test_workspace_chat_excel_ingest.py` & `tests/test_document_extractors.py`: Tests Excel and document parsing.

---

## 5. Test Requirements for R1–R4 (Zero Regression Specification)

To guarantee 100% test pass with zero regression across the entire project, the following test specifications must be implemented and verified:

### R1. MOM Search Cleanliness Tests
1. **`test_mom_search_no_hardcoded_heuristics_or_penalties`**:
   - Inspects `src/aios_habit/mom_local_index.py` via AST/source inspection to ensure `q1_terms`, `q2_terms`, `q3_terms`, and `-50.0` score penalties are completely eliminated.
   - Tests `search_mom_index` on synthetic corpora to verify unbiased BM25 / token scoring.
   - Verifies `erd_kho_van_new.html` receives fair, objective scores when query terms match.

### R2. Excel Streaming Row-Chunking Tests
2. **`test_excel_streaming_chunking_large_file_over_1500_rows`**:
   - Generates a synthetic Excel workbook with 1,500+ rows and multiple columns (e.g. manufacturing BOM with headers: `["Mã vật tư", "Tên linh kiện", "Số lượng", "Đơn giá", "Trạng thái"]`).
   - Invokes the streaming row-chunking extractor.
   - Verifies all rows (>1500) are extracted into sequential chunks without truncation.
   - Verifies each chunk retains the table header row for retrieval grounding.
   - Verifies no memory spikes or uncompressed limit errors occur.

### R3. Dynamic Abstention & Canned Answers Removal Tests
3. **`test_no_canned_answers_in_reporting_scripts`**:
   - Verifies `scripts/generate_ai_grounded_report.py` does not define or use `POLISHED_ANSWERS`.
   - Verifies `scripts/run_workspace_chat_12_questions.py` does not contain hardcoded abstention text for BQ11/BQ12.
4. **`test_workspace_chat_dynamic_abstention_on_unanswerable_queries`**:
   - Executes queries on absent topics (e.g. quantum computing, blockchain) against the staged vector index.
   - Asserts `build_evidence_pack` assigns `EvidenceAnswerMode.ABSTAIN`.
   - Asserts `synthesize_evidence` returns `abstained=True`, `grounded=False`, `citation_ids=()`, and structured refusal text with `LIMITATIONS`.
5. **`test_generate_ai_grounded_report_dynamic_generation`**:
   - Runs `generate_ai_grounded_report.py` to confirm it reads live run artifacts or executes live pipeline and generates a fully grounded Markdown report.

### R4. Complete Pytest Suite Pass & Regression Prevention
6. **Full Suite Execution**:
   - Run `pytest tests/` ensuring all 116 test files pass with 0 failures, 0 errors.
   - Ensure all mocks cleanly isolate external model/subprocess calls.

---

## 6. Conclusion & Recommendations

1. **R3 implementation is clean and straightforward**: All required dynamic abstention logic already exists in `aios_habit.rag_v2.evidence` and `aios_habit.rag_v2.synthesis`. The scripts `generate_ai_grounded_report.py` and `run_workspace_chat_12_questions.py` simply need to have their hardcoded dictionaries and bypasses removed and hooked up to `synthesize_evidence(pack)`.
2. **R4 testing is comprehensive**: The project has extensive test suites. Implementing the proposed automated tests for R1, R2, R3, and running the full pytest suite will ensure zero regressions.
