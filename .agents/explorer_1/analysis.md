# MOM Document Inventory, Parsers, Local Indexing & Coverage: Forensic Code Audit

**Investigation Target**: AIOS_habbit MOM Document Inventory, Document Extractors/Parsers, Local Index, and Coverage Components.  
**Auditor**: explorer_1  
**Timestamp**: 2026-08-20T06:33:00+07:00  
**Status**: COMPLETE

---

## 1. Executive Summary

This forensic investigation audited the codebase of `AIOS_habbit` to determine whether the MOM document processing pipeline (`real_doc_inventory.py`, `mom_local_index.py`, `mom_coverage.py`, `document_extractors.py`, `excel_extractors.py`, `deep_document_parsers.py`, `ocr_engines.py`) executes genuine document extraction, dynamic coverage calculation, and standard local search, or whether it relies on mock data, synthetic file stubs, or hardcoded answers.

### Key Forensic Findings:
1. **Document Parsers & Extractors** ([GENUINE]):
   - The system implements real, comprehensive local extraction pipelines for **PDF** (`pdf_inspector`, `fitz`/PyMuPDF, `docling`, `marker`, `pymupdf4llm`), **Word DOCX** (native OOXML XML parsing via `zipfile` and `xml.etree.ElementTree`), **PowerPoint PPTX** (native OOXML XML parsing via `zipfile`), **Excel XLSX/XLSM/XLS** (`openpyxl`, `xlrd`, DrawingML shapes, embedded chart metadata, and embedded images), **HTML** (`HTMLParser`), and **Images/OCR** (`RapidOCR` with ONNX, `PaddleOCR`, `pytesseract` with multi-pass image preprocessing).
   - No mock data or fake parser stubs are used in the core extraction libraries.
2. **Document Inventory (`real_doc_inventory.py`)** ([GENUINE]):
   - Recursively walks disk directories using `Path.rglob("*")`, verifies filesystem metadata (`stat.st_size`, `stat.st_mtime`), and computes streaming SHA-256 hashes (`_sha256_short`).
   - Minor dead-code defect in `_support_reason` (lines 77-80) due to prior inclusion in `SUPPORTED_EXTS`.
3. **Coverage Engine (`mom_coverage.py`)** ([GENUINE / DYNAMIC]):
   - Evaluates coverage dynamically from actual extracted chunk statuses (`extracted_success`, `extracted_partial`, `ocr_success`, `ocr_partial`, `unsupported_no_local_ocr`, `unsupported_no_local_tool`, `failed_with_reason`).
   - Supports formal governance exclusion audit through a JSON disposition ledger (`_load_dispositions`).
4. **MOM Local Index Storage & Embeddings (`mom_local_index.py`)** ([FLAT JSONL / NO EMBEDDINGS]):
   - `build_mom_local_index` extracts text chunks and serializes them to a JSON Lines file (`local_cases/mom_pilot/mom_local_index.jsonl`).
   - **No vector embeddings** (e.g. `sentence-transformers`, `ChromaDB`, `FAISS`, `sqlite-vec`) are generated or stored in `mom_local_index.py`. (Note: RAG v2 in `rag_v2/index.py` provides full SQLite FTS5 BM25 + BGE-M3 dense/sparse vectors + ColBERT multi-vector maxsim, but `mom_local_index.py` does not use it).
5. **MOM Local Search Retrieval (`mom_local_index.py`)** ([HARDCODED HEURISTICS / OVERFITTED RETRIEVAL]):
   - `search_mom_index` uses token frequency matching over JSONL chunks, but contains **explicit hardcoded terms and boosting heuristics specifically tailored for benchmark questions Q1, Q2, and Q3**.
   - Contains an explicit hardcoded **score penalty (`score -= 50.0`) targeting a specific file (`erd_kho_van_new.html`)** on Q2 queries to prevent it from ranking high.

---

## 2. Component-by-Component Forensic Audit

### 2.1. MOM Document Inventory (`src/aios_habit/real_doc_inventory.py`)
- **Classification**: `[GENUINE]`
- **Purpose**: Discovers and catalogs local files for MOM pilot, computing metadata, file types, SHA-256 hashes, duplicate detection, and format support reasons.

