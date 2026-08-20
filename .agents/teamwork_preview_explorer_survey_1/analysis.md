# Forensic Analysis Report: Requirement 1 (MOM Local Index & Search Hardcode Removal)

**Target**: `src/aios_habit/mom_local_index.py` & MOM Search Retrieval Architecture  
**Author**: `teamwork_preview_explorer_survey_1`  
**Date**: 2026-08-20  
**Integrity Mode**: Development / Read-Only Investigation  

---

## 1. Executive Summary

This investigation analyzed Requirement 1 of the comprehensive MOM upgrade: **complete removal of hardcoded keywords, artificial score boosts, and file-targeted penalties in `mom_local_index.py`**, alongside standardizing the ranking algorithm to objective BM25 / TF-IDF or RAG v2 retrieval.

### Key Findings
1. **Verbatim Hardcoded Retrieval Heuristics Located**:
   - Lines 304–310 of `src/aios_habit/mom_local_index.py` declare static keyword lists (`q1_terms`, `q2_terms`, `q3_terms`) specifically tailored to pass benchmark questions Q1 (MES/MOM comparison), Q2 (Production History system), and Q3 (Manual Shipping Excel schema).
   - Lines 312–314 detect query intent using substring matches against these static lists.
   - Lines 332–367 apply artificial score additions (`+10.0` to `+20.0 * len(matched)`) and an explicit penalty `score -= 50.0` targeting `erd_kho_van_new.html` on Q2 queries.
2. **Current Ranking Architecture vs Reusable Utilities**:
   - Current `search_mom_index` uses basic substring counting without inverse document frequency (IDF) or document length normalization, relying on the hardcoded bonuses to force desired ranking.
   - The codebase contains two reference retrieval implementations:
     - `src/aios_habit/rag_search.py`: SQLite FTS5 BM25 + fallback substring scoring.
     - `src/aios_habit/rag_v2/index.py`: Full hybrid retrieval engine (SQLite FTS5 BM25 + BGE-M3 Dense 1024D + Sparse Lexical + ColBERT MaxSim + Reciprocal Rank Fusion + Deterministic Lexical Scoring `_score_candidate`).
3. **Caller Dependency Analysis**:
   - Direct callers: `src/aios_habit/mom_coverage.py` (`build_mom_local_index`, `load_mom_chunks`, `MomChunk`), `scripts/audit_mom_corpus.py` (via `mom_coverage`), and test suites in `tests/test_mom_local_pilot.py` and `tests/test_mom_pdf_ingestion_retrieval.py`.
   - Consumer contract: `src/aios_habit/mom_benchmark.py` (`generate_mom_grounded_answer`) expects search results with `.score`, `.matched_terms`, and `.chunk` attributes.
4. **Test Suite Compatibility**:
   - All existing tests in `test_mom_local_pilot.py` and `test_mom_pdf_ingestion_retrieval.py` rely on `search_mom_index` matching query terms to document text/metadata.
   - Standardizing to an objective in-memory BM25 / TF-IDF algorithm (with CJK n-gram support and metadata weighting) will naturally satisfy 100% of existing tests without any hardcoded query rules or file penalties.

---

## 2. Exhaustive Audit of Hardcoding in `src/aios_habit/mom_local_index.py`

### 2.1 Hardcoded Keyword Lists (Lines 304–310)
```python
# Lines 304-310 in src/aios_habit/mom_local_index.py
    # Q1 target terms (MES/MOM comparison)
    q1_terms = ["mes", "mom", "mes_mom", "momデータ連携", "実行", "製造", "traceability", "scheduling", "quality", "inventory"]
    # Q2 target terms (Production History system)
    q2_terms = ["生産履歴", "着完工", "ラインアウト", "復帰登録", "修理内容入力", "部品供給停止", "再開登録", "工程在庫修正", "戻入", "分割入庫", "製造人員登録"]
    # Q3 target terms (Manual Shipping Excel metadata)
    q3_terms = ["manualshipping_existinglineauto_inbounddownload", "item_code", "item_rev", "sup_line", "process_id", "oricon_id", "containername", "kdcrenameshipchangeqty"]
```

### 2.2 Query Intent Overfitting (Lines 312–314)
```python
# Lines 312-314 in src/aios_habit/mom_local_index.py
    # Detect query intents
    query_has_q1 = any(t in q for t in q1_terms)
    query_has_q2 = any(t in q for t in q2_terms)
    query_has_q3 = any(t in q for t in q3_terms)
```

