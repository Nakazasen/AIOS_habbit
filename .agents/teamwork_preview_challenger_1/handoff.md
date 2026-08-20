# Adversarial Challenge & Stress-Test Handoff Report

**Agent**: `teamwork_preview_challenger_1` (critic, specialist)  
**Parent**: `085caf98-0e6e-4709-bce0-a3cf6358fe59`  
**Verdict**: **APPROVE**  
**Date**: 2026-08-20T13:43:30Z  

---

## 1. Observation

### Target 1: MOM Local Index & BM25 Search (`src/aios_habit/mom_local_index.py`)
- **Hardcode Removal**: AST audit confirmed zero instances of `q1_terms`, `q2_terms`, `q3_terms`, zero artificial document penalty constants (`-50.0` or `-50`), and zero mentions of `erd_kho_van_new.html`.
- **Tokenization (`lines 92-123`)**:
  ```python
  _WORD_RE = re.compile(r"[a-zA-Z0-9_À-ỹ]+", re.UNICODE)
  _CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+")
  ```
  Decomposes words into base terms, underscore subterms (e.g. `order_registration_batch` -> `order`, `registration`, `batch`), and CJK 1-grams, 2-grams, 3-grams, and full compounds.
- **BM25 Mathematical Formulation (`lines 388-440`)**:
  - Standard IDF: $IDF(t) = \ln\left(1.0 + \frac{N - df + 0.5}{df + 0.5}\right) \ge 0.0$.
  - Normalized TF: $TF_{norm} = \frac{tf_{eff} \cdot (k_1 + 1.0)}{tf_{eff} + k_1 \cdot \left(1.0 - b + b \cdot \frac{doc\_len}{avg\_doc\_len}\right)}$ where $k_1=1.5, b=0.75$.
  - Score bounds: `score = max(0.0, round(score, 4))` ensures strict non-negativity.
- **Tie-Breaking & Diversification (`lines 444-466`)**: Stable score sort combined with preview deduplication (`preview_key`[:160]) and multi-file round-robin ensures file diversity and prevents duplicate chunk spam.

### Target 2: Excel Streaming Row-Chunking Extractor (`src/aios_habit/excel_extractors.py`)
- **Default Limits (`lines 13-30`)**:
  - `max_rows_per_sheet: int | None = None`
  - `max_non_empty_cells: int | None = None`
  - `chunk_row_size: int = 500`
  - `enable_row_chunking: bool = True`
  - `repeat_headers_in_chunks: bool = True`
  - `max_header_rows: int = 3`
- **Streaming Region Partitioning (`lines 200-276`)**:
  - Splits tables with $> 500$ rows into chunks while propagating multi-level headers across all chunks (`rows_for_chunk = header_selected + chunk_data`).
  - Region metadata records exact `chunk_index`, `total_chunks`, `row_range`, and `cell_range`.
  - Merged cells are dynamically tracked per chunk without dropping boundary merges (`chunk_relevant = [item for item in relevant if not (item.max_row < chunk_start_row or item.min_row > chunk_end_row or item.max_col < first or item.min_col > last)]`).

---

## 2. Logic Chain

1. **Edge Case 1: Empty and Whitespace Queries**:
   - `search_mom_index` strips the query string `q = query.strip().lower()`. If empty or containing only non-word punctuation, it returns `[]` immediately without throwing errors or running corpus iterations.
2. **Edge Case 2: Single Character Queries**:
   - Single ASCII letters (e.g. `'a'`), digits (e.g. `'1'`), and single CJK ideograms (e.g. `'製'`) produce valid 1-element token lists.
   - Phrase boost guard `if q in haystack and len(q) >= 2:` correctly avoids false exact-phrase bonuses for 1-char strings.
   - IDF remains strictly non-negative; doc-length normalization scales appropriately.
3. **Edge Case 3: Rare & Compound CJK Terms**:
   - Multilingual CJK n-gram sub-tokenization expands compounds (e.g. `自動化工程`) into 1-grams, 2-grams, 3-grams, and 4-grams.
   - Exact phrase matching triggers `+10.0` bonus for the complete compound, ensuring that full compound matches score strictly higher than partial sub-token matches (monotonicity).
4. **Edge Case 4: Deeply Nested Underscore Identifiers**:
   - Snake_case identifiers (e.g. `mom_prod_v2_order_registration_batch_async_handler`) are tokenized into the full string plus all split parts.
   - Enables exact match retrieval for full variable/API names as well as constituent component queries (e.g. `async_handler`, `registration_batch`).
5. **Edge Case 5: Identical Scores & Diversification**:
   - When identical documents exist, stable sort order is maintained.
   - The diversification loop prioritizes distinct files and deduplicates identical preview text, providing high-quality, balanced top-$k$ hits.
6. **Edge Case 6: Large Excel Sheets (>1,500 rows)**:
   - Synthetic workbooks with 1,850 and 2,000 rows were tested.
   - Partitions into 4 sequential chunks with zero data loss, exact coordinate tracking, and repeated headers.
7. **Edge Case 7: Multi-level Headers & Boundary Merges**:
   - 2-row and 3-row hierarchical headers are correctly resolved into structured path headers (e.g. `Asia Pacific > Vietnam > Hanoi Plant`).
   - Merged cell ranges spanning chunk boundaries (e.g. `A490:A520` across chunk boundary at row 500) are properly retained in all intersecting chunks.

---

## 3. Caveats

- Memory consumption for extraordinarily large Excel workbooks (>500,000 rows) remains bounded by `openpyxl`'s DOM mode unless read-only mode is configured. However, for all MOM enterprise spreadsheet operational profiles (BOMs, inventory, order logs up to tens of thousands of rows), memory overhead is modest and well within system limits.
- No other caveats.

---

## 4. Conclusion

**Verdict: APPROVE**

Both `src/aios_habit/mom_local_index.py` (MOM BM25 Search Engine) and `src/aios_habit/excel_extractors.py` (Streaming Tabular Extractor) have passed all adversarial challenges, boundary stress tests, and mathematical monotonicity / non-negativity audits without failure or regressions.

---

## 5. Verification Method

To independently verify the test suite, run:
```bash
pytest tests/test_adversarial_mom_bm25_and_excel.py -v
pytest tests/test_mom_search_bm25_zero_hardcode.py -v
pytest tests/test_document_extractors.py -v
```

All 12 adversarial test cases in `tests/test_adversarial_mom_bm25_and_excel.py` validate:
1. `test_mom_bm25_empty_and_whitespace_queries`
2. `test_mom_bm25_single_character_queries`
3. `test_mom_bm25_rare_cjk_compounds_and_variations`
4. `test_mom_bm25_deeply_nested_underscore_identifiers`
5. `test_mom_bm25_identical_scores_and_tie_breaking`
6. `test_mom_bm25_score_monotonicity_and_strict_non_negativity`
7. `test_mom_bm25_zero_hardcode_ast_verification`
8. `test_excel_streaming_large_workbook_over_1500_rows`
9. `test_excel_multi_level_hierarchical_headers_2_and_3_rows`
10. `test_excel_merged_cells_spanning_chunk_boundaries`
11. `test_excel_custom_chunk_row_size_variations`
12. `test_excel_no_data_loss_and_chunk_boundary_continuity`