#### Code Evidence:
- **Real Filesystem Traversal & Streaming SHA-256**:
  - `src/aios_habit/real_doc_inventory.py:55-65`:
    ```python
    def _sha256_short(path: Path, max_bytes: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            remaining = max_bytes
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()[:16]
    ```
  - `src/aios_habit/real_doc_inventory.py:68-72`:
    ```python
    def _iter_files(root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if path.is_file():
                yield path
    ```
  - `src/aios_habit/real_doc_inventory.py:113-136`:
    ```python
    for file_path in sorted(_iter_files(root_resolved), key=lambda p: str(p).lower()):
        try:
            rel = file_path.relative_to(root_resolved).as_posix()
            ext = file_path.suffix.lower() or "[no_ext]"
            stat = file_path.stat()
            sha = _sha256_short(file_path)
            supported, reason = _support_reason(ext)
            ...
            item = MomFileInventoryItem(
                relative_path=rel,
                file_type=ext,
                size_bytes=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                sha256_short=sha,
                supported=supported,
                unsupported_reason=reason,
            )
            items.append(item)
    ```

#### Technical Defect / Caveat:
- `src/aios_habit/real_doc_inventory.py:74-82`:
  ```python
  def _support_reason(ext: str) -> tuple[bool, str]:
      if ext in SUPPORTED_EXTS:
          return True, ""
      if ext in {".pdf"}:
          return False, "pdf extraction dependency not available"
      if ext in {".docx", ".doc"}:
          return False, "docx/doc extraction dependency not available"
      return False, "unsupported file type"
  ```
  Because `SUPPORTED_EXTS` (line 20) is defined as `SUPPORTED_TEXT_EXTS | SUPPORTED_TABLE_EXTS | SUPPORTED_DOC_EXTS | SUPPORTED_PDF_EXTS | SUPPORTED_IMAGE_EXTS`, `.pdf` and `.docx` are already present in `SUPPORTED_EXTS`. Therefore, line 75 returns `True, ""` for `.pdf` and `.docx`, making lines 77-80 unreachable dead code.

---

### 2.2. MOM Document Extractors & Parsers (`src/aios_habit/document_extractors.py`, `excel_extractors.py`, `deep_document_parsers.py`, `ocr_engines.py`)
- **Classification**: `[GENUINE]`
- **Purpose**: Multi-format extraction covering PDF, Word, Excel, PowerPoint, HTML, Text, and OCR images.

#### Format-by-Format Evidence:

#### A. PDF Extraction (`document_extractors.py` & `deep_document_parsers.py`)
- **Libraries Used**: `pdf_inspector`, `fitz` (PyMuPDF), `pymupdf4llm`, `docling`, `marker` (`marker_single`), `PIL` (Pillow).
- **Implementation**:
  - `src/aios_habit/document_extractors.py:96-147`: `route_pdf_pages` attempts `pdf_inspector.extract_pages_markdown(path)` first.
  - `src/aios_habit/document_extractors.py:118-146`: If a page is flagged as `needs_ocr`, PyMuPDF (`fitz.open()`) attempts native text rescue first (`document[page_num].get_text("text")`).
  - `src/aios_habit/document_extractors.py:151-189`: Fallback to native PyMuPDF page-by-page extraction if `pdf_inspector` is unavailable.
  - `src/aios_habit/document_extractors.py:686-713`: In deep OCR modes (`deep`, `offline_max`, `auto_deep`), calls `run_deep_parser` from `deep_document_parsers.py`.
  - `src/aios_habit/deep_document_parsers.py:43-92`: Real IBM `docling` pipeline invocation (`DocumentConverter`, `PdfPipelineOptions`, `AcceleratorOptions` with CPU threading).
  - `src/aios_habit/deep_document_parsers.py:94-134`: Real `marker` CLI invocation (`marker_single`).
  - `src/aios_habit/document_extractors.py:750-787`: For scanned/image PDF pages without native text, renders high-resolution pixmap at 2x scale (`page.get_pixmap(matrix=fitz.Matrix(2, 2))`), converts to PIL RGB Image, and passes to local OCR engine (`_ocr_image_object`).

