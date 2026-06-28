# AIOS Extraction Adapter Strategy

## Extractor Adapter Interface
An AIOS Extractor Adapter provides a consistent interface to third-party libraries while shielding the rest of the application from dependency-specific imports.
Each adapter must:
1. Accept a `Path` and a `root` directory.
2. Return a list of `ExtractionResult` objects.
3. Not crash if an optional dependency is missing; instead, it must return a failure or unsupported result.
4. Support gracefully failing to the next adapter in the chain.

## Common Element Schema
All extraction results are normalized via `build_elements_from_extracted_payload` into the `RAGDocumentElement` schema, which includes:
- `element_id`, `document_id`, `text`
- `source_title`, `source_path`, `relative_path`, `file_type`
- `privacy_mode`
- `extractor_name`, `extraction_status`, `warnings`
- `metadata`

## Fallback Chain by File Type
### Excel (.xlsx, .xlsm)
1. Existing `openpyxl` cell/table extraction.
2. Add standard library `zipfile` parsing to extract text from shapes/textboxes in `xl/drawings/drawing*.xml`.
3. (Optional) Pandas table view if enabled.
4. Fallback: Metadata-only if extraction fails.

### PDF (.pdf)
1. `PyMuPDF4LLM` (if installed, optional).
2. Existing `PyMuPDF` (`fitz`) text layer extraction.
3. Existing `PyMuPDF` + `pytesseract` OCR extraction.
4. (Optional) `Docling`.
5. Fallback: Metadata-only.

### PPTX (.pptx)
1. Existing `python-pptx` (via XML parsing) which extracts slide and note text.
2. (Optional) `Docling` or `MarkItDown`.
3. Fallback: Metadata-only.

### Image (.png, .jpg, etc.)
1. Existing OCR via `pytesseract` + `PIL`.
2. Fallback: Metadata-only.

## Preserving Citation Metadata
To retain strict traceability to the origin, the `ExtractionResult` captures context that maps to `RAGDocumentElement` attributes:
- **page**: Set `ExtractionResult.page` -> maps to `page_number` in `metadata`.
- **sheet**: Set `ExtractionResult.sheet` -> maps to `sheet_name`.
- **row_range / cell_range**: Set `ExtractionResult.row_range` -> maps to `metadata['row_range']`.
- **slide**: Set `ExtractionResult.slide` -> maps to `metadata['slide']`.
- **shape_id / image_id**: Included in `metadata`.
- **extractor_name**: Directly maps to `extractor_name`.

## Marking Extraction Confidence
Extraction status should be explicit:
- **High**: `extracted_success`
- **Medium/Partial**: `extracted_partial`, `ocr_partial`
- **Low/Failed**: `failed_with_reason`, `unsupported_no_local_tool`
- **Metadata Only**: Returns empty text but sets `extraction_status = "metadata_only"` (or similar handled natively in `notebooklm_compare.py` fallback).

## Avoiding Breaking Existing Tests
- Do not remove or change the signature of existing functions (`extract_text_chunks_from_file`, `_extract_excel`, etc.).
- Augment existing results. For Excel, we will simply append the `ExtractionResult` from the drawing XML parsing to the list returned by `_extract_excel`.
- Return empty strings or handle errors gracefully within the adapters so the indexer doesn't crash.

## Keeping Heavy Dependencies Optional
- Do not add heavy dependencies (like `docling` or `unstructured`) to `pyproject.toml` or `requirements.txt` yet.
- Use `importlib.util.find_spec` or try/except blocks when importing optional adapters.
