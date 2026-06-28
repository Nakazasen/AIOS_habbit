# Extraction Library Matrix

| Library | Supported Formats | Installed | Windows Risk | Dependency Weight | OCR Support | Table Support | Office Support | Shape/Textbox | Output Type | Recommended Role | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Docling** | PDF, DOCX, PPTX, XLSX, HTML, Images | No | Medium | Heavy | Yes | Yes | Yes | Yes | Markdown/JSON | Universal multi-format extractor | Optional later |
| **Unstructured** | PDF, Office, HTML, Images, etc. | No | High | Heavy | Yes | Yes | Yes | Limited | JSON/Elements | Universal partitioner | Optional later |
| **MarkItDown** | Office, PDF, HTML, etc. | No | Low | Medium | No | Basic | Yes | Basic | Markdown | Lightweight Markdown converter | Optional later |
| **PyMuPDF4LLM** | PDF | No | Low | Light | No (relies on PyMuPDF) | Yes | No | No | Markdown/JSON | PDF optimized for RAG | Optional later |
| **PyMuPDF (fitz)** | PDF | Yes | Low | Medium | External (Tesseract) | Basic | No | No | Text/Images | Core PDF extraction | Use now |
| **openpyxl** | XLSX, XLSM | Yes | Low | Light | No | Yes (cells) | Excel | No | Python Objects | Core Excel cell extraction | Use now |
| **pandas** | CSV, XLSX, etc. | Yes | Low | Medium | No | Yes (dataframe) | Excel | No | DataFrame/String | Data/table extraction | Use now |
| **python-pptx** | PPTX | Yes | Low | Light | No | Yes | PPTX | Yes | Python Objects | Core PPTX extraction | Use now |
| **Pillow (PIL)** | Images | Yes | Low | Light | External | No | No | No | Image object | Image handling/preprocessing | Use now |
| **zipfile (stdlib)**| Office XML (docx, xlsx, pptx) | Yes | Low | None | No | XML | Office | Yes (via XML parsing) | XML string | Shape/Textbox fallback | Use now |

## Summary
The heavy all-in-one libraries (`docling`, `unstructured`, `markitdown`) are not currently installed. To avoid introducing heavy dependencies, risk, and massive refactors for P1, we will rely on standard lightweight Python libraries.

We can achieve strong Excel and PPTX extraction by combining `openpyxl`/`python-pptx` with standard library `zipfile` parsing (to extract `<a:t>` tags from `xl/drawings/drawing*.xml` for Excel shapes and text boxes). PDF extraction already exists via PyMuPDF (`fitz`), and we will defer `PyMuPDF4LLM` for now.