#### B. Word DOCX Extraction (`document_extractors.py`)
- **Libraries Used**: Standard library `zipfile`, `xml.etree.ElementTree`.
- **Implementation**:
  - `src/aios_habit/document_extractors.py:475-502`:
    ```python
    def _extract_docx(path: Path) -> ExtractionResult:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                names = ["word/document.xml"]
                names.extend(sorted(n for n in archive.namelist() if re.fullmatch(r"word/(header|footer)\d+\.xml", n, flags=re.IGNORECASE)))
                sections: list[str] = []
                for name in names:
                    root = _xml_root_from_zip(archive, name)
                    if root is None:
                        continue
                    lines: list[str] = []
                    for child in root.iter():
                        local = _xml_local_name(child.tag)
                        if local in {"p", "tbl"}:
                            text = _text_nodes(child)
                            if text:
                                lines.append(text)
                    clean = _clean_lines(lines, limit=300)
                    if clean:
                        label = "Document" if name == "word/document.xml" else Path(name).stem
                        sections.append(f"{label}:\n" + "\n".join(clean))
        except zipfile.BadZipFile:
            return ExtractionResult("", ".docx", "docx_zip_xml", "failed_with_reason", "invalid docx zip container")
    ```
  - Parses real OOXML XML structures (`word/document.xml`, header/footer XMLs), extracts text nodes (`<w:t>`), handles tables (`tbl`) and paragraphs (`p`). Zero mock or dummy data.

#### C. PowerPoint PPTX Extraction (`document_extractors.py`)
- **Libraries Used**: Standard library `zipfile`, `re`, `html`.
- **Implementation**:
  - `src/aios_habit/document_extractors.py:330-364`: `_extract_pptx` opens PPTX container via `zipfile.ZipFile`, reads `ppt/slides/slide*.xml` and `ppt/notesslides/notesSlide*.xml`, extracts text from `<a:t>` tags, counts embedded media files (`ppt/media/`), and formats output with slide text and speaker notes.

#### D. Excel XLSX / XLSM / XLS Extraction (`excel_extractors.py`)
- **Libraries Used**: `openpyxl`, `xlrd`, `zipfile`, `PIL` (Pillow).
- **Implementation**:
  - `src/aios_habit/excel_extractors.py:312-389`: `_extract_openpyxl` opens workbook, iterates through sheets up to `max_sheets` (12), extracts cell values up to `max_rows_per_sheet` (1000) and `max_non_empty_cells` (20000).
  - `src/aios_habit/excel_extractors.py:195-241`: `_regions` segments tables, detects merged cells (`sheet.merged_cells.ranges`), and identifies hierarchical multi-row headers (`_header_depth` lines 164-177).
  - `src/aios_habit/excel_extractors.py:350-356`: Extracts chart series, titles, and cell references (`sheet._charts`).
  - `src/aios_habit/excel_extractors.py:357-377`: Extracts embedded images (`sheet._images`), enforces image byte/pixel guards, and runs OCR on embedded diagrams (`document_extractors.py:413-447`).
  - `src/aios_habit/document_extractors.py:449-468`: Parses DrawingML XML text boxes and shapes (`xl/drawings/drawing*.xml`) from the zip container so floating text boxes are not lost.
  - `src/aios_habit/excel_extractors.py:403-443`: `_extract_xls` provides legacy binary Excel support via `xlrd`.

#### E. HTML Extraction (`document_extractors.py`)
- **Libraries Used**: Standard library `html.parser.HTMLParser`.
- **Implementation**:
  - `src/aios_habit/document_extractors.py:192-235`, `320-328`: `_ReadableHTMLParser` ignores `<script>`, `<style>`, and `<noscript>`, unescapes HTML entities, handles block breaks (`p`, `div`, `li`, `tr`, `h1`-`h6`), and dedupes repetitive lines.

