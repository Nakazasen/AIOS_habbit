# AIOS FAIR COMPARE AFTER EXCEL EXTRACTION REPORT

- Excel extraction adapter commit: 7d46f76
- AIOS answers: 12
- NotebookLM answers: 0 (pending re-run for new questions)
- insufficient evidence before: 12/12
- insufficient evidence after: 2/12
- AIOS wins: N/A (human review required)
- NotebookLM wins: N/A
- ties: N/A
- uncertain: 12
- Excel extraction helped: YES (Insufficient evidence dropped from 12 to 2)
- remaining blockers: NotebookLM answers need to be generated for new questions. PDF, PPTX, Image/HTML extraction are metadata-only.
- next best adapter: PDF (PyMuPDF4LLM)
- tests: PASS (tests/test_notebooklm_compare.py, tests/test_document_extractors.py)
- full pytest: PASS (325 passed)
- real docs tracked: NO
- runtime outputs tracked: NO
- NotebookLM parity claimed: NO
- P1.0 opened: NO

## Notes
We fixed two bugs that masked AIOS's real capabilities:
1. notebooklm_compare.py file discovery limit prevented Excel files from being selected in random sampling.
2. FTS MATCH query strict AND logic and regex parsing stripped Unicode/Japanese filename characters, causing 0 search results.

With these fixed, BM25 retrieval successfully found the extracted Excel texts and AIOS answered 10/12 questions confidently!
