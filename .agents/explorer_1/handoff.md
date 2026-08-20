# Handoff Report: MOM Document Inventory, Extractors, Local Index & Coverage

- **Agent**: explorer_1
- **Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\explorer_1`
- **Parent Conversation ID**: `1f8ede27-4c01-427f-b899-9b9b6eaebec7`
- **Handoff Type**: Hard (Investigation Complete)
- **Target Task**: Forensic Code Audit of MOM Document Inventory, Parsers/Extractors, Local Indexing, and Coverage components.

---

## 1. Observation

### 1.1 Document Parsers and Extraction Libraries
1. **PDF Parser** (`src/aios_habit/document_extractors.py:96-190`, `715-804`, `deep_document_parsers.py:43-134`):
   - `route_pdf_pages` (lines 96-190) attempts `pdf_inspector.extract_pages_markdown`, rescues text via `fitz` (PyMuPDF `document[page_num].get_text("text")`), and falls back to `pymupdf4llm` or native `fitz.open()`.
   - `_deep_pdf_result` (lines 686-713) calls `deep_document_parsers.run_deep_parser` (`docling.document_converter.DocumentConverter` or `marker_single` CLI).
   - Scanned PDF pages render to pixmap via `page.get_pixmap(matrix=fitz.Matrix(2, 2))` (line 772) and execute OCR via `_ocr_image_object` (line 776).
2. **Word DOCX Parser** (`src/aios_habit/document_extractors.py:475-502`):
   - `_extract_docx` uses standard library `zipfile.ZipFile` to parse `word/document.xml`, `word/header*.xml`, `word/footer*.xml` with `xml.etree.ElementTree`, extracting paragraphs `<w:p>` and tables `<w:tbl>` via text nodes `<w:t>`. No mock/stub text.
3. **PowerPoint PPTX Parser** (`src/aios_habit/document_extractors.py:330-364`):
   - `_extract_pptx` opens PPTX container via `zipfile.ZipFile`, parses `ppt/slides/*.xml` and `ppt/notesslides/*.xml` for `<a:t>` tags, and counts embedded media files (`ppt/media/`).
4. **Excel XLSX / XLSM / XLS Parser** (`src/aios_habit/excel_extractors.py:312-389`, `403-443`):
   - `_extract_openpyxl` uses `openpyxl.load_workbook(BytesIO(data))` to read sheets up to 12 (`max_sheets`), rows up to 1000 (`max_rows_per_sheet`), and cells up to 20000 (`max_non_empty_cells`).
   - Identifies merged cell ranges (`sheet.merged_cells.ranges`), header depth (`_header_depth` lines 164-177), chart series/titles (`sheet._charts` lines 350-356), and embedded images (`sheet._images` lines 357-377).
   - `document_extractors.py:449-468` parses DrawingML text boxes (`xl/drawings/drawing*.xml`).
   - `_extract_xls` (lines 403-443) uses `xlrd.open_workbook` for legacy binary `.xls`.
5. **HTML Parser** (`src/aios_habit/document_extractors.py:192-235`, `320-328`):
   - `_ReadableHTMLParser` uses standard `html.parser.HTMLParser`, filters out `<script>`, `<style>`, `<noscript>`, converts tags to line breaks, and dedupes repetitive lines.
6. **OCR Engines** (`src/aios_habit/ocr_engines.py:89-249`, `document_extractors.py:542-664`):
   - Supports `RapidOCR` with `onnxruntime` (`run_rapidocr`, lines 89-138), `PaddleOCR` with `paddle` (`run_paddleocr`, lines 140-213), and `Tesseract` (`_run_tesseract_engine`, `document_extractors.py:560-620`).
   - Multi-profile preprocessing (`_ocr_preprocessing_attempts`, `document_extractors.py:542-558`) with PSM 3/6/11 and sharpening. Rejects confidence < 35.0 (line 651).

### 1.2 MOM Document Inventory (`src/aios_habit/real_doc_inventory.py`)
- `_sha256_short` (lines 55-65) streams file bytes to compute real 16-char SHA-256 prefixes.
- `_iter_files` (lines 68-72) calls `root.rglob("*")`.
- `scan_mom_inventory` (lines 84-162) gathers file statistics (`stat.st_size`, `stat.st_mtime`), maps duplicates, and outputs `MomInventory`.
- `_support_reason` (lines 74-82) has dead code on lines 77-80 because `.pdf` and `.docx` are already included in `SUPPORTED_EXTS` (line 20).

### 1.3 MOM Local Index Storage & Embeddings (`src/aios_habit/mom_local_index.py`)
- `build_mom_local_index` (lines 218-279) iterates through files in `root_path`, parses text via `_read_text_file`, `_read_csv_file`, `_excel_chunks` (pandas), or `_extractor_chunks` (`document_extractors`), and writes chunks to `local_cases/mom_pilot/mom_local_index.jsonl` (line 266).
- **Embeddings**: There are **no vector embeddings** generated or stored in `mom_local_index.py`. No `sentence-transformers`, `ChromaDB`, `FAISS`, or `sqlite-vec` are imported or called.
- `load_mom_chunks` (lines 281-294) reads chunks back from the flat JSONL file.

### 1.4 Hardcoded Retrieval Boosts and File Penalties (`src/aios_habit/mom_local_index.py`)
- In `search_mom_index` (lines 297-392):
  - **Lines 304-310**:
    ```python
    # Q1 target terms (MES/MOM comparison)
    q1_terms = ["mes", "mom", "mes_mom", "momデータ連携", "実行", "製造", "traceability", "scheduling", "quality", "inventory"]
    # Q2 target terms (Production History system)
    q2_terms = ["生産履歴", "着完工", "ラインアウト", "復帰登録", "修理内容入力", "部品供給停止", "再開登録", "工程在庫修正", "戻入", "分割入庫", "製造人員登録"]
    # Q3 target terms (Manual Shipping Excel metadata)
    q3_terms = ["manualshipping_existinglineauto_inbounddownload", "item_code", "item_rev", "sup_line", "process_id", "oricon_id", "containername", "kdcrenameshipchangeqty"]
    ```
  - **Lines 333-340 (Q1 boosts)**: `score += 15.0 * len(matched_q1)`, `+10.0` for `.pdf`, `+15.0` for filename containing "mes" or "mom".
  - **Lines 343-350 (Q2 boosts)**: `score += 15.0 * len(matched_q2)`, `+10.0` for `.pdf`, `+15.0` for filename containing "生産履歴", "着完工", "仕様".
  - **Lines 352-356 (Q2 explicit file penalty)**:
    ```python
    # Targeted Penalty for ERD_Kho_Van_NEW.html on Q2 queries
    if "erd_kho_van_new.html" in chunk.relative_path.lower():
        has_exact_q2_terms = any(term in haystack for term in q2_terms)
        if not has_exact_q2_terms:
            score -= 50.0
    ```
  - **Lines 359-366 (Q3 boosts)**: `score += 20.0 * len(matched_q3)`, `+10.0` for `.xlsx`/`.xlsm`, `+15.0` for filename/sheet containing "manual" or "ship".

### 1.5 MOM Coverage Calculation (`src/aios_habit/mom_coverage.py`)
- `summarize_mom_coverage` (lines 100-169) performs live filesystem enumeration (`root.rglob("*")`), calls `build_mom_local_index(root)`, classifies chunk statuses (`extracted_success`, `extracted_partial`, `ocr_success`, `ocr_partial`, `unsupported_no_local_ocr`, `unsupported_no_local_tool`, `failed_with_reason`), checks approved exclusions in `_load_dispositions`, and dynamically computes percentages. 100% dynamic calculation.

### 1.6 Data Assets Audit (`local_cases/` vs `tailieugoc/`)
- `local_cases/notebook_assets/NB-MOM-GL/` and `local_cases/assets/CASE-MOM-PL-1/` contain mock unit test files marked with `_fake` (e.g. `mom_shipping_process_fake.md` containing `Lưu ý: Đây là tài liệu giả để pilot AIOS, không phải tài liệu thật.`).
- `tailieugoc/` contains 82 authentic Japanese & Vietnamese manufacturing specifications (`MES_MOM説明資料_20251031.pdf`, `生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf`, etc.).

---

## 2. Logic Chain

1. **Extraction Reality**:
   - `document_extractors.py` and `excel_extractors.py` use industry-standard libraries (`fitz`/PyMuPDF, `openpyxl`, `xlrd`, `rapidocr`, `paddleocr`, `pytesseract`, `docling`, `marker`) and native OOXML XML unpacking for DOCX/PPTX.
   - Therefore, file extraction is **GENUINE** and handles real PDF, Excel, Word, PPTX, HTML, and images without synthetic mocking.
2. **Indexing Structure**:
   - `mom_local_index.py` stores extracted chunks as text lines in `mom_local_index.jsonl`.
   - Inspection of `mom_local_index.py` shows no embedding models, vector libraries, or vector databases.
   - Therefore, the MOM local index is a **flat JSONL keyword-searchable text index**, NOT a vector index.
3. **Retrieval Overfitting**:
   - `search_mom_index` in `mom_local_index.py:304-367` defines explicit term sets `q1_terms`, `q2_terms`, `q3_terms`, grants heavy artificial bonuses (`+15.0` to `+20.0`), and applies a `-50.0` score deduction to `erd_kho_van_new.html`.
   - Therefore, retrieval ranking in `mom_local_index.py` is **HEURISTICALLY OVERFITTED** to pass benchmark questions Q1, Q2, and Q3.
4. **Coverage Integrity**:
   - `mom_coverage.py` calculates file counts, usable ratios, and OCR counts directly from `len(corpus_files)` and `file_status`.
   - Therefore, coverage calculation is **GENUINE and DYNAMIC**.

---

## 3. Caveats

- Benchmark evaluation execution scripts (`mom_benchmark.py`, `mom_benchmark_gate.py`, `battle_notebooklm_rag_v2.py`) are under the scope of explorer_2 and explorer_3 and were only cross-referenced for data flow.
- The `rag_v2` subsystem (`src/aios_habit/rag_v2/index.py`, `chunking.py`, `retrieval_backends.py`) contains a separate, production-grade SQLite FTS5 + BGE-M3 dense/sparse/ColBERT vector engine that does NOT suffer from the hardcoded Q1/Q2/Q3 boosts of `mom_local_index.py`.

---

## 4. Conclusion

| Component | Forensic Classification | Production Readiness Assessment |
| :--- | :--- | :--- |
| **Document Extractors (`document_extractors.py`, `excel_extractors.py`)** | `[GENUINE]` | **Ready for Production**: Excellent multi-format parsing, merged cell and table structure extraction, drawing text box support, and multi-profile OCR. |
| **Document Inventory (`real_doc_inventory.py`)** | `[GENUINE]` | **Ready for Production**: Reliable recursive file scanning and streaming SHA-256 duplicate detection. Minor dead code in `_support_reason` should be cleaned up. |
| **Coverage Engine (`mom_coverage.py`)** | `[GENUINE / DYNAMIC]` | **Ready for Production**: Dynamic metrics, governance ledger support, strict coverage verification. |
| **MOM Local Index (`mom_local_index.py`)** | `[FLAT JSONL / NO EMBEDDINGS]` | **Prototype Only / Overfitted**: Search is hardcoded for Q1/Q2/Q3 and applies artificial score penalties against `erd_kho_van_new.html`. Must migrate to `rag_v2` (`LocalChunkIndex` with FTS5 BM25 + BGE-M3 embeddings) for production. |

---

## 5. Verification Method

To independently verify all claims made in this report:

1. **Verify Document Parsers & OCR on Synthetic Data**:
   ```bash
   pytest tests/test_mom_local_pilot.py -k "test_document_extractor or test_inventory_scan"
   ```
2. **Inspect Hardcoded Term Boosts & Penalties in `mom_local_index.py`**:
   - Inspect `src/aios_habit/mom_local_index.py:304-310` for `q1_terms`, `q2_terms`, `q3_terms`.
   - Inspect `src/aios_habit/mom_local_index.py:352-356` for the `-50.0` penalty on `erd_kho_van_new.html`.
3. **Verify Coverage Dynamic Calculation**:
   ```bash
   pytest tests/test_mom_local_pilot.py -k "test_mom_coverage_summary or test_strict_corpus_audit"
   ```
4. **Inspect RAG v2 Contrast**:
   - Inspect `src/aios_habit/rag_v2/index.py:689-800` (`LocalChunkIndex`) to verify SQLite FTS5 BM25 and vector embedding tables.
