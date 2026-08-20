# DISPATCH

## 2026-08-19T23:43:18Z

Mission:
Orchestrate the full implementation, refactoring, and testing of the MOM system upgrade in AIOS_habbit as detailed in ORIGINAL_REQUEST.md:
1. R1: Remove all hardcoded keyword lists (q1_terms, q2_terms, q3_terms) and penalty (-50.0) from mom_local_index.py, standardize to BM25/TF-IDF or RAG v2 Hybrid Retrieval.
2. R2: Upgrade Excel extractor in excel_extractors.py to streaming row-chunking with repeated headers, removing the 1000-row / 20k-cell hard limits.
3. R3: Remove POLISHED_ANSWERS and canned strings from scripts/generate_ai_grounded_report.py & scripts/run_workspace_chat_12_questions.py, integrate ClaimGuard dynamic abstention and evidence extraction.
4. R4: Add comprehensive tests and ensure 100% pytest pass rate (Zero Failures / Zero Errors).
