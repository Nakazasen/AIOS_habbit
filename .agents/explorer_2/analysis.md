# Forensic Investigation Report: MOM Benchmark, Evaluation Gates, and Test Suites

**Author**: `explorer_2`  
**Date**: 2026-08-20  
**Workspace**: `d:\Sandbox\AIOS_habbit`  
**Scope**: Forensic audit of MOM benchmark scripts, evaluation gates, test suites, and ground-truth configurations.

---

## Executive Summary

This forensic investigation analyzed the authenticity, rigor, scoring mechanics, and test validity across:
1. **MOM Pilot Benchmark & Gates**: `src/aios_habit/mom_benchmark.py`, `src/aios_habit/mom_benchmark_gate.py`, `local_cases/mom_pilot/`
2. **RAG v1 Benchmark**: `src/aios_habit/rag_benchmark.py`
3. **RAG v2 Evaluation & Battle Harness**: `src/aios_habit/rag_v2/eval_harness.py`, `scripts/battle_notebooklm_rag_v2.py`, `src/aios_habit/benchmark_reference_acquisition.py`, `src/aios_habit/benchmark_reference_registry.py`
4. **Adaptive Reranking & OCR Benchmarks**: `scripts/benchmark_adaptive_reranking.py`, `scripts/benchmark_ocr_engines.py`
5. **Test Suites & Fixtures**: `tests/test_mom_local_pilot.py`, `tests/test_mom_pdf_ingestion_retrieval.py`, `tests/test_rag_benchmark.py`, `tests/test_battle_notebooklm_rag_v2.py`, `tests/test_rag_v2_eval_harness.py`

### Key Findings & Verdict Matrix

| Component | Target File(s) | Classification | Authenticity & Rigor Assessment |
|---|---|---|---|
| **MOM Answer Generation** | `src/aios_habit/mom_benchmark.py:186-291` | `[HYBRID/HEURISTIC]` | Real local keyword/term search filter over chunk previews; deterministic string templating for answers; no LLM inference used. |
| **MOM Pre-computed Records** | `local_cases/mom_pilot/benchmark_records.jsonl:1-247` | `[HARDCODED/MOCKED]` | Lines 2-21 contain 20 identical canned scoring dicts (sum=26/30, maturity=94.0) with placeholder text ("confidential answer text omitted"). Lines 200-247 are side-effect test pollution. |
| **MOM Scoring Functions** | `src/aios_habit/mom_benchmark.py:47-84, 293-338` | `[HARDCODED/MOCKED]` & `[HYBRID/HEURISTIC]` | NotebookLM score is hardcoded to `15 + bonus` (`mom_benchmark.py:75`); AIOS scores use string token pattern matching ("confirmed by source", "next checks", text length > 120). |
| **MOM Evaluation Gate** | `src/aios_habit/mom_benchmark_gate.py:81-110` | `[HYBRID/HEURISTIC]` | Gate logic is strictly conditional (checks >= 90 average, ref count, zero critical hallucinations, NotebookLM threshold). No hardcoded `return True`, but passes when fed canned records. |
| **RAG v1 Benchmark** | `src/aios_habit/rag_benchmark.py:88-208` | `[GENUINE]` (Retrieval) / `[STUB]` (LLM) | In-memory SQLite search; real dynamic calculation of Top Chunk Hit Rate, Document Hit Rate, Citation Hit Rate, Latency. Explicitly disclaims LLM parity. |
| **RAG v2 Evaluation Harness** | `src/aios_habit/rag_v2/eval_harness.py:322-650` | `[GENUINE]` | Highly rigorous; dynamic calculation of MRR@10, Recall@5, Recall@10, First Relevant Rank, Exact Identifier Recall, Grounded Answer Rate, Citation Validity, False Support, and Latency breakdown. |
| **Adaptive Reranking Benchmark** | `scripts/benchmark_adaptive_reranking.py:569-1050` | `[GENUINE]` | Real local BGE-M3 and BGE-Reranker model inference; evaluates 60 judged test queries against 50 corpus documents; fail-closed gate blocks synthetic number fabrication. |
| **OCR Engines Benchmark** | `scripts/benchmark_ocr_engines.py:38-87` | `[GENUINE]` | Real Sequential RapidOCR/PaddleOCR execution on image files; measures dynamic latency and confidence. |
| **Test Suites** | `tests/` | `[GENUINE]` | Tests validate real parsing, indexing, search, gate conditions, and privacy invariants on synthetic fixtures. Mocking is restricted to external network/LLM dependencies and simulated failure recovery. |

