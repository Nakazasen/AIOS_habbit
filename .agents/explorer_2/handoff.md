# Handoff Report: MOM Benchmark, Evaluation Gates, and Test Suites Forensic Audit

**Agent**: `explorer_2`  
**Handoff Type**: Hard (Task Complete)  
**Date**: 2026-08-20  
**Target Path**: `d:\Sandbox\AIOS_habbit\.agents\explorer_2\handoff.md`  

---

## 1. Observation

### Observation 1.1: MOM Answer Generation Mechanics
- **File**: `src/aios_habit/mom_benchmark.py`
- **Lines 186–291**: `generate_mom_grounded_answer(question: str, search_results: list[Any], *, max_sources: int = 5) -> dict[str, Any]`
- **Verbatim Code & Comment**:
  ```python
  # Lines 188-192:
  # "The function intentionally avoids cloud/LLM calls. It produces short,
  # evidence-grounded sections and source refs suitable for benchmark scoring,
  # while detailed confidential text remains in ignored runtime records only."
  ```
- **Lines 270–276**:
  ```python
  answer_text = (
      f"Tóm tắt trả lời / Answer summary:\nAIOS tìm thấy {len(source_refs)} nguồn cục bộ liên quan; mức tin cậy={confidence}. {confidence_note}\n\n"
      f"Điều có bằng chứng / Confirmed by source:\n{confirmed_text}\n\n"
      f"Điểm chưa đủ bằng chứng / Not found / insufficient evidence:\n{not_found}\n\n"
      f"Cần kiểm tra tiếp / Next checks:\n- " + "\n- ".join(next_checks) + "\n\n"
      f"Source coverage:\n{len(source_refs)} nguồn; loại file={', '.join(file_types) if file_types else 'none'}; OCR={'yes' if has_ocr else 'no'}; chỉ cục bộ."
  )
  ```
- **Finding**: Retrieval filters keyword terms over local search hits; answer generation is deterministic string templating with zero LLM API/model calls.

### Observation 1.2: MOM Benchmark Records Canned Artifacts
- **File**: `local_cases/mom_pilot/benchmark_records.jsonl`
- **Lines 2–21 (MOM20-01 to MOM20-20)**:
  - Verbatim excerpt from Line 2:
    ```json
    {"question_id": "MOM20-01", "question": "Production history registration process overview", "aios_answer_summary": "AIOS local search returned source refs and a local-only prompt pack; detailed answer kept out of git/report. Evidence available in source refs.", "aios_source_refs": [{"chunk_id": "MOM-00bc6987c411d134-CH000", "relative_path": "仕様書/マテハン/Atlas_Command_Spec_v023 1.xlsm", "source_file": "Atlas_Command_Spec_v023 1.xlsm", "sheet": "Revision History", "section": "sheet Revision History preview", "score": 6.0, "privacy_level": "local_only", "file_type": ".xlsm", "page": "", "slide": "", "extractor_name": "openpyxl", "extraction_status": "extracted_success", "ocr_engine": ""}], "notebooklm_answer_summary": "NotebookLM live query success; answer omitted from committed report for privacy.", "notebooklm_query_status": "success", "comparison_scores": {"source_traceability": 5, "answer_completeness": 4, "hallucination_risk": 5, "actionability": 4, "vietnamese_clarity": 4, "evidence_alignment": 4}, "winner": "Inconclusive", "notes": "M2.2 safe aggregate record; confidential answer text omitted. | NotebookLM là comparator, không phải ground truth; ground truth vẫn là MOM source refs.", "privacy_level": "local_only", "created_at": "2026-06-21T19:13:32.976508", "record_id": "MOM-BENCH-103419D0"}
    ```
  - Every single record in MOM20-01 through MOM20-20 has identical scores `{"source_traceability": 5, "answer_completeness": 4, "hallucination_risk": 5, "actionability": 4, "vietnamese_clarity": 4, "evidence_alignment": 4}` (sum = 26/30, weighted score = 94.0) and identical boilerplate placeholder summaries.
- **Lines 200–247**: 48 repeated identical test dummy records (`"question_id": "Q1"`, `"question": "Quy trình là gì?"`) resulting from test suite executions where `BENCHMARK_RECORDS_FILE` was appended to directly.

