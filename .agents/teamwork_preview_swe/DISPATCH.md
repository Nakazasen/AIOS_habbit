## 2026-08-21T09:49:45Z

Add a local folder document batch import feature to AIOS Habit Workspace Chat, allowing users to enter a directory path on their machine to scan and ingest all supported documents (.pdf, .docx, .xlsx, .xls, .pptx, .txt, .md, .csv, images) into a notebook or conversation in one click.

Requirements:
- R1. Local Directory Scanner & Validator: backend utility to scan a local folder path for supported document formats (with optional recursive subfolder scan), reporting total file count, supported vs unsupported files, and total size. Validate security and path existence.
- R2. Workspace Chat UI Integration: Add "📁 Nhập từ thư mục" (Import from Folder) option inside "Thêm nguồn" (Add Sources) in `src/aios_habit/workspace_chat_app.py`. Include path input field, "Quét thư mục" (Scan Folder) button with preview table/list, and "Nhập tất cả tài liệu vào sổ" (Ingest All) button. Privacy level settings and progress bar / status summary.
- R3. Batch Ingestion Execution & Error Resilience: Process files sequentially or in bounded batches through existing extraction and storage pipeline (`source_ingest.py` / `workspace_chat_store.py`). Gracefully handle corrupted or locked files.
- Automated tests covering directory scanning, validation, and batch ingestion.
