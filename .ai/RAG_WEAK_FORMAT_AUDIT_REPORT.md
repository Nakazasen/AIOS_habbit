# RAG Weak Format Audit Report

Real MOM folder used locally only: `[LOCAL_WORKSPACE]\MOM_WMS_QLLSSX\tailieugoc`.

No raw document text is included here. Aggregates were written under ignored `local_runs/rag_hardening_sweep/`.

## Aggregate snapshot
- Files audited: 52
- Extensions audited: `.xlsx`, `.png`, `.pptx`, `.pdf`, `.html`, `.xlsm`
- PDF: 6 files, 6 content-supported, 0 metadata-only
- PPTX: 7 files, 7 content-supported via local zip/XML extractor
- DOCX: 0 files present in this MOM sample
- PNG/JPG: 17 PNG files, OCR/local text produced for 16, 1 empty/weak
- HTML: 1 file, 1 content-supported
- XLSX/XLSM: 21 files, 21 content-supported
- Scanned PDF suspected: 0 in this audit because text extraction succeeded for all PDFs

## Weakest areas
1. Images remain dependent on local OCR availability/quality.
2. DOCX adapter is implemented/tested but no DOCX files were present in this MOM folder.
3. PPTX extraction is now content-supported, but fidelity is XML-text level rather than full layout semantics.
4. Excel is strong for cells/shapes, but layout-heavy semantics still need human review.

## Priority recommendation
1. Keep registry/fallback metadata-only behavior.
2. Improve PPTX/DOCX fidelity only if owner needs layout-level reconstruction.
3. Improve OCR language packs for Japanese/Vietnamese screenshots.
4. Add evaluator/owner acceptance before claiming any parity.

