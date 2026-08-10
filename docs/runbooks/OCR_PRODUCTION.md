# OCR Production Runbook

## Pipeline

```text
PDF Inspector → PyMuPDF native rescue → RapidOCR
                                      → PaddleOCR (optional)
                                      → Tesseract (emergency only)

deep / auto_deep → Docling CPU
offline_max       → Marker CPU → Docling fallback
```

BGE-M3 Hybrid retrieval is unchanged. Every OCR/deep parser is local-only.
Models are loaded lazily and engines run sequentially to avoid 16 GB RAM exhaustion.

## Install tiers

```powershell
# Recommended laptop profile: PDF Inspector + RapidOCR/ONNX CPU
.\.venv\Scripts\python.exe -m pip install -e ".[rag-ingestion-cpu]"

# Optional PaddleOCR fallback (large)
.\.venv\Scripts\python.exe -m pip install -e ".[ocr-paddle-cpu]"

# Optional Docling deep parser
.\.venv\Scripts\python.exe -m pip install -e ".[document-deep-cpu]"

# Optional Marker + Docling maximum offline profile (largest)
.\.venv\Scripts\python.exe -m pip install -e ".[document-offline-max]"
```

Do not install PaddleOCR or Marker on the default laptop profile unless benchmark data
shows that RapidOCR is insufficient.

## Runtime modes

Set `AIOS_OCR_MODE` before ingestion:

| Mode | Behavior | Laptop recommendation |
|---|---|---|
| `fast` | RapidOCR only | Lowest latency/RAM |
| `balanced` | RapidOCR → PaddleOCR → Tesseract | **Default** |
| `auto_deep` | Docling only for table/column PDFs; otherwise balanced | Structured corpora |
| `deep` | Docling for every PDF; lightweight fallback on failure | Manual opt-in |
| `offline_max` | Marker → Docling | Workstation/batch only |
| `legacy` | Tesseract only | Emergency rollback |

PowerShell example:

```powershell
$env:AIOS_OCR_MODE = "balanced"
$env:AIOS_OCR_CPU_THREADS = "4"
$env:AIOS_MAX_PDF_OCR_PAGES = "3"
$env:AIOS_DEEP_PARSE_TIMEOUT_SECONDS = "300"
```

`AIOS_OCR_ENGINE_ORDER` can override the balanced order, for example
`rapidocr,tesseract`. Invalid names are ignored.

## Benchmark gate

Render representative PDF pages to images, including native Vietnamese, scans,
rotations, tables and low-resolution pages. Then run engines sequentially:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_ocr_engines.py .\benchmark-pages `
  --engines rapidocr,paddleocr --threads 4 --output .\ocr_benchmark.jsonl
```

Review exact text accuracy against human ground truth in addition to confidence and
latency. Promote PaddleOCR only if its measured accuracy gain justifies installation
size and memory use. Never benchmark multiple engines concurrently on a 16 GB laptop.

## Failure behavior

- Missing optional engines never crash ingestion.
- Failed deep parsing falls back to PDF Inspector/PyMuPDF/RapidOCR.
- OCR text below the existing confidence gate is rejected.
- Only the configured maximum number of scanned pages is OCR'd per PDF.
- Provenance records the actual engine (`rapidocr`, `paddleocr`, `tesseract`,
  `docling-cpu`, or `marker-cpu`).