#### F. Image OCR & Preprocessing (`ocr_engines.py` & `document_extractors.py`)
- **Libraries Used**: `rapidocr` + `onnxruntime`, `paddleocr` + `paddle`, `pytesseract` + Tesseract executable, `PIL` (Pillow).
- **Implementation**:
  - `src/aios_habit/ocr_engines.py:89-138`: `run_rapidocr` executes RapidOCR with ONNX runtime on CPU.
  - `src/aios_habit/ocr_engines.py:140-213`: `run_paddleocr` executes PaddleOCR with MKLDNN on CPU.
  - `src/aios_habit/ocr_engines.py:215-249`: `run_ocr_router` executes configured engine order with quality gates.
  - `src/aios_habit/document_extractors.py:542-558`: `_ocr_preprocessing_attempts` generates multiple deterministic image transformations (original, grayscale autocontrast upscale at PSM 3/6/11, sharpened contrast at PSM 11).
  - `src/aios_habit/document_extractors.py:651-664`: Rejects low-confidence OCR results below threshold (35.0) and assigns `ocr_partial` (35-60) vs `ocr_success` (>=60).

---

### 2.3. MOM Local Indexing & Vector Storage (`src/aios_habit/mom_local_index.py`)
- **Classification**: `[HYBRID / HEURISTIC STORAGE & RETRIEVAL]`
- **Purpose**: Builds a local search index over MOM documents for Q&A prompt generation and case creation.

#### How the Index is Built:
- `src/aios_habit/mom_local_index.py:218-279` (`build_mom_local_index`):
  - Traverses directory, computes SHA-256 for each file.
  - Direct text parsing for `.txt`, `.md`, `.markdown`, `.json` (line 243).
  - CSV parsing via `csv.reader` (line 247).
  - Excel parsing via `pandas.ExcelFile` and `pd.read_excel` (line 251).
  - Advanced parsing for other formats via `_extractor_chunks` delegating to `document_extractors.extract_text_chunks_from_file` (line 253).
  - Chunks text into 1200-character segments (`CHUNK_SIZE = 1200`, `MAX_CHUNKS_PER_FILE = 30`).
  - Serializes chunks to JSON Lines format at `local_cases/mom_pilot/mom_local_index.jsonl` (line 265-268).

#### Vector Embeddings Assessment:
- **Zero Vector Embeddings in `mom_local_index.py`**:
  - The index is strictly flat JSONL lines of text chunks (`MomChunk` records: chunk_id, source_file, relative_path, file_type, text, preview, privacy_level, source_hash, metadata).
  - No vector embeddings, vector databases (ChromaDB, FAISS, Milvus), or vector SQLite extensions (sqlite-vec) are used.
  - Search relies on in-memory linear iteration through the JSONL file (`load_mom_chunks(index_path)`).

#### Retrieval Mechanism & Hardcoded Overfitting Audit:
- `src/aios_habit/mom_local_index.py:297-392` (`search_mom_index`):
  - In `search_mom_index`, there is a basic token frequency counter (`haystack.count(term)` lines 324-330).
  - However, the function contains **explicit hardcoded term lists and specialized boosting logic targeting benchmark questions Q1, Q2, and Q3**:
  
  **Code Evidence (Lines 304-367)**:
  ```python
  304:     # Q1 target terms (MES/MOM comparison)
  305:     q1_terms = ["mes", "mom", "mes_mom", "momデータ連携", "実行", "製造", "traceability", "scheduling", "quality", "inventory"]
  306:     # Q2 target terms (Production History system)
  307:     q2_terms = ["生産履歴", "着完工", "ラインアウト", "復帰登録", "修理内容入力", "部品供給停止", "再開登録", "工程在庫修正", "戻入", "分割入庫", "製造人員登録"]
  308:     # Q3 target terms (Manual Shipping Excel metadata)
  309:     q3_terms = ["manualshipping_existinglineauto_inbounddownload", "item_code", "item_rev", "sup_line", "process_id", "oricon_id", "containername", "kdcrenameshipchangeqty"]
  310: 
  311:     # Detect query intents
  312:     query_has_q1 = any(t in q for t in q1_terms)
  313:     query_has_q2 = any(t in q for t in q2_terms)
  314:     query_has_q3 = any(t in q for t in q3_terms)
  ```

  **Q1 Query Boosts (Lines 332-340)**:
  ```python
  333:             if query_has_q1:
  334:                 matched_q1 = [term for term in q1_terms if term in haystack]
  335:                 if matched_q1:
  336:                     score += 15.0 * len(matched_q1)
  337:                 if chunk.file_type == ".pdf":
  338:                     score += 10.0
  339:                 if any(k in chunk.source_file.lower() for k in ["mes", "mom"]):
  340:                     score += 15.0
  ```

  **Q2 Query Boosts & Targeted Penalty against `erd_kho_van_new.html` (Lines 342-356)**:
  ```python
  343:             if query_has_q2:
  344:                 matched_q2 = [term for term in q2_terms if term in haystack]
  345:                 if matched_q2:
  346:                     score += 15.0 * len(matched_q2)
  347:                 if chunk.file_type == ".pdf":
  348:                     score += 10.0
  349:                 if any(k in chunk.source_file.lower() for k in ["生産履歴", "着完工", "仕様"]):
  350:                     score += 15.0
  351: 
  352:                 # Targeted Penalty for ERD_Kho_Van_NEW.html on Q2 queries
  353:                 if "erd_kho_van_new.html" in chunk.relative_path.lower():
  354:                     has_exact_q2_terms = any(term in haystack for term in q2_terms)
  355:                     if not has_exact_q2_terms:
  356:                         score -= 50.0
  ```

  **Q3 Query Boosts (Lines 358-366)**:
  ```python
  359:             if query_has_q3:
  360:                 matched_q3 = [term for term in q3_terms if term in haystack]
  361:                 if matched_q3:
  362:                     score += 20.0 * len(matched_q3)
  363:                 if chunk.file_type in {".xlsx", ".xlsm"}:
  364:                     score += 10.0
  365:                 if any(k in chunk.source_file.lower() or k in chunk.sheet.lower() for k in ["manual", "ship"]):
  366:                     score += 15.0
  ```

