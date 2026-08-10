# RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY

Status: `DONE`

## Outcome

Recovered every in-scope MOM/WMS corpus source through bounded local extraction or OCR without cloud processing or owner exclusions.

## Delivered scope

- Added local Tesseract OCR with confidence, sample count, preprocessing, attempt, engine, language, page, and quality-gate provenance.
- Added deterministic grayscale/autocontrast/upscale and layout-aware PSM attempts while retaining the `35.0` usable-confidence threshold.
- Added page-level OCR fallback for scanned or mixed PDFs while preserving native-text priority and the three-page safety guard.
- Preserved OCR provenance through extraction, registry, chunk metadata, and local indexing.
- Added strict all-file denominator accounting and validated owner-disposition support.
- Added a deterministic local corpus audit CLI and example disposition schema.

## Final corpus evidence

Strict audit command:

```powershell
.\.venv\Scripts\python.exe scripts\audit_mom_corpus.py "D:\Sandbox\MOM_WMS_QLLSSX\tailieugoc" --output "local_cases\mom_pilot\corpus_audit_ocr_v2.json"
```

Result:

- `70/70` usable sources (`100.0%`).
- `51` native-usable and `19` OCR-usable files.
- All `17` PNG sources recovered.
- `670` chunks generated, including `38` OCR chunks (`20` PNG and `18` PDF).
- `0` unresolved files, `0` unknown unsupported sources, and `0` owner exclusions.
- `strict_passed: true`, `privacy_level: local_only`, and `cloud_ocr_used: false`.
- Runtime report remains ignored under `local_cases/mom_pilot/corpus_audit_ocr_v2.json`.

The two PDF page-guard records are explicit page-level safety notices inside otherwise usable documents; they do not create unresolved source dispositions.

## Verification

- Focused PDF/OCR/extraction suite: `49 passed`.
- Full repository regression: `1108 passed`.
- Documentation contract: `DOCUMENTATION_CONTRACT=PASS`.
- `python -m compileall -q src tests`: PASS.
- Application audit: `PASS`, no errors or warnings.
- Workspace Chat bare import: PASS; expected Streamlit missing-context warnings only.
- `git diff --check`: PASS; existing Windows LF-to-CRLF notices only.

## Privacy constraints

OCR, temporary images, extracted text, and indexes remain local under ignored runtime roots. Logs and committed evidence contain aggregate counts/statuses, not private extracted document text.

## Rollback

Disable the OCR adapter and rebuild the local index from canonical sources. Original source files were never modified; prior audit artifacts can be retained for comparison.