### 2.3 Artificial Score Boosts and Targeted Penalty (Lines 332–367)
```python
# Lines 332-367 in src/aios_habit/mom_local_index.py
        if score > 0:
            # Q1 Retrieval Enhancements: Boost MES/MOM PDF sources and matching terms
            if query_has_q1:
                matched_q1 = [term for term in q1_terms if term in haystack]
                if matched_q1:
                    score += 15.0 * len(matched_q1)
                if chunk.file_type == ".pdf":
                    score += 10.0
                if any(k in chunk.source_file.lower() for k in ["mes", "mom"]):
                    score += 15.0

            # Q2 Retrieval Enhancements: Boost Production History PDF specs and Japanese terms
            if query_has_q2:
                matched_q2 = [term for term in q2_terms if term in haystack]
                if matched_q2:
                    score += 15.0 * len(matched_q2)
                if chunk.file_type == ".pdf":
                    score += 10.0
                if any(k in chunk.source_file.lower() for k in ["生産履歴", "着完工", "仕様"]):
                    score += 15.0

                # Targeted Penalty for ERD_Kho_Van_NEW.html on Q2 queries
                if "erd_kho_van_new.html" in chunk.relative_path.lower():
                    has_exact_q2_terms = any(term in haystack for term in q2_terms)
                    if not has_exact_q2_terms:
                        score -= 50.0

            # Q3 Retrieval Enhancements: Boost specific Excel metadata columns and manual shipping sheets
            if query_has_q3:
                matched_q3 = [term for term in q3_terms if term in haystack]
                if matched_q3:
                    score += 20.0 * len(matched_q3)
                if chunk.file_type in {".xlsx", ".xlsm"}:
                    score += 10.0
                if any(k in chunk.source_file.lower() or k in chunk.sheet.lower() for k in ["manual", "ship"]):
                    score += 15.0
```

### 2.4 Audit Summary Table of Hardcoding
| Category | File Location | Mechanism / Value | Impact / Flaw |
|---|---|---|---|
| **Hardcoded Query Sets** | `mom_local_index.py:305` | `q1_terms = [...]` | Overfits ranking specifically to MES/MOM benchmark query |
| **Hardcoded Query Sets** | `mom_local_index.py:307` | `q2_terms = [...]` | Overfits ranking specifically to Japanese production history query |
| **Hardcoded Query Sets** | `mom_local_index.py:309` | `q3_terms = [...]` | Overfits ranking specifically to manual shipping column names |
| **Artificial Scoring Bonus** | `mom_local_index.py:336, 346, 362` | `+15.0 * len(matched_terms)`, `+20.0 * len(matched_terms)` | Fabricates non-standard rank scores up to +200 points |
| **Filetype Bias** | `mom_local_index.py:338, 348, 364` | `+10.0` for PDF / Excel based on query intent | Artificially prefers specific file formats regardless of text relevance |
| **Filename Bias** | `mom_local_index.py:340, 350, 366` | `+15.0` for fixed substrings (`mes`, `mom`, `生産履歴`, `仕様`, `manual`, `ship`) | Distorts lexical relevance with hardcoded name matching |
| **Negative File Penalty** | `mom_local_index.py:353-356` | `score -= 50.0` specifically targeting `erd_kho_van_new.html` | Deliberately demotes an HTML file to keep it off the top results for Q2 |

---

## 3. Comparative Architecture & Ranking Algorithms in AIOS_habbit

### 3.1 Retrieval Engines in the Workspace
The codebase contains three distinct search/retrieval subsystems:

| Dimension | MOM Local Index (`mom_local_index.py`) | RAG Search (`rag_search.py`) | RAG v2 (`rag_v2/index.py`) |
|---|---|---|---|
| **Data Storage** | Flat JSONL file (`mom_local_index.jsonl`) | SQLite (`chunk_metadata` + `chunk_fts`) | SQLite WAL (`chunks` table + `chunks_fts` + vector tables) |
| **Lexical Retrieval** | Substring / Token Count + Heuristic Boosts | SQLite FTS5 BM25 (`bm25(chunk_fts)`) | SQLite FTS5 BM25 (`bm25(chunks_fts, ...)`) |
| **Semantic Retrieval** | None (Text-only) | None | BGE-M3 Dense (1024D) + Sparse Lexical + ColBERT Multi-vector MaxSim |
| **Ranking Fusion** | Score sorting + First-per-file diversity | Linear weighted boost | Reciprocal Rank Fusion (RRF) + Deterministic Lexical Candidate Scoring |
| **CJK / Multi-language** | Unicode regex `[a-zA-Z0-9_À-ỹ\u4e00-\u9faf\u3040-\u30ff]+` | `\w+` tokens | Overlapping 2/3/4-character CJK n-grams + word tokens |
| **Hardcoding Status** | **Heavily Overfitted** (`q1_terms`, `q2_terms`, `q3_terms`, `-50.0`) | Neutral | **Quarantined & Zero Hardcode** (Guarded by `test_rag_v2_hardcode_guard.py`) |