### Observation 1.3: MOM Scoring & Comparator Formula
- **File**: `src/aios_habit/mom_benchmark.py`
- **Lines 57–64**:
  ```python
  scores = {
      "source_traceability": _clamp_score(5 if source_count >= 2 else 3 if source_count == 1 else 0),
      "answer_completeness": _clamp_score(3 if aios_answer_summary.strip() else 1 if source_count else 0),
      "hallucination_risk": _clamp_score(5 if source_count and "chưa đủ" in aios_answer_summary.lower() else 4 if source_count else 2),
      "actionability": _clamp_score(4 if "next" in aios_answer_summary.lower() or "kiểm" in aios_answer_summary.lower() else 2 if source_count else 0),
      "vietnamese_clarity": _clamp_score(4 if aios_answer_summary.strip() else 0),
      "evidence_alignment": _clamp_score(5 if source_count else 0),
  }
  ```
- **Lines 70–75**:
  ```python
  notebook_bonus = 0
  if any(token in notebooklm_answer_summary.lower() for token in ("nguồn", "source", "trích", "citation")):
      notebook_bonus += 3
  if any(token in notebooklm_answer_summary.lower() for token in ("không đủ", "chưa đủ", "not enough")):
      notebook_bonus += 2
  notebook_total = 15 + notebook_bonus
  ```
- **Finding**: Scoring is based entirely on string token pattern checks; NotebookLM total score is hardcoded to 15 + heuristic bonus.

### Observation 1.4: Gate Enforcement in `mom_benchmark_gate.py`
- **File**: `src/aios_habit/mom_benchmark_gate.py`
- **Lines 87–99**:
  ```python
  scores = [weighted_maturity_score(record.comparison_scores) for record in records]
  average = round(sum(scores) / len(scores), 2) if scores else 0.0
  target_90_met = average >= 90 and refs == questions_run and critical == 0
  stable = questions_run >= target_questions and notebooklm_success >= expansion_threshold and target_90_met
  reason = "pass" if stable else "benchmark gate not met"
  if refs != questions_run:
      reason = "not all AIOS answers have source refs"
  elif critical:
      reason = "critical hallucination detected"
  elif average < 90:
      reason = "average maturity score below 90"
  elif notebooklm_success < expansion_threshold:
      reason = "NotebookLM success below required threshold"
  ```
- **Finding**: Gate logic enforces real strict branching conditions without hardcoded bypasses (`return True`), but will pass when supplied with pre-stamped passing records.

### Observation 1.5: RAG v2 & Adaptive Reranking Authenticity
- **File**: `src/aios_habit/rag_v2/eval_harness.py:322-650`
  - Calculates dynamic `MRR@10`, `Recall@5`, `Recall@10`, `First Relevant Rank`, `Candidate Recall` across lexical, dense, and fused stages.
- **File**: `scripts/benchmark_adaptive_reranking.py:102-157, 584-650, 740-900`
  - `check_prerequisites` verifies model directories (`local_runs/retrieval_models/bge-m3-5617a9f` and `bge-reranker-v2-m3`), `FlagEmbedding`, and `torch`. If missing, execution halts closed with `overall_status: "BLOCKED"` and `measured: None` across all 13 gates.
  - When ready, executes real cross-encoder reranking over 60 judged test queries against 50 corpus documents (`tests/fixtures/adaptive_routing_cases.json` & `adaptive_reranking_corpus.json`), measuring actual latencies, MRR gain, and recall regression.

### Observation 1.6: Test Suite Mechanics in `tests/`
- **File**: `tests/test_mom_local_pilot.py` (640 lines)
  - Tests parsing, index chunking, query priority, and coverage audits on synthetic files written to `tmp_path`.
  - Gate tests (`test_benchmark_gate_blocks_50_when_score_below_90`, lines 431–450; `test_benchmark_gate_allows_50_when_20q_passes`, lines 452–471) test gate boundary conditions using synthetic `MomBenchmarkRecord` objects.
  - Leak observed in line 119: `save_benchmark_record(record)` writes to live file `BENCHMARK_RECORDS_FILE` instead of `tmp_path`.
- **File**: `tests/test_mom_pdf_ingestion_retrieval.py` (207 lines)
  - Uses `DummyPyMuPDF4LLM` to isolate dependency environments while validating real retrieval ranking algorithms.

---

## 2. Logic Chain

1. **Answer Generation in MOM**:
   - From *Observation 1.1*, `generate_mom_grounded_answer` performs real keyword filtering over chunk previews, but compiles answer text via string interpolation templates without calling an LLM.
   - Therefore, MOM answer generation is `[HYBRID/HEURISTIC]`, not real dynamic LLM generation.

2. **Benchmark Record Authenticity in MOM Pilot**:
   - From *Observation 1.2*, all 20 records (`MOM20-01` to `MOM20-20`) in `local_cases/mom_pilot/benchmark_records.jsonl` share identical comparison score maps (weighted maturity = 94.0) and generic placeholder summary strings.
   - Therefore, the committed 20Q MOM benchmark dataset is `[HARDCODED/MOCKED]`.