---

## Forensic Question 1: Benchmark Queries & Answer Generation Mechanics

### MOM Pilot Benchmark (`src/aios_habit/mom_benchmark.py`)
- **Query Formulation**: In `local_cases/mom_pilot/benchmark_questions.json:1-27`, there are only 5 static questions (`MOM-Q01` to `MOM-Q05`).
- **Answer Generation**: `generate_mom_grounded_answer(question, search_results, max_sources=5)` (lines 186–291) executes the following:
  1. Filters search hits using question-specific extracted keywords (`_question_specific_terms`, lines 177–183) or unsupported topic blocklists (`_UNSUPPORTED_STRICT_TERMS`, lines 170–174).
  2. Compiles matching chunk references (`source_refs`, lines 214–240) extracting `chunk_id`, `relative_path`, `sheet`, `page`, `slide`, `preview`.
  3. Constructs a deterministic string template with 5 structured sections:
     - `Tóm tắt trả lời / Answer summary`
     - `Điều có bằng chứng / Confirmed by source`
     - `Điểm chưa đủ bằng chứng / Not found / insufficient evidence`
     - `Cần kiểm tra tiếp / Next checks`
     - `Source coverage`
  4. Lines 188–192 explicitly document:
     ```python
     # Line 188-192:
     # "The function intentionally avoids cloud/LLM calls. It produces short,
     # evidence-grounded sections and source refs suitable for benchmark scoring,
     # while detailed confidential text remains in ignored runtime records only."
     ```
  5. The output dictionary sets `"prompt_only": False` and `"privacy_level": "local_only"` (lines 288–289).

### Pre-computed Benchmark Artifacts (`local_cases/mom_pilot/benchmark_records.jsonl`)
- **Lines 2–21 (MOM20-01 to MOM20-20)**:
  - Every single record contains identical placeholder answers:
    ```json
    "aios_answer_summary": "AIOS local search returned source refs and a local-only prompt pack; detailed answer kept out of git/report. Evidence available in source refs."
    "notebooklm_answer_summary": "NotebookLM live query success; answer omitted from committed report for privacy."
    "notebooklm_query_status": "success"
    "comparison_scores": {"source_traceability": 5, "answer_completeness": 4, "hallucination_risk": 5, "actionability": 4, "vietnamese_clarity": 4, "evidence_alignment": 4}
    "winner": "Inconclusive"
    ```
  - These 20 records were generated offline and committed as static aggregates.
- **Lines 200–247**:
  - Repeated dummy records generated as a side effect when running `pytest tests/test_mom_local_pilot.py` (specifically `test_benchmark_record_manual_required_not_fake_success`, lines 110–120), because `save_benchmark_record` writes directly to `BENCHMARK_RECORDS_FILE` without monkeypatching `MOM_RUNTIME_DIR`.

### RAG v2 & Adaptive Reranking Generation
- In `src/aios_habit/rag_v2/eval_harness.py:322-440` and `src/aios_habit/rag_v2/synthesis.py`:
  - Retrieval executes over real SQLite chunk tables (`LocalChunkIndex`).
  - Evidence packs are assembled dynamically (`build_evidence_pack`).
  - Local rule-based synthesis (`synthesize_evidence`) generates structured claims and citations from retrieved snippets.
