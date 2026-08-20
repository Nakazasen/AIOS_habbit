# Independent Review & Adversarial Challenge Report (Reviewer 2: R3 & R4)

## Review Summary

**Verdict**: **APPROVE**
**Overall Risk Assessment**: **LOW**
**Scope**: Requirement R3 (Dynamic Abstention & Zero Canned Answers) and Requirement R4 (Comprehensive Tests & Regression Guards).

---

## 1. Observation

### Obs 1: Elimination of `POLISHED_ANSWERS` & Dynamic Report Generation
- In `scripts/generate_ai_grounded_report.py`:
  - `POLISHED_ANSWERS` dictionary is completely removed (0 occurrences in AST or source text).
  - Lines 18–38: `load_dynamic_results()` loads dynamically from live JSON results (`docs/reports/workspace_chat_full_12_questions.json`) or triggers live execution via `from scripts.run_workspace_chat_12_questions import main as run_benchmark`.
  - Lines 40–133: `format_grounded_report()` formats Markdown tables and per-question sections directly from dynamic runtime fields (`answer`, `cited_sources`, `latency`, `t_ret`, `t_syn`, `chunks_count`, `abstained`, `grounded`).

### Obs 2: Dynamic Execution & Grounded Synthesis in 12-Question Benchmark
- In `scripts/run_workspace_chat_12_questions.py`:
  - Lines 83–133: Iterates through `QUESTIONS`, executes live BGE-M3 hybrid retrieval via `pipeline.query(question_text, sources, expansion=...)`, and performs dynamic synthesis via `synth_res = synthesize_evidence(pack)` from `src/aios_habit/rag_v2/synthesis.py`.
  - Zero hardcoded responses or answer dictionaries exist in the benchmark runner.
  - Dynamic abstention is verified for unanswerable questions (BQ11 "quantum computing", BQ12 "blockchain QA"), where retrieval yields zero citable factory evidence and triggers fail-closed refusal.

### Obs 3: Dynamic Abstention Format in Synthesis Engine & Claim Readiness
- In `src/aios_habit/rag_v2/synthesis.py`:
  - Lines 1378–1398: `_abstention(pack, reasons)` constructs a fail-closed, standardized Vietnamese refusal:
    ```python
    answer = "\n".join((
        "KHÔNG ĐỦ BẰNG CHỨNG:",
        "- Corpus được truy xuất không thiết lập được sự kiện hoặc quan hệ mà câu hỏi yêu cầu.",
        "- Cần nguồn trực tiếp (ví dụ: tài liệu quy trình, bản ghi hệ thống hoặc hàng dữ liệu có mục tiêu) trước khi có thể trả lời an toàn.",
        f"LIMITATIONS: {reason_text}",
    ))
    ```
  - Returns `LocalSynthesisResult` with `grounded=False`, `abstained=True`, `claims=()`, `citation_ids=()`.
- In `src/aios_habit/claim_guard.py`:
  - Lines 18–81: `evaluate_claim_readiness()` rigorously gates scope, corpus domain coverage, answer quality, deterministic vs model synthesis, and explicit human/owner approvals.

### Obs 4: AST-Based Regression Guards in `tests/test_mom_search_bm25_zero_hardcode.py`
- `test_ast_mom_local_index_zero_hardcoded_terms` (lines 48–63): Verifies 0 occurrences of `q1_terms`, `q2_terms`, `q3_terms`, `q1`, `q2`, `q3` across `ast.Name`, `ast.Attribute`, and string constants.
- `test_ast_mom_local_index_zero_file_penalties` (lines 64–75): Verifies 0 occurrences of penalty constants `-50.0` / `-50` and string constant `"erd_kho_van_new.html"`.
- `test_ast_excel_extractors_default_limits_none` (lines 129–164): Verifies `ExcelExtractionConfig` defaults have `max_rows_per_sheet=None`, `max_non_empty_cells=None`, `enable_row_chunking=True`, `chunk_row_size=500`.
- `test_ast_scripts_zero_polished_answers` (lines 181–198): Verifies `POLISHED_ANSWERS` is 0 in AST names and strings of both `generate_ai_grounded_report.py` and `run_workspace_chat_12_questions.py`.
- Functional tests (lines 76–124, 165–176, 200–214): Verify BM25 multilingual search, Excel default instantiation, and ClaimGuard dynamic abstention.

---

## 2. Logic Chain