- **Forensic Assessment of Heuristics**:
  - While real document texts are being matched, the scoring algorithm has been explicitly manually hand-tuned (overfitted) to favor specific file names and file types for benchmark questions Q1, Q2, and Q3, and explicitly suppresses a competing file (`erd_kho_van_new.html`) via a hardcoded penalty of `-50.0`.
  - In a generalized enterprise production environment, such hardcoded question-specific term boosts and hardcoded file penalties will not generalize to arbitrary queries.

---

### 2.4. MOM Coverage Engine (`src/aios_habit/mom_coverage.py`)
- **Classification**: `[GENUINE / DYNAMIC]`
- **Purpose**: Computes document inventory extraction coverage, tracking extraction success, OCR rates, unsupported reasons, and approved exclusions.

#### Code Evidence:
- `src/aios_habit/mom_coverage.py:100-169`:
  - Scans files in root directory dynamically:
    ```python
    corpus_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if root.exists() and path.is_file()
    }
    ```
  - Calls `build_mom_local_index(root)` (line 107) to extract all files.
  - Aggregates chunk statuses into buckets (`extracted_success`, `extracted_partial`, `ocr_success`, `ocr_partial`, `unsupported_no_local_ocr`, `unsupported_no_local_tool`, `failed_with_reason`) (lines 84-97, 116-120).
  - Loads owner disposition ledger (`_load_dispositions`, lines 51-82) to reconcile approved exclusions.
  - Dynamically calculates:
    - `usable_files = len(usable_paths)` (line 139)
    - `usable_coverage_percent = round((usable_files / total_files * 100.0) if total_files else 100.0, 2)` (line 148)
    - `ocr_chunks_count`, `docx_chunks_count`, `png_ocr_chunks_count`, `pdf_ocr_chunks_count` (lines 154-157)
    - `disposition_coverage_percent` (line 163)
    - `strict_passed = not unresolved and not disposition_errors and unknown_unsupported == 0` (line 164)
- **Verdict**: Coverage calculation is completely dynamic and accurately reflects the underlying extraction state of the corpus.

---