- In `scripts/benchmark_adaptive_reranking.py:740-833`:
  - 60 test queries from `tests/fixtures/adaptive_routing_cases.json` are evaluated against `tests/fixtures/adaptive_reranking_corpus.json`.
  - Runs actual `RagV2DevPipeline` with real BGE-M3 dense embeddings and BGE-Reranker model inference.

---

## Forensic Question 2: Calculation of Evaluation Scores & Metrics

### MOM Benchmark Scoring (`src/aios_habit/mom_benchmark.py` & `src/aios_habit/mom_benchmark_gate.py`)
1. **`compare_aios_notebooklm` (`mom_benchmark.py:47-84`)**:
   - `source_traceability`: 5 if >= 2 refs, 3 if 1 ref, 0 if 0 refs (line 58).
   - `answer_completeness`: 3 if answer present, 1 if refs present, 0 otherwise (line 59).
   - `hallucination_risk`: 5 if "chưa đủ" in answer and refs present; 4 if refs present; 2 otherwise (line 60).
   - `actionability`: 4 if "next" or "kiểm" in answer; 2 if refs present; 0 otherwise (line 61).
   - `vietnamese_clarity`: 4 if answer present; 0 otherwise (line 62).
   - `evidence_alignment`: 5 if refs present; 0 otherwise (line 63).
   - **NotebookLM comparator score**:
     ```python
     # Lines 70-75:
     notebook_bonus = 0
     if any(token in notebooklm_answer_summary.lower() for token in ("nguồn", "source", "trích", "citation")):
         notebook_bonus += 3
     if any(token in notebooklm_answer_summary.lower() for token in ("không đủ", "chưa đủ", "not enough")):
         notebook_bonus += 2
     notebook_total = 15 + notebook_bonus
     ```
     `notebook_total` is hardcoded to base 15 + heuristic bonus (max 20).
2. **`score_mom_real_answer` (`mom_benchmark.py:293-326`)**:
   - Evaluates string patterns across 7 dimensions (source_traceability, evidence_alignment, completeness, unknown_handling, actionability, clarity, hallucination_control).
   - Checks presence of exact header substrings: `"confirmed by source"`, `"not found"`, `"next checks"`, `"source coverage"` (line 298).
3. **`weighted_maturity_score` (`mom_benchmark_gate.py:22-31`) & `weighted_real_answer_score` (`mom_benchmark.py:328-338`)**:
   - Computes weighted linear sum on 0–100 scale:
     - Evidence alignment: 30% (or 25%)
     - Source traceability: 20%
     - Answer completeness: 20%
     - Hallucination control / risk: 10%
     - Actionability: 10%
     - Vietnamese clarity: 10% (or 5%)
     - Unknown handling: 10%

### RAG v1 Benchmark Metrics (`src/aios_habit/rag_benchmark.py:126-179`)
Metrics are dynamically computed per execution:
- `top_chunk_hit_rate = sum(r.hit_expected_chunk) / ans_count` (line 134)
- `document_hit_rate = sum(r.hit_expected_document) / ans_count` (line 135)
- `citation_hit_rate = sum(r.hit_expected_citation) / ans_count` (line 136)
- `insufficient_detection_rate = sum(r.insufficient_evidence) / ins_count` (line 138)
- `privacy_pass_rate = sum(r.privacy_ok) / q_count` (line 139)
- `average_latency_ms = sum(r.latency_ms) / q_count` (line 140)

### RAG v2 & Adaptive Reranking Metrics (`src/aios_habit/rag_v2/eval_harness.py` & `scripts/benchmark_adaptive_reranking.py`)
Metrics are computed dynamically from actual execution:
- **MRR (Mean Reciprocal Rank)**:
  `reciprocal_rank = 1.0 / final_first_rank if 0 < final_first_rank <= 10 else 0.0` (`eval_harness.py:353`, `benchmark_adaptive_reranking.py:805-819`)
- **Recall@5 and Recall@10**:
  `recall_at_5 = 0 < final_first_rank <= 5`, `recall_at_10 = 0 < final_first_rank <= 10` (`eval_harness.py:464-465`)
