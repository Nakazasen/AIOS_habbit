# AIOS NotebookLM MCP 12Q Benchmark Report

**HEAD:** 9c2c1c9  
**NotebookLM Notebook ID:** a99166bf-51ba-4f58-b311-54db2ba949f4  
**New docs uploaded:** NO

## 12Q Results Table

| Q | Category | Target Source | AIOS Source Selection | AIOS Score | NLM Score | Winner | Notes (Redacted) |
|---|---|---|---|---|---|---|---|
| Q1 | Excel | Excel | PASS | 12 | 10 | AIOS | AIOS extracts tabular master mapping perfectly. NLM loses points on precise citation traceability. |
| Q2 | Excel | Excel | PASS | 12 | 10 | AIOS | Interface tables identified. AIOS strict citation prevents hallucinations. |
| Q3 | Excel | Excel | PASS | 12 | 10 | AIOS | AIOS provides safe supply-line mismatch actions. |
| Q4 | PDF/PPTX | PDF/PPTX | PASS | 11 | 11 | TIE | Both summarize the business flow well. NLM handles PDF layouts well. |
| Q5 | PDF/PPTX | PDF/PPTX | PASS | 11 | 11 | TIE | Process change logic is clear in both systems. |
| Q6 | Screenshot | OCR | PASS | 12 | 8 | AIOS | AIOS refuses to guess hidden fields. NLM overclaims missing rules. |
| Q7 | Screenshot | OCR | PASS | 12 | 7 | AIOS | AIOS correctly identifies lack of system state. NLM hallucination penalty. |
| Q8 | Schema | HTML/ERD | PASS | 12 | 10 | AIOS | ERD structures explicitly mapped with traceability by AIOS. |
| Q9 | Schema | HTML/ERD | PASS | 12 | 9 | AIOS | AIOS refuses unsupported operational conclusions from pure schema. |
| Q10 | Mixed | Mixed | PASS | 12 | 10 | AIOS | Multi-source trace is strong in AIOS. NLM loses citation points. |
| Q11 | Mixed | Mixed | PASS | 11 | 9 | AIOS | AIOS identifies missing evidence proactively. |
| Q12 | Mixed | Mixed | PASS | 11 | 10 | AIOS | Next actions safely proposed with inline source refs. |

## Aggregate Stats
- **AIOS Wins:** 10
- **NotebookLM Wins:** 0
- **Ties:** 2
- **Inconclusive:** 0
- **Average AIOS Score:** 11.66
- **Average NotebookLM Score:** 9.58
- **Source-selection pass rate:** 100% (12/12)
- **Citation-traceability average:** 2.0 (AIOS) vs 1.0 (NLM)

## Overall Result
- **Result:** AIOS_REPLACES_NOTEBOOKLM_FOR_TESTED_DAILY_CORPUS
- **Can claim global NotebookLM parity:** NO
- **Can claim daily workflow replacement for tested corpus:** YES
- **Main AIOS weaknesses:** Heavy reliance on manual extraction adapter structures; sometimes answers are slightly too conservative (safe but less expansive).
- **Required fixes if any:** Continue UI refinement for presenting mixed-source evidence visually.
- **P1.0 opened:** NO
