# Extraction Upgrade Report

## Adapter Implemented
**Excel Cell + Shape/Textbox Adapter (openpyxl + zipfile)**
Implemented a safe, local-only adapter leveraging `openpyxl` for Excel cells and `zipfile` parsing `xl/drawings/drawing*.xml` for text boxes and shapes.

## Files Affected
- `src/aios_habit/document_extractors.py` (added zipfile logic)
- `src/aios_habit/notebooklm_compare.py` (hooked into `build_chunks_from_folder`)
- `tests/test_document_extractors.py` (new test)
- `tests/test_notebooklm_compare.py` (updated test)

## Testing and Quality
- **Test Results**: All tests including new fake/generated fixtures pass correctly.
- **Full Pytest**: 325/325 passed.
- **AIOS Real Run**: Executed successfully. AIOS now extracts Excel text from both cells and shapes instead of falling back to metadata-only. The NotebookLM benchmark harness consumes this real text for valid queries.
- **Remaining Metadata-only types**: PDF (during benchmark, since PyMuPDF4LLM is not installed and fitz is currently bypassed by the benchmark harness), PPTX, and HTML/Images.
- **Next Recommended Adapter**: `ADD_PPTX_ADAPTER` (since PPTX is the second largest failure category for NotebookLM imports).

## Parity
**NotebookLM Parity Claimed**: NO (We have only closed the extraction gap for Excel; PPTX and PDF gaps remain, and human review is still needed for the updated answers).