- **Hard MRR Gain**:
  `measured_hard_mrr_gain = round(mean_mrr_rerank_hard - mean_mrr_hybrid_hard, 4)` (`benchmark_adaptive_reranking.py:852`)
- **Recall Regression**:
  `measured_recall_regression = round(max(0.0, mean_recall_hybrid - mean_recall_rerank), 4)` (`benchmark_adaptive_reranking.py:856`)
- **Latency Percentiles**:
  Calculated via `_percentile(latencies, 0.50)` and `_percentile(latencies, 0.95)` using real wall-clock timings (`benchmark_adaptive_reranking.py:858-861`, `scripts/benchmark_workspace_chat_rag_v2.py:226`).

---

## Forensic Question 3: Gate Enforcement & Bypass Analysis

### `src/aios_habit/mom_benchmark_gate.py` (`evaluate_benchmark_gate`)
- **Gate Logic Inspection (lines 81–110)**:
  ```python
  # Line 87-90:
  scores = [weighted_maturity_score(record.comparison_scores) for record in records]
  average = round(sum(scores) / len(scores), 2) if scores else 0.0
  target_90_met = average >= 90 and refs == questions_run and critical == 0
  stable = questions_run >= target_questions and notebooklm_success >= expansion_threshold and target_90_met
  reason = "pass" if stable else "benchmark gate not met"
  ```
- **Failure Branches (lines 92–99)**:
  - If `refs != questions_run`: `reason = "not all AIOS answers have source refs"`
  - If `critical > 0`: `reason = "critical hallucination detected"`
  - If `average < 90`: `reason = "average maturity score below 90"`
  - If `notebooklm_success < expansion_threshold`: `reason = "NotebookLM success below required threshold"`
- **Bypass Analysis**:
  - There are **NO backdoors, bypass flags, or hardcoded pass constants** in `evaluate_benchmark_gate`.
  - However, because the 20 pre-generated records in `benchmark_records.jsonl` were stored with identical scores yielding `average = 94.0` and `notebooklm_query_status = "success"`, passing those records to `evaluate_benchmark_gate(records, target_questions=20, expansion_threshold=18)` evaluates directly to `attempted_50=True` and `reason="pass"`.

### Fail-Closed Gates in Other Modules
- **`scripts/battle_notebooklm_rag_v2.py` (`assess_fail_fast`, lines 144–228)**:
  - Evaluates live execution rows. If an infrastructure error occurs, consecutive errors >= 2, unusable answer rate >= 80%, or false support on an insufficient question is detected, it immediately returns `should_stop: True`.
- **`scripts/benchmark_adaptive_reranking.py` (`check_prerequisites`, lines 102–157)**:
  - Validates existence of model weights (BGE-M3, BGE-Reranker), Python dependencies (`FlagEmbedding`, `torch`), manifest, and judged dataset. If any item is missing, it sets `overall_status = "BLOCKED"` and writes `measured: None` for all 13 gates. It never fabricates synthetic scores.

---

## Forensic Question 4: Test Suites Verification in `tests/`

Investigation of 118 test files in `tests/` revealed that tests primarily test **real functional pipelines and logic against synthetic local fixtures**:

1. **`tests/test_mom_local_pilot.py` (640 lines)**:
   - Tests file parsers (`_extract_pdf`, `pptx_zip_xml`, `openpyxl`), indexing (`build_mom_local_index`), query search (`search_mom_index`), and coverage audits (`summarize_mom_coverage`).
   - Uses real file system fixtures created in `tmp_path` (e.g. `test_mom_local_index_chunks_and_search_synthetic_text`, lines 27–47; `test_strict_corpus_audit_accepts_only_valid_owner_exclusion`, lines 400–428).
   - Gate tests (`test_benchmark_gate_blocks_50_when_score_below_90`, `test_benchmark_gate_allows_50_when_20q_passes`, lines 431–471) construct synthetic `MomBenchmarkRecord` objects to verify that gate boundaries trigger correctly.
