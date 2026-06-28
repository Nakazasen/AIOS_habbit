# PDF Extraction Adapter Research

## Current PDF Behavior
Currently, AIOS_habbit does not extract content from PDFs. When a PDF is ingested, it falls back to a metadata-only chunk. This results in bad evidence during RAG because the content isn't searchable, and the Strong Model Answer Bridge correctly refuses to hallucinate from metadata alone (as seen in the Q1 and Q2 failures during the MOM 3Q test).

## Installed PDF Libraries
An inspection of the local environment reveals the following availability:
- `pymupdf4llm`: False
- `fitz` (PyMuPDF): True
- `pypdf`: True
- `pdfplumber`: True
- `docling`: False
- `markitdown`: False

## Chosen Adapter & Fallback
Since `pymupdf4llm` is not installed, but `fitz` (PyMuPDF) is present, we will use **PyMuPDF (`fitz`)** as the fallback. PyMuPDF is fast, robust, and capable of extracting text with page-level granularity, which maps perfectly to `RAGDocumentElement` requirements for citation.

If `fitz` import fails (which it shouldn't, given the check), the extractor will gracefully return an element with `extraction_status="dependency_missing"` and `_is_metadata_only="True"`.

## Out of Scope
This goal does not include:
- PPTX extraction
- Image OCR
- Vector DB
- Graph DB

These are omitted to maintain focus on solving the immediate text-based PDF gap, reducing complexity and adhering strictly to the user's instructions.

## Claims
- **NotebookLM parity claimed**: NO
- **P1.0 opened**: NO