1. **R3 Verification (Zero Canned Answers & Dynamic Abstention)**:
   - From Obs 1 and Obs 2, both `scripts/generate_ai_grounded_report.py` and `scripts/run_workspace_chat_12_questions.py` have completely eliminated `POLISHED_ANSWERS` and static mock answers.
   - Live query responses flow through `pipeline.query()` -> `EvidencePack` -> `synthesize_evidence(pack)` -> `LocalSynthesisResult`.
   - When evidence is insufficient (e.g. BQ11 and BQ12), `_abstention()` handles it dynamically without fallback leaks or static mocks.
   - Macro governance is safely gated by `ClaimGuard.evaluate_claim_readiness()`.

2. **R4 Verification (AST Regression Guards & Test Architecture)**:
   - From Obs 4, `tests/test_mom_search_bm25_zero_hardcode.py` inspects the AST of target modules directly at syntax level, preventing accidental reintroduction of heuristics, target document penalties, or canned answers.
   - From Obs 3 and existing tests in `tests/test_claim_guard.py`, `tests/test_rag_v2_synthesis.py`, and `tests/test_document_extractors.py`, unit and integration tests thoroughly validate streaming chunking, BM25 objective ranking, and fail-closed dynamic abstention.

3. **Integrity Violation Analysis**:
   - Zero hardcoded test outputs or fake answers embedded in source modules.
   - Zero facade/dummy implementations; all BM25, Excel streaming chunking, and grounded synthesis functions contain full production logic.
   - Zero shortcuts or external bypasses.
   - **Conclusion**: Integrity verification passes with zero violations.

---

## 3. Adversarial Challenges & Stress Testing

### Challenge 1: Dynamic Abstention Leaks & Prompt Conformance
- **Assumption**: Does dynamic abstention ever invent citations or provide partial speculative answers on unanswerable questions?
- **Stress-Test**: Evaluated `_abstention()` in `rag_v2/synthesis.py:1378-1398`. When `abstained=True`, `citation_ids=()`, `claims=()`, and `grounded=False`. Output contains explicit `LIMITATIONS: <reasons>` and no ungrounded claims.
- **Result**: PASS.

### Challenge 2: AST Guard Robustness Against Obfuscation
- **Assumption**: Could hardcoding be reintroduced using alternate AST representations?
- **Stress-Test**: Examined AST helper `_find_all_names_and_strings` in `test_mom_search_bm25_zero_hardcode.py`. It traverses `ast.Name`, `ast.Attribute`, `ast.Constant` (strings, ints, floats), and `ast.UnaryOp` (negative numbers).
- **Result**: PASS.

---

## 4. Verified Claims

- `POLISHED_ANSWERS` eliminated from `scripts/` → Verified via AST inspection & global regex search → **PASS**
- Dynamic synthesis in `scripts/run_workspace_chat_12_questions.py` → Verified via code trace & `synthesize_evidence` contract → **PASS**
- Dynamic refusal format `"KHÔNG ĐỦ BẰNG CHỨNG:"` in `synthesis.py` → Verified via line 1383 → **PASS**
- AST regression guards for keywords, penalties, defaults, and canned dicts → Verified via `tests/test_mom_search_bm25_zero_hardcode.py` → **PASS**
- Excel streaming chunking without 1,000-row limits → Verified via `tests/test_document_extractors.py` and `excel_extractors.py` → **PASS**

---

## 5. Caveats

- Benchmark evaluation script `scripts/run_workspace_chat_12_questions.py` requires pre-built indexed databases (`local_runs/battle_workspace_stage_cache/...`) when running against the full 69-file staging dataset.
- No other caveats.

---

## 6. Conclusion & Verdict

**Final Verdict**: **APPROVE**

Requirements R3 and R4 are completely implemented with high code quality, zero hardcoded shortcuts, verified fail-closed dynamic abstention, and robust AST regression guards.

---

## 7. Verification Method

To independently re-verify:
```bash
# 1. Run zero-hardcode AST regression suite
pytest tests/test_mom_search_bm25_zero_hardcode.py

# 2. Run ClaimGuard governance test suite
pytest tests/test_claim_guard.py

# 3. Run Grounded Synthesis & Dynamic Abstention test suite
pytest tests/test_rag_v2_synthesis.py

# 4. Run Excel Streaming Extractor test suite
pytest tests/test_document_extractors.py

# 5. Verify zero occurrences of POLISHED_ANSWERS in source files
python -c "import ast; tree = ast.parse(open('scripts/generate_ai_grounded_report.py').read()); assert 'POLISHED_ANSWERS' not in [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]"
```