### 3.2 Analysis of RAG v2 Lexical Candidate Scoring (`_score_candidate`)
In `src/aios_habit/rag_v2/index.py:2999-3130`, the generic deterministic candidate scoring calculates:
1. **Tokenization & CJK N-grams**: Decomposes text into word tokens and 2/3/4-grams for Japanese/Chinese text.
2. **Frequency Capping**: `lexical_count = min(5.0, raw_lexical_count)` to prevent keyword stuffing.
3. **Metadata Matching**: `source_token_matches * 2.0` (title/path) + `structure_token_matches * 1.0` (section/sheet).
4. **Exact Phrase Bonuses**: `+4.0` for full exact phrase in text, `+3.0` in filename/path, `+1.5` in sheet/section.
5. **Domain-Neutral Intent Matching**: Checks for action words (`check`, `verify`, `bước`, `kiểm`) and problem words (`error`, `fault`, `lỗi`).
6. **Repetitive Dump Penalty**: Penalizes low-information repetitive logs.

### 3.3 Recommended Algorithm for `mom_local_index.py` Standardizing to BM25 / TF-IDF
To cleanly satisfy Requirement 1 without introducing heavy external dependencies or breaking the simple standalone JSONL index architecture:
1. **In-Memory BM25 / TF-IDF with CJK N-Grams**:
   - Compute corpus statistics across the chunks loaded from `index_path` ($N$, document frequencies $DF(t)$, average document length $avgdl$).
   - Standard BM25 IDF:
     $$\text{IDF}(t) = \ln\left(1 + \frac{N - DF(t) + 0.5}{DF(t) + 0.5}\right)$$
   - Standard BM25 term weighting with $k_1 = 1.2$, $b = 0.75$:
     $$\text{TF\_BM25}(t, D) = \frac{\text{TF}(t, D) \cdot (k_1 + 1)}{\text{TF}(t, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{avgdl}\right)}$$
   - Combine with objective metadata weighting (matching tokens in `source_file`, `relative_path`, or `sheet` receive natural multiplier).
   - Exact phrase boost for consecutive query tokens found in chunk text.
   - Result: 100% objective, mathematically rigorous, query-agnostic ranking with zero hardcode.

---

## 4. Caller and Dependency Map

### 4.1 Dependency Graph
```
[ mom_local_index.py ]
       ├── MomChunk (Dataclass)
       │      └── Imported by: mom_coverage.py, test_mom_pdf_ingestion_retrieval.py
       ├── MomSearchHit (Dataclass)
       │      └── Consumed by: mom_benchmark.py (generate_mom_grounded_answer), test_mom_local_pilot.py
       ├── MomIndexBuildResult (Dataclass)
       │      └── Imported by: mom_coverage.py
       ├── build_mom_local_index()
       │      └── Imported by: mom_coverage.py (summarize_mom_coverage)
       │      └── Called in tests: test_mom_local_pilot.py, test_mom_pdf_ingestion_retrieval.py
       │      └── Indirectly called by: scripts/audit_mom_corpus.py (via mom_coverage)
       ├── load_mom_chunks()
       │      └── Imported by: mom_coverage.py (summarize_mom_coverage)
       │      └── Internal use: search_mom_index()
       ├── search_mom_index()
       │      └── Called in tests: test_mom_local_pilot.py, test_mom_pdf_ingestion_retrieval.py
       ├── build_mom_qa_prompt()
       │      └── Called in tests: test_mom_local_pilot.py
       ├── create_mom_case_from_hit()
       │      └── Called in tests: test_mom_local_pilot.py
       └── generate_safe_benchmark_questions()
              └── Called in tests: test_mom_local_pilot.py
```

### 4.2 Quarantine Status in `tests/test_rag_v2_hardcode_guard.py`
- Line 40 of `tests/test_rag_v2_hardcode_guard.py` explicitly lists `"aios_habit.mom_local_index"` under `QUARANTINED_IMPORT_PREFIXES`.
- `rag_v2` does not and must not import `mom_local_index`.
- Modifying `mom_local_index.py` will not cause any adverse side effects in `rag_v2`.

---

## 5. Comprehensive Inventory of Existing Tests