2. **`tests/test_mom_pdf_ingestion_retrieval.py` (207 lines)**:
   - Uses a dummy mock class `DummyPyMuPDF4LLM` to simulate PDF extraction when `pymupdf4llm` is not installed or when testing dependency missing fallback (`test_pdf_extraction_fail_soft`, lines 33–46).
   - Verifies search scoring, query priority, and domain boosting on synthetic `MomChunk` objects (`test_retrieval_q1_mes_mom_boosting`, `test_retrieval_q2_production_history_anti_erd`, lines 74–164).
3. **`tests/test_rag_benchmark.py` (316 lines)**:
   - Constructs synthetic `RAGChunk` and `RAGBenchmarkQuestion` instances (`_mock_chunks`, `_mock_questions`, lines 9–143).
   - Validates in-memory SQLite schema creation, BM25 keyword search, result scoring, privacy enforcement, and metric aggregation.
4. **`tests/test_rag_v2_eval_harness.py` (457 lines)**:
   - Builds real in-memory `LocalChunkIndex` from `DocumentChunk` fixtures.
   - Asserts exact ranking logic, reciprocal rank calculations, false support detection, and error classification (`CANDIDATE_RECALL_MISS`, `FALSE_INSUFFICIENCY`, `CITATION_MISS`).
5. **`tests/test_battle_notebooklm_rag_v2.py` (258 lines)**:
   - Specifically tests crash recovery, resumption, and checkpoint persistence by monkeypatching `prepare_workspace_chat_sources` to simulate intermittent failures (`test_workspace_stage_resumes_exact_checkpoint_without_repreparing_commits`, lines 62–110).

---

## Detailed Classification Summary

| Component | Code Location | Classification | Evidence & Rationale |
|---|---|---|---|
| MOM Grounded Answer Generator | `src/aios_habit/mom_benchmark.py:186-291` | `[HYBRID/HEURISTIC]` | Deterministic template using real local chunk preview hits and keyword matching; no LLM inference. |
| MOM Comparator Scoring | `src/aios_habit/mom_benchmark.py:47-84` | `[HARDCODED/MOCKED]` | NotebookLM score is hardcoded to `15 + bonus` (`line 75`); AIOS scores use string token presence. |
| MOM 20Q Benchmark Records | `local_cases/mom_pilot/benchmark_records.jsonl:1-21` | `[HARDCODED/MOCKED]` | Pre-computed static records with identical canned scores (maturity=94.0) and redacted boilerplate summaries. |
| MOM Benchmark Gate | `src/aios_habit/mom_benchmark_gate.py:81-110` | `[HYBRID/HEURISTIC]` | Genuine condition checks (average >= 90, 100% refs, 0 critical), but operates on heuristic score inputs. |
| RAG v1 Benchmark Runner | `src/aios_habit/rag_benchmark.py:181-208` | `[GENUINE]` (Retrieval) / `[STUB]` (LLM) | Real SQLite BM25 search and metric calculations; LLM comparison is explicitly out of scope. |
| RAG v2 Evaluation Harness | `src/aios_habit/rag_v2/eval_harness.py:1-913` | `[GENUINE]` | Real multi-stage ranking, reciprocal rank, recall, false support, and latency metric calculations. |
| Adaptive Reranking Benchmark | `scripts/benchmark_adaptive_reranking.py:1-1158` | `[GENUINE]` | Authentic local BGE-M3 + BGE-Reranker model inference; fail-closed gates with zero fabricated numbers. |
| OCR Engines Benchmark | `scripts/benchmark_ocr_engines.py:1-93` | `[GENUINE]` | Authentic local OCR execution and statistical latency/confidence aggregation. |
| Test Suites (`tests/`) | `tests/test_*.py` | `[GENUINE]` | Real assertion of functionality against synthetic fixtures; mocks are confined to unit boundary isolation. |