### 2.5. Fake Test Assets Audit (`local_cases/` & `data/`)
- **Classification**: `[TEST FIXTURES / MOCKS]`
- **Observation**:
  - In `local_cases/notebook_assets/NB-MOM-GL/`:
    - `1782010574484_8973ee_mom_shipping_process_fake.md`: Line 10 contains: `Lưu ý: Đây là tài liệu giả để pilot AIOS, không phải tài liệu thật.`
    - `1782010574486_0a037e_u002_initialization_checklist_fake.csv`: Contains synthetic test checks (`CHK-001, DHCP setting, initialized by U002`).
    - `1782010574501_508748_entity_settings_glossary_fake.txt`: Contains synthetic glossary.
  - In `local_cases/assets/CASE-MOM-PL-1/`:
    - `polarisnext_shipping_config_mismatch_fake.csv`: Synthetic CSV mismatch fixture.
  - In `tailieugoc/`:
    - Contains 82 **real, authentic Japanese & Vietnamese manufacturing specifications** (`MES_MOM説明資料_20251031.pdf`, `MOMデータ連携説明_20251220.pdf`, `マテコン操作手順書_v001_生産技術 TV.pdf`, `生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf`, etc.).
- **Verdict**: Fake files exist solely in `local_cases/` as pilot unit test fixtures. The real production dataset resides in `tailieugoc/` and contains genuine complex multi-lingual enterprise documents.

---

## 3. Comparative Architecture: `mom_local_index` vs `rag_v2`

| Dimension | MOM Local Index (`mom_local_index.py`) | RAG Engine v2 (`rag_v2/index.py` & `rag_v2/chunking.py`) |
| :--- | :--- | :--- |
| **Storage Engine** | Flat JSON Lines file (`mom_local_index.jsonl`) | SQLite Database with WAL mode (`LocalChunkIndex`) |
| **Full-Text Search** | In-memory regex token scanning | SQLite FTS5 with BM25 ranking & CJK n-grams |
| **Dense Vector Embeddings** | None | BGE-M3 (512/1024d) via worker process/ONNX/PyTorch |
| **Sparse / Lexical Vectors** | None | Sparse lexical weights (`SparseVector`) |
| **Multi-Vector Retrieval** | None | ColBERT Late-Interaction MaxSim (`MultiVector`) |
| **Reranking** | None | Cross-Encoder Reranker (`RerankerBackend`) |
| **Query Planning & Fusion** | Hardcoded Q1/Q2/Q3 intent regex & bonus scores | Reciprocal Rank Fusion (RRF) + semantic floor filtering |
| **Query-Specific Overfitting**| **YES** (`q1_terms`, `q2_terms`, `q3_terms`, `-50.0` penalty on `erd_kho_van_new.html`) | **NO** (General query planning & facet matching) |
| **Production Readiness** | Prototype / Benchmark Pilot Only | Near-Production Grade Hybrid Retrieval |

---

## 4. Synthesis of Forensic Answers

| Forensic Question | Code Finding | Classification |
| :--- | :--- | :--- |
| **1. Does the system parse real files (PDF, DOCX, XLSX, TXT, OCR)? What libraries are used?** | Yes. PDF uses `fitz` (PyMuPDF), `pdf_inspector`, `docling`, `marker`. DOCX & PPTX use native OOXML XML parsing (`zipfile`, `ElementTree`). Excel uses `openpyxl` & `xlrd` with merged cell, chart, and embedded image extraction. OCR uses `rapidocr` (ONNX), `paddleocr`, `pytesseract`. | `[GENUINE]` |
| **2. Is there hardcoding, mock data, or synthetic files disguised as real parsing?** | Parsers are real. Test fixtures in `local_cases/` are explicitly marked `_fake`. However, `mom_local_index.py:304-367` contains hardcoded terms and heuristic boosts for Q1, Q2, Q3, and a `-50.0` penalty against `erd_kho_van_new.html`. | `[HYBRID / HEURISTIC]` |
| **3. How is the local index built? Does it use real embeddings or hardcoded dictionaries?** | It extracts text chunks to a JSONL flat file. It does **not** generate or store vector embeddings. Search is a linear scan with regex token count and hardcoded benchmark heuristic score boosts. (Contrast with `rag_v2`, which has full BM25 + dense/sparse/ColBERT vectors). | `[FLAT JSONL / NO EMBEDDINGS]` |
| **4. How does `mom_coverage.py` calculate coverage? Is it dynamic or hardcoded?** | It is 100% dynamic. It walks the filesystem, checks extractor statuses for every file, calculates percentage ratios, and validates against a governance disposition ledger. | `[GENUINE / DYNAMIC]` |