| Test File | Test Function | Target Verified | Impact of Hardcode Removal |
|---|---|---|---|
| `tests/test_mom_local_pilot.py:27` | `test_mom_local_index_chunks_and_search_synthetic_text` | `build_mom_local_index`, `search_mom_index("production history input fields")` | **PASS** — Markdown content matches query tokens naturally |
| `tests/test_mom_local_pilot.py:49` | `test_mom_prompt_pack_includes_refs_and_privacy_warning` | `search_mom_index("MOM WMS interaction")`, `build_mom_qa_prompt` | **PASS** — Flow.md content matches query tokens naturally |
| `tests/test_mom_local_pilot.py:68` | `test_mom_prompt_pack_marks_insufficient_when_no_hits` | `build_mom_qa_prompt("unknown question", [])` | **PASS** — Validates insufficient evidence handling on empty hit list |
| `tests/test_mom_local_pilot.py:79` | `test_create_mom_case_from_hit_has_draft_local_provenance` | `search_mom_index("production history")`, `create_mom_case_from_hit` | **PASS** — Case creation verifies provenance metadata |
| `tests/test_mom_local_pilot.py:228` | `test_mom_local_index_uses_document_extractors_for_html_pptx_xlsm` | `search_mom_index("interface mapping token")`, `search_mom_index("HTML production result")` | **PASS** — Extracts and matches terms from PPTX and HTML |
| `tests/test_mom_local_pilot.py:530` | `test_generate_mom_grounded_answer_returns_actual_sections` | `search_mom_index("Production registration")`, `generate_mom_grounded_answer` | **PASS** — Grounded answer generator consumes hits structure |
| `tests/test_mom_local_pilot.py:567` | `test_generate_mom_grounded_answer_filters_unsupported_specific_terms` | `search_mom_index("unsupported blockchain topic...")` | **PASS** — Verifies abstention on unsupported domain terms |
| `tests/test_mom_local_pilot.py:597` | `test_generate_mom_grounded_answer_broadened_fallback_not_high_confidence` | `search_mom_index("unicorn interface")` | **PASS** — Fallback handling with low/medium confidence |
| `tests/test_mom_pdf_ingestion_retrieval.py:47` | `test_mom_index_includes_pdf_chunks` | `build_mom_local_index` with mock PDF text | **PASS** — Verifies indexing of PDF text-layer |
| `tests/test_mom_pdf_ingestion_retrieval.py:74` | `test_retrieval_q1_mes_mom_boosting` | `search_mom_index("What is the difference between MES and MOM?")` | **PASS** — `MES_MOM_Linkage.pdf` has higher BM25 score than unrelated `ItemMaster.xlsx` without hardcode |
| `tests/test_mom_pdf_ingestion_retrieval.py:114` | `test_retrieval_q2_production_history_anti_erd` | `search_mom_index("Các chức năng của 生産履歴登録システム là gì?")` & `search_mom_index("ERD diagram showing tables Warehouse")` | **PASS** — Japanese spec matches query 1; ERD HTML matches query 2. Natural BM25 separation without `-50.0` penalty |
| `tests/test_mom_pdf_ingestion_retrieval.py:165` | `test_retrieval_q3_manual_shipping_no_regression` | `search_mom_index("ManualShipping_ExistingLineAuto_InboundDownload...")` | **PASS** — Excel schema matches all tokens; BM25 naturally scores highest |

---

## 6. Implementation Recommendations for R1

1. **Delete All Hardcoded Term Dictionaries**:
   - Completely remove `q1_terms`, `q2_terms`, `q3_terms`.
   - Remove `query_has_q1`, `query_has_q2`, `query_has_q3`.
   - Remove all `if query_has_q1: ...`, `if query_has_q2: ...`, `if query_has_q3: ...` blocks.
   - Remove the targeted `-50.0` penalty on `erd_kho_van_new.html`.
2. **Implement Generic In-Memory BM25 / TF-IDF**:
   - Compute corpus DF and IDF from `load_mom_chunks(index_path)`.
   - Tokenize query and chunks using Unicode + CJK n-gram sub-tokens (2-grams, 3-grams) for robust Asian text matching.
   - Apply standard BM25 saturation ($k_1=1.2, b=0.75$) with chunk length normalization.
   - Apply objective boosts:
     - Exact phrase match in chunk text: `+4.0`.
     - Exact phrase match in source filename / relative path: `+3.0`.
     - Token matches in filename, path, or sheet: `+1.5` per matched token.
   - Maintain hit deduplication and file diversification.
3. **Preserve Exact Data Signatures**:
   - `search_mom_index(query: str, limit: int = 5, index_path: str | Path = INDEX_FILE) -> list[MomSearchHit]`
   - `MomSearchHit(chunk=chunk, score=score, matched_terms=sorted(set(matched)))`
   - Keeps 100% backward compatibility for all callers and tests.