3. **Scoring Formulas**:
   - From *Observation 1.3*, `compare_aios_notebooklm` assigns scores based on token substring existence and hardcodes `notebook_total = 15 + bonus`.
   - Therefore, MOM comparison scoring is `[HARDCODED/MOCKED]` & `[HYBRID/HEURISTIC]`.

4. **Gate Integrity**:
   - From *Observation 1.4*, `mom_benchmark_gate.py` has no unconditional bypass flags or constants (`return True`), but when supplied with the pre-computed 20Q records (which were stamped with maturity 94.0 and status "success"), it outputs `target_90_met=True, attempted_50=True`.
   - Therefore, the gate logic is `[HYBRID/HEURISTIC]` (valid rules evaluated over heuristic input scores).

5. **RAG v2 & Adaptive Benchmark Rigor**:
   - From *Observation 1.5*, `eval_harness.py` and `benchmark_adaptive_reranking.py` calculate true statistical information retrieval metrics (MRR, Recall@k, P95, RAM RSS) from actual model executions and fail closed when prerequisites are missing.
   - Therefore, RAG v2 and Adaptive Reranking benchmarks are `[GENUINE]`.

6. **Test Suite Integrity**:
   - From *Observation 1.6*, tests in `tests/` execute real functional code against synthetic fixtures. Mocks are used appropriately for external network, missing dependencies, or fault-injection testing.
   - Therefore, the test suite is `[GENUINE]`.

---

## 3. Caveats

- **No Caveats on Code Structure**: All relevant benchmark, gate, script, and test files were inspected with line-numbered code evidence.
- **Assumptions**: The 20 records in `benchmark_records.jsonl` were intentionally scrubbed of confidential client data (per comments "M2.2 safe aggregate record; confidential answer text omitted"), which accounts for the placeholder text; however, the scores themselves are identical across all 20 questions.

---

## 4. Conclusion

1. **MOM Benchmark (`mom_benchmark.py`, `mom_benchmark_gate.py`, `benchmark_records.jsonl`)**:
   - **Generation**: `[HYBRID/HEURISTIC]` (deterministic template over keyword-filtered chunk previews, no LLM).
   - **Scoring**: `[HARDCODED/MOCKED]` & `[HYBRID/HEURISTIC]` (substring heuristics, hardcoded NotebookLM base score of 15).
   - **Records**: `[HARDCODED/MOCKED]` (20 identical score entries, maturity 94.0).
   - **Gate**: `[HYBRID/HEURISTIC]` (real condition checks, no backdoor bypasses).

2. **RAG v1 & v2 Evaluation Suites (`rag_benchmark.py`, `eval_harness.py`, `battle_notebooklm_rag_v2.py`)**:
   - **Retrieval & Scoring**: `[GENUINE]` (real SQLite index search, dynamic MRR, Recall@5/10, latency percentiles, fail-fast circuit breakers).
   - **LLM Parity**: Explicitly scoped as retrieval-only in v1; multi-arm provider evaluation with failure isolation in v2.

3. **Adaptive Reranking & OCR Benchmarks (`benchmark_adaptive_reranking.py`, `benchmark_ocr_engines.py`)**:
   - `[GENUINE]` (authentic local model inference, fail-closed gate prevents number fabrication).

4. **Test Suites (`tests/`)**:
   - `[GENUINE]` (authentic assertions verifying core indexing, parsing, privacy, and gate logic on synthetic fixtures).

---

## 5. Verification Method

To independently verify all claims:

1. **Verify MOM Benchmark Answer Templating & Heuristic Scoring**:
   ```powershell
   pytest tests/test_mom_local_pilot.py -k "test_generate_mom_grounded_answer or test_real_answer_scoring or test_benchmark_scores" -v
   ```
2. **Verify MOM Gate Boundary Logic (90 threshold)**:
   ```powershell
   pytest tests/test_mom_local_pilot.py -k "test_benchmark_gate_blocks_50 or test_benchmark_gate_allows_50" -v
   ```
3. **Verify RAG Benchmark Metric Calculation**:
   ```powershell
   pytest tests/test_rag_benchmark.py -v
   pytest tests/test_rag_v2_eval_harness.py -v
   ```
4. **Verify Adaptive Reranking Fail-Closed Prerequisite Gate**:
   ```powershell
   python scripts/benchmark_adaptive_reranking.py --fixture tests/fixtures/adaptive_routing_cases.json
   ```
   (Inspect output JSON to verify `overall_status: "BLOCKED"` and `measured: None` if models are not staged).
5. **Inspect Canned Records**:
   ```powershell
   Get-Content local_cases/mom_pilot/benchmark_records.jsonl -TotalCount 5
   ```
