# RAG Hardening Sweep Report

## What changed
- Added explicit extractor registry and metadata-only fallback schema.
- Added local heuristic evaluator foundation.
- Added tests for PPTX, DOCX, HTML, image/OCR safety, registry routing, metadata-only fallback, normalization, and evaluator final-answer eligibility.
- Added normalization to reduce coordinate-only garbage while preserving Japanese/Vietnamese/English text.

## Adapter status
- PPTX: local zip/XML extraction for slide text, notes, media count.
- DOCX: local zip/XML extraction for paragraphs, tables, headers/footers.
- HTML: stdlib parser; script/style/noscript removed; visible text, mermaid/code text retained as visible content.
- Image/OCR: local-only OCR through Tesseract if available; otherwise safe metadata/no cloud OCR.
- Excel: existing openpyxl cell/shape extractor retained; normalization reduces coordinate-only noise.
- PDF: existing PyMuPDF adapter retained.

## Real MOM weak-format benchmark
Aggregate only, no raw text committed:
- MOM 3Q rerun: retrieval/evidence path available; source-aware Q3 safeguards retained by tests.
- Weak-format 6Q run: simulated at evidence-pack/prompt level against available audited extensions.
- PPTX improved: content-supported for 7/7 PPTX files in current MOM folder.
- DOCX: adapter tested, but no DOCX files in MOM folder.
- PNG: OCR/local extraction depends on local Tesseract and language packs; metadata-only fallback remains safe.
- HTML: content-supported for 1/1 HTML files.
- Excel: content-supported for XLSX/XLSM; coordinate normalization added.

## Evaluation
- Heuristic only; Ragas/DeepEval not installed and not required.
- Local Evidence Draft remains non-final.
- Only strong/pasted/human-approved answer kinds are eligible for final comparison.
- Metadata-only evidence fails groundedness.

## Safety
- Direct provider/cloud calls were not added.
- Real MOM documents were not staged or committed.
- local_runs remains ignored.
- NotebookLM parity is not claimed.
- P1.0 remains locked.

## Remaining blockers
- Owner UI smoke test and owner acceptance run.
- OCR quality for Japanese/Vietnamese screenshots.
- Layout-aware PPTX/DOCX extraction if needed.
- Optional LLM judge evaluator if owner approves model use.
