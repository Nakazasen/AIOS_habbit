# Empirical Challenge Handoff Report: Dynamic Abstention, ClaimGuard & Dynamic Script Execution

**Agent**: Empirical Challenger 2 (critic, specialist)  
**Target Subsystems**:
- Dynamic Abstention & Claim Readiness (`src/aios_habit/claim_guard.py`, `src/aios_habit/rag_v2/synthesis.py`)
- Dynamic Benchmark & Reporting Execution (`scripts/generate_ai_grounded_report.py`, `scripts/run_workspace_chat_12_questions.py`)  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Dynamic Abstention & Grounded Synthesis (`src/aios_habit/rag_v2/synthesis.py`)
- **Abstention Structure & Triggering**:
  - In `src/aios_habit/rag_v2/synthesis.py` (lines 1378–1398), `_abstention(pack, reasons)` constructs a fail-closed Vietnamese standard refusal format:
    ```
    KHÔNG ĐỦ BẰNG CHỨNG:
    - Corpus được truy xuất không thiết lập được sự kiện hoặc quan hệ mà câu hỏi yêu cầu.
    - Cần nguồn trực tiếp (ví dụ: tài liệu quy trình, bản ghi hệ thống hoặc hàng dữ liệu có mục tiêu) trước khi có thể trả lời an toàn.
    LIMITATIONS: <reasons>
    ```
  - It returns `LocalSynthesisResult(answer=..., claims=(), citation_ids=(), grounded=False, abstained=True, abstention_reasons=..., answer_mode="abstain")`.
- **Handling of Out-of-Domain Queries**:
  - For unrepresented domains (e.g. quantum computing BQ11, blockchain BQ12, cooking recipes, random strings), retrieval finds 0 chunks or fails the lexical/semantic relevance threshold (`final_evidence_query_coverage_below_threshold`, `no_target_query_evidence`, `no_direct_query_evidence`).
  - In `evidence.py` (lines 749–751), these missing-evidence reasons are classified as hard insufficiency reasons (`hard_insufficiency_reasons`), forcing `answer_mode = EvidenceAnswerMode.ABSTAIN`.
  - In `synthesis.py` (lines 731–739), `synthesize_evidence(pack)` immediately delegates to `_abstention()` without performing answer composition.
- **Handling of Corrupted & Adversarial Evidence Packs**:
  - *Empty Items*: If `pack.items` is empty, `no_citable_evidence` is flagged, cleanly triggering `_abstention()`.
  - *Missing Citations*: `validate_grounded_claims()` (lines 112–135) flags `claim_N_missing_citation`. If fallback cannot resolve citations, synthesis abstains cleanly with `no_valid_grounded_claims`.
  - *Unknown / Mismatched Citation Labels*: Flagged as `claim_N_unknown_citation` or `claim_N_evidence_mismatch`.
  - *Unsupported Critical Literals*: In provider synthesis, `validate_provider_synthesis_answer()` (lines 402–414) scans for critical numbers, percentages, and identifiers; if not present in cited text, `provider_answer_unsupported_critical_literal` is triggered, immediately blocking provider answer adoption.
  - *Script Mismatches*: `_provider_answer_has_script_mismatch()` (lines 334–349) detects foreign script hallucination on Latin queries and fails validation.
  - *Budget Overflow*: If synthesized text exceeds `_MAX_LOCAL_ANSWER_CHARS` (2,400 chars), lines 810–811 trigger `_abstention()` with `local_answer_budget_exceeded`.

### 1.2 ClaimGuard Governance Engine (`src/aios_habit/claim_guard.py`)
- `evaluate_claim_readiness()` evaluates 8 predefined claim types (`general_notebooklm_replacement`, `daily_replacement`, `notebooklm_parity`, `global_notebooklm_parity`, `p1_opened`, `p1_0_opened`, `mom_specific_assistant`, `mom_only_replacement`):
  - **MOM/WMS Narrow Corpus Block**: Blocks general replacement claims when corpus is limited to `{"mom", "wms", "manufacturing", "manufacturing_mom_wms"}`.
  - **Incomplete Human Review Block**: Blocks replacement/parity claims when review is `pending`, `missing`, `not_done`, or `human_review`.
  - **Deterministic Model Parity Block**: Blocks parity claims when comparing deterministic synthesis against LLM models.
  - **Owner Approval Check**: Blocks `p1_opened` / `p1_0_opened` unless `owner_approved_p1=True`.
  - **Unknown Claim Gate**: Any unregistered claim type is rejected with `Unknown claim type '<type>' is blocked by default.`
  - All tests in `tests/test_claim_guard.py` comprehensively test these guards.

