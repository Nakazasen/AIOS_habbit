# AIOS RAG Hardening Library Study

## Scope
Reviewed design patterns only from well-known document/RAG ecosystems. No external code was copied.

## Dependency availability
Observed locally: `fitz`, `pypdf`, `pdfplumber`, `docx`, `openpyxl`, `pandas`, `PIL`, `pytesseract`, `markdown`, `bs4`, `lxml` are importable. Not installed: `docling`, `unstructured`, `markitdown`, `pymupdf4llm`, `python_pptx`, `easyocr`, `haystack`, `llama_index`, `ragas`, `deepeval`.

## Docling patterns reviewed
- Use a DocumentConverter facade with format-specific backends.
- Preserve document elements, pages, tables, hierarchy and provenance.
- Convert to a common intermediate document model before chunking.
- AIOS already has `ExtractionResult` and chunk dictionaries, but lacked an explicit registry/capability layer.
- Risk: Docling is powerful but heavy; not added now.

## Unstructured patterns reviewed
- `partition_*` functions create typed elements with metadata.
- Chunking is downstream and preserves element categories.
- AIOS should keep element type, page/sheet/slide/image index and extraction status.
- Risk: broad dependency surface; not added now.

## Microsoft MarkItDown patterns reviewed
- Multi-format conversion to Markdown is useful as a fallback surface.
- AIOS should prefer local narrow adapters first, then optional markdown conversion later.
- Risk: adding MarkItDown now is unnecessary because it is not installed and PPTX/DOCX zip XML paths cover first-pass needs.

## LlamaIndex patterns reviewed
- Document -> node -> index -> retriever with metadata-preserving nodes.
- AIOS already has document elements/chunks and RAG metadata; hardening should normalize chunks before indexing.
- Risk: not needed as a dependency for local-first operation.

## Haystack patterns reviewed
- Componentized pipeline: converter, cleaner, splitter, writer, retriever, reranker.
- AIOS should expose adapter registry and capability checks without changing retrieval architecture.
- Risk: dependency not installed; not added.

## Ragas / DeepEval patterns reviewed
- Useful metrics: faithfulness, answer relevancy, context precision/recall.
- AIOS needs a local heuristic evaluator first; LLM judge remains optional.
- Critical rule: local evidence draft is not final and must not compete against NotebookLM final answers.

## Recommended adapter priority
1. Registry/capability layer and strict metadata-only fallback.
2. PPTX/DOCX/HTML local extractors.
3. Image metadata and optional local OCR only.
4. Excel shape/text cleanup and chunk normalization.
5. Heuristic evaluator foundation.
6. Optional Docling/Unstructured/MarkItDown later if owner approves dependency cost.

## Privacy impact and local-first requirements
- No cloud OCR.
- No full-folder upload.
- No raw extracted text committed.
- Local-only evidence remains blocked from direct cloud provider calls.
- Metadata-only fallback must never become content evidence.

## What not to implement now
- No vector DB/graph DB.
- No heavy framework dependency.
- No cloud OCR or image/person inference.
- No NotebookLM parity claim.
- No P1.0 opening.
