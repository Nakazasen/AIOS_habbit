# AIOS NotebookLM MCP 12Q Benchmark Plan

## Mission
Run a strict 12-question NotebookLM MCP benchmark to evaluate if AIOS can replace NotebookLM for the tested daily workflow corpus.

## Privacy Policy
- No raw answers committed.
- No raw chunks printed.
- No local_runs committed.
- No raw documents committed.
- NotebookLM parity claimed: NO
- P1.0 opened: NO

## 12Q Set

### A. Excel-heavy (3 questions)
**Q1.** What is the staging and master mapping for ManualShipping vs ExistingLine?
- Target source type: Excel

**Q2.** Describe the data handoff and interface table relationships between WMS, MOM, and AGV.
- Target source type: Excel

**Q3.** How do you investigate a quantity/container/supply-line mismatch using table evidence?
- Target source type: Excel

### B. PDF/PPTX process/manual boundary (2 questions)
**Q4.** What is the MOM/AMS business flow regarding the automatic vs manual/owner review boundary?
- Target source type: PDF/PPTX

**Q5.** How is an operation/process change or design/running change explained in the process documentation?
- Target source type: PDF/PPTX

### C. Screenshot/image/OCR (2 questions)
**Q6.** What visible UI fields, statuses, containers, or oricon evidence can be trusted directly from screenshots?
- Target source type: Screenshot/Image/OCR

**Q7.** What operational or systemic states must NOT be inferred from screenshot-only evidence?
- Target source type: Screenshot/Image/OCR

### D. HTML/ERD/schema (2 questions)
**Q8.** What tables, fields, and relationships are explicitly shown in the HTML/ERD/schema evidence?
- Target source type: HTML/ERD/schema

**Q9.** What operational conclusions are unsupported if only schema/ERD documentation is available?
- Target source type: HTML/ERD/schema

### E. Mixed multi-source (3 questions)
**Q10.** Explain a full troubleshooting path that combines evidence from Excel, PDF/PPTX, and screenshots.
- Target source type: Mixed (Excel, PDF/PPTX, Screenshot)

**Q11.** Identify missing evidence that would be required before answering a complex production issue.
- Target source type: Mixed

**Q12.** Produce a set of owner next actions and a handover summary, citing sources correctly.
- Target source type: Mixed

## Scoring Rubric (Max 12 points per question)
Each dimension is scored 0–2:
1. Relevance to question
2. Evidence coverage
3. Correct uncertainty handling
4. Non-hallucination
5. Practical usefulness
6. Source/citation traceability

**Penalty Rules:**
- Wrong primary source type without justification: -2
- Overclaims hidden business rule from screenshot/schema only: -2
- Lacks uncertainty when evidence is weak: -1 or -2
- Answer is safe but not actionable: usefulness max 1
- No citation/source traceability: source score max 1
- Raw unsupported conclusion: non-hallucination max 1