### 1.3 Dynamic Execution of Benchmark & Report Scripts
- `scripts/run_workspace_chat_12_questions.py`:
  - Directly queries `RagV2DevPipeline` and calls `synthesize_evidence(pack)` for all 12 benchmark questions (BQ01–BQ12).
  - Absolutely zero hardcoded lookup tables, zero canned answers, zero mock latencies.
  - Outputs live JSON to `docs/reports/workspace_chat_full_12_questions.json` and Markdown to `docs/reports/workspace_chat_full_12_questions_report.md`.
- `scripts/generate_ai_grounded_report.py`:
  - `load_dynamic_results()` loads execution data from `docs/reports/workspace_chat_full_12_questions.json` or triggers live execution dynamically.
  - The static dictionary `POLISHED_ANSWERS` has been **100% eliminated** from the script.
  - Generates `docs/reports/workspace_chat_full_12_questions_polished_report.md` from actual live data.

---

## 2. Logic Chain

1. **Premise 1 (Dynamic Abstention Integrity)**: The system must refuse to answer out-of-domain, corrupted, or unsupported queries without hallucinating.
   - *Evidence*: `synthesis.py` strictly gates on `pack.answer_mode == EvidenceAnswerMode.ABSTAIN` and validation errors, outputting `"KHÔNG ĐỦ BẰNG CHỨNG:"` with verified limitation reasons. Both out-of-domain questions (BQ11 and BQ12) in the 12-question benchmark produce 0 chunks and correctly return `"KHÔNG ĐỦ BẰNG CHỨNG:"` with `abstained=True` and `grounded=False`.
2. **Premise 2 (ClaimGuard Defense-in-Depth)**: Claims cannot be made without sufficient scope, multi-domain evidence, and owner approval.
   - *Evidence*: `claim_guard.py` implements fail-closed verification across 8 claim types and denies unknown claims by default.
3. **Premise 3 (Zero Hardcoded/Canned Content in Scripts)**: Evaluation and reporting scripts must reflect real retrieval and synthesis outputs.
   - *Evidence*: `POLISHED_ANSWERS` has been completely deleted. `run_workspace_chat_12_questions.py` and `generate_ai_grounded_report.py` execute dynamic pipeline calls and dynamically render actual JSON outputs.

---

## 3. Caveats

- **No Live Provider Cloud Dependency**: The synthesis engine defaults to deterministic local extractive synthesis when no cloud provider is configured, ensuring strict local data privacy and predictability.
- **Strict Coordinate Lookups**: Lookup questions (like BQ09) require explicit coordinate metadata (`sheet`, `row_range`, `cell_range`) in the evidence items; if coordinates are absent, the system fails closed rather than inferring values.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- The dynamic abstention mechanism, ClaimGuard engine, and dynamic evaluation scripts strictly satisfy all R3 requirements and acceptance criteria:
  1. Dynamic abstention cleanly refuses out-of-domain and corrupted queries with `"KHÔNG ĐỦ BẰNG CHỨNG:"`.
  2. ClaimGuard enforces robust fail-closed claim verification.
  3. `POLISHED_ANSWERS` and canned string lookups are completely eliminated from reporting scripts.

---

## 5. Verification Method

To independently verify these findings:
1. Inspect AST / code structure:
   - `src/aios_habit/claim_guard.py:18-80`
   - `src/aios_habit/rag_v2/synthesis.py:1378-1398`
   - `scripts/generate_ai_grounded_report.py:1-144`
   - `scripts/run_workspace_chat_12_questions.py:1-179`
2. Inspect generated report and JSON artifacts:
   - `docs/reports/workspace_chat_full_12_questions.json`
   - `docs/reports/workspace_chat_full_12_questions_polished_report.md`
3. Run test suites:
   - `pytest tests/test_claim_guard.py`
   - `pytest tests/test_rag_v2_synthesis.py`
