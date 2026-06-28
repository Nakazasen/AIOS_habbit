# Current Extraction State

## Supported File Types
- Text: `.txt`, `.md`, `.markdown`, `.json`, `.csv`
- Documents: `.pdf`, `.html`, `.docx`
- Spreadsheets: `.xlsx`, `.xlsm`
- Presentations: `.pptx`
- Images: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`

## Current Extraction Behavior
- **Excel**: Handled by `_extract_excel` via `openpyxl`. Only reads the first 12 sheets, and only values from the first 25 rows per sheet (`iter_rows()`). Fails to extract shapes, text boxes, and charts. AIOS `mom_local_index.py` also has an alternative Pandas path (`pd.read_excel`), which also ignores shapes and text boxes.
- **PDF**: Handled by `_extract_pdf_text_layer` via `pypdf`/`PyPDF2`. If no text is found, it falls back to `_extract_pdf_ocr` using `fitz` (PyMuPDF) + `pytesseract`.
- **PPTX**: Handled by `_extract_pptx` via `zipfile` reading XML. Extracts slide text and speaker notes.
- **Image**: Handled by `_ocr_image` via `pytesseract` and `PIL`.

## Where Metadata-Only Fallback Happens
- **NotebookLM Benchmark**: In `notebooklm_compare.py`, `build_chunks_from_folder()` explicitly bypasses all binary extraction. If `path.suffix.lower()` is not in `SUPPORTED_TEXT_SUFFIXES`, it sets `text = f"Metadata-only source record for {path.name}..."`. This ignores `document_extractors.py` completely for PDFs, Excel, and PPTX during the benchmark.
- **MOM Local Index**: In `mom_local_index.py`, `.doc`/`.docx` are disabled ("doc/docx extraction not enabled for MOM pilot"), and `.pdf` files without OCR return `unsupported_no_local_tool` if OCR fails.

## Why Current AIOS Loses to NotebookLM on V2
The V2 benchmark questions were based on NotebookLM's ability to ingest Excel, PPTX, and HTML files. Because `notebooklm_compare.py` uses metadata-only fallbacks for anything that isn't plain text, AIOS essentially has NO content indexed for the binary files and answers "Insufficient evidence". Even if `document_extractors.py` was used, it would fail to answer questions based on Excel shapes and text boxes since `openpyxl` ignores them.

## What Must Not Be Changed
- The core data structures in `rag_ingest.py` (`RAGDocumentElement`, `RAGChunk`).
- Existing text and CSV extraction logic.
- Privacy handling (e.g. `local_only` defaults).
- P1 requirement for local-first testing.
