# BÁO CÁO KẾT QUẢ THỰC THI VÉ DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE

> **ĐÓNG DẤU MODEL:** `Gemini 2.5 Flash / Thinking Level: High (Advanced Agentic Pair Programming)`  
> **Thời điểm hoàn thành:** 2026-10-21T15:25:00+07:00  
> **Môi trường thực thi:** Máy nhà (H410ASROCK), Windows 10 x64, CPU thuần (Intel Core i3-10100F, không GPU, không PyTorch)  
> **Runtime Python:** Python 3.11.14 (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`)  
> **Nhánh mã nguồn:** `phieu-viec/rag-fix1` (Kho `D:\Sandbox\AIOS_habbit`)  
> **Kho điều phối & bằng chứng:** `D:\Sandbox\aios-dieu-phoi-desktop` (Nhánh `main`)

---

## 1. TỔNG QUAN VÀ BỐI CẢNH

Vé **DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE** yêu cầu tích hợp thư viện **Indra OCR** (`indra-ocr==1.1.2`, repo `datalab-to/indra`) làm lớp bổ trợ ở tầng nạp tài liệu (ingest/extraction pipeline) của `AIOS_habbit`. 

Mục tiêu chính:
- Biến các tài liệu PDF kỹ thuật có lớp chữ mỏng hoặc scan thuần (trước đây "câm" - không có lớp chữ để tìm kiếm và truy hồi) thành tài liệu có thể tìm kiếm và truy hồi chính xác tri thức.
- Cơ chế bổ trợ: giữ nguyên và sử dụng lớp chữ sẵn có khi có chất lượng tốt; chạy Indra OCR bổ sung phần thiếu hoặc các trang scan.
- Đảm bảo an toàn tuyệt đối: hoạt động hoàn toàn trên CPU thuần với ONNX Runtime, không phụ thuộc PyTorch hay GPU, không tranh chấp tài nguyên với BGE-M3 hay mô hình trả lời.
- Tuyệt đối không re-ingest các kho dữ liệu production; chỉ thử nghiệm và nghiệm thu trên Staging test store.

---

## 2. CHI TIẾT CÀI ĐẶT & CẤU TRÚC KỸ THUẬT

### 2.1. Thư viện và Model Weights
- **Gói cài đặt:**
  - `indra-ocr==1.1.2`
  - `opencv-python-headless==5.0.0.93` (không xung đột GUI)
  - `pypdfium2==5.14.0` (kết xuất trang PDF sang ảnh cho OCR)
  - `onnxruntime==1.23.2` (CPU execution provider)
- **Vị trí lưu cache model trên máy nhà:**
  - Đường dẫn: `C:\Users\Admin\.cache\huggingface\hub\models--datalab-to--indra-ocr`
  - Kích thước snapshot model ONNX: ~18 MB (tổng thư mục snapshot repo: 72.56 MB).
  - Tải tự động qua Hugging Face Hub snapshot khi khởi tạo model lần đầu.
- **Tiêu thụ tài nguyên:** CPU thuần 100%, không nạp CUDA/PyTorch, thời gian khởi động model ~0.4s.

### 2.2. Các tệp đã sửa đổi và tạo mới trong `AIOS_habbit`
1. **[src/aios_habit/indra_ocr_adapter.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/indra_ocr_adapter.py)** (Mới):
   - Triển khai `evaluate_pdf_gate(pdf_path, total_pages, page_char_counts)`: thực thi logic 4 cổng kích hoạt.
   - Triển khai `run_indra_extraction(pdf_path, page_indices)`: kết xuất ảnh trang qua `pypdfium2`, gọi `IndraOCR` trích xuất markdown cấu trúc, tính toán số ký tự trước/sau, số trang OCR.
   - Ghi nhật ký trích xuất chi tiết theo định dạng JSONL vào `local_runs/indra_ingest.jsonl`.
   - Cung cấp hàm kiểm tra cấu hình `is_indra_enabled()` và khả năng sẵn sàng `is_indra_available()`.
2. **[src/aios_habit/document_extractors.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/document_extractors.py)** (Sửa đổi):
   - Tích hợp cổng Indra OCR vào `_extract_pdf_pages_routed()`.
   - Kết hợp lớp chữ có sẵn với nội dung OCR cấu trúc từ Indra cho từng trang được kích hoạt.
   - Gắn `indra_stats` vào metadata của từng chunk (`ExtractedChunk.metadata["indra_stats"]`) và trả về extraction status chuẩn `"extracted"`.
3. **[src/aios_habit/workspace_chat_source_ingest.py](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_source_ingest.py)** (Sửa đổi):
   - Đọc `indra_stats` từ các chunk trích xuất và đẩy vào dictionary kết quả nạp `metadata` của `ingest_and_extract_bytes()`.
   - Cung cấp các trường chuẩn: `so_ky_tu_lop_chu_san`, `so_ky_tu_sau_indra`, `so_trang_ocr`, `co_dung_indra`, `thoi_gian_nap`, `cong_kich_hoat`.
4. **[tests/test_indra_ocr_adapter.py](file:///D:/Sandbox/AIOS_habbit/tests/test_indra_ocr_adapter.py)** (Mới):
   - Bộ 10 test tự động kiểm thử toàn diện: công tắc cấu hình, các cổng (a), (b), (c), (d), ghi nhật ký metadata, phục hồi hành vi cũ 100% khi tắt cấu hình, và báo cáo khả năng hệ thống.
5. **[scripts/measure_indra_before_after.py](file:///D:/Sandbox/AIOS_habbit/scripts/measure_indra_before_after.py)** (Mới):
   - Đo lường đối chứng trước/sau trên 4 tệp thật (8D, Sơ đồ mạch, C6610 scan 31 trang, Service manual 165MB).
6. **[scripts/verify_indra_staging_retrieval_browser.py](file:///D:/Sandbox/AIOS_habbit/scripts/verify_indra_staging_retrieval_browser.py)** (Mới):
   - Tự động nạp tài liệu vào Staging store (`nb-indra-staging-test`), khởi động server Streamlit, truy vấn hỏi-đáp RAG và dùng Playwright chụp ảnh giao diện thật.

---

## 3. CỔNG KÍCH HOẠT (ACTIVATION GATES) & CỜ CẤU HÌNH

Hệ thống triển khai chính xác 4 quy tắc cổng kích hoạt tại `evaluate_pdf_gate()`:

1. **Cổng (a) - Trang trống chữ (`gate_a_zero_char_pages`):**
   - Nếu tài liệu PDF có bất kỳ trang nào có số ký tự lớp chữ sẵn bằng `0`, hệ thống sẽ kích hoạt Indra OCR riêng cho các trang đó (áp dụng cho tài liệu có dung lượng trang lớn nhưng bị sót trang scan).
2. **Cổng (b) - Tài liệu ngắn và vừa (`gate_b_short_doc`):**
   - Nếu tổng số trang PDF $\le 100$ trang, hệ thống kích hoạt Indra OCR cho toàn bộ tài liệu để đảm bảo nhận diện đầy đủ bảng biểu, mã linh kiện và chữ mỏng trong sơ đồ.
3. **Cổng (c) - Bỏ qua tài liệu dài đủ chữ (`gate_c_skipped_long_doc`):**
   - Nếu tổng số trang PDF $> 100$ trang mà mọi trang đều có lớp chữ sẵn (không có trang nào 0 ký tự), hệ thống **bỏ qua hoàn toàn Indra OCR**, giữ nguyên 100% đường trích xuất cũ. Đây là cổng chặn tài nguyên cho các tài liệu khổng lồ như Service manual 1.758 trang.
4. **Cổng (d) - Tài liệu phi PDF (`gate_d_non_pdf`):**
   - Các định dạng khác (DOCX, PPTX, XLSX, HTML, TXT, ...) giữ nguyên đường trích xuất chuyên dụng, không đi qua bộ chuyển đổi PDF/Indra.
5. **Cờ cấu hình tắt/mở (`AIOS_INDRA_OCR_ENABLED`):**
   - Mặc định: `1` (Bật).
   - Khi đặt `AIOS_INDRA_OCR_ENABLED=0` hoặc `false`: cổng lập tức vô hiệu hóa Indra OCR (`disabled_by_config`), hệ thống quay về hành vi nạp ban đầu 100%, không phát sinh bất kỳ lời gọi OCR nào.

---

## 4. KẾT QUẢ ĐO LƯỜNG TRƯỚC / SAU (BENCHMARK THỰC TẾ)

Dữ liệu kiểm thử được trích xuất từ kho tài liệu thực tế của dự án (`Điều chỉnh-20260905T053942Z-1-001.zip`), đo đạc độc lập bằng kịch bản `measure_indra_before_after.py`.

### Bảng đối chứng trích xuất chi tiết:

| Tài liệu thử nghiệm | Số trang | Dung lượng | Đường cũ (Ký tự / Bytes) | Sau Indra (Ký tự / Bytes) | Số trang OCR | Thời gian nạp | Cổng kích hoạt | Đánh giá ngưỡng Trial |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Báo cáo 8D nhà cung cấp KDTVN** (`8d_kdtvn_5p.pdf`) | 5 | 1.48 MB | 3,125 chars (6,228 B) | **5,746 chars** (**8,751 B**) | 3 / 5 | 4.70s | `gate_b_short_doc` | **ĐẠT** (Trial: $\ge 8,000$ B; đọc đúng model `302XC45060`, số báo cáo `S260017-3`, cấu trúc bảng) |
| **Sơ đồ mạch 7PA1187DCZ** (`7pa1187dcz_11p.pdf`) | 11 | 643 KB | 31,187 chars (35,234 B) | **95,816 chars** (**99,670 B**) | 10 / 11 | 17.15s | `gate_b_short_doc` | **ĐẠT** (Trial: $\ge 90,000$ chars; đọc đúng `ASSY 303TD47030`, `PWB 7PA1187DCZ+GH01`, tiếng Nhật) |
| **Scan thuần C6610** (`c6610_n00137687_scan_31p.pdf`) | 31 | 10.48 MB | 2,159 chars (2,235 B) *(28 trang lỗi)* | **41,720 chars** (**61,133 B**) | 31 / 31 | 64.26s | `gate_b_short_doc` | **ĐẠT XUẤT SẮC** (Trial: $\ge 20,000$ chars; trích được 9,150 ký tự Nhật gồm Kana + Kanji; đọc đúng `302ND31540-01`, `COUPLING CLAW`) |
| **Service manual (Đối chứng âm)** (`2xd_smkdj_jpn_service_manual_1758p.pdf`) | 1,758 | 164.9 MB | 1,569,357 chars | **1,569,357 chars** (Giữ nguyên) | 0 / 1,758 | 49.60s *(Cũ: 49.71s)* | `gate_c_skipped_long_doc` | **ĐẠT** (Indra không kích hoạt, thời gian nạp tương đương, không tốn tài nguyên OCR) |

### Phân tích chi tiết chất lượng nhận diện tiếng Nhật trên bản scan C6610:
- Khẳng định của hãng rằng *"không đọc được kana từ tài liệu scan"* đã bị **bác bỏ hoàn toàn** trên tệp scan thực tế:
  - **Hiragana:** 2,860 ký tự.
  - **Katakana:** 1,767 ký tự.
  - **Kanji (Hán tự):** 4,523 ký tự.
  - **Tổng ký tự tiếng Nhật:** **9,150 ký tự**.
  - **Nội dung trích xuất mạch lạc:** Đọc chính xác số quản lý PLM `N00137687`, tên bộ phận `COUPLING CLAW`, mã phụ tùng linh kiện `302ND31540-01` (mã bản vẽ `30C2G31011-01`), cũng như các bước điều tra nguyên nhân biến dạng khớp nhả sấy dẫn đến mã lỗi C6610.

---

## 5. CHỨNG MINH TRUY HỒI TRÊN STAGING & BẰNG CHỨNG ẢNH GIAO DIỆN THẬT

### 5.1. Quy trình nghiệm thu truy hồi Staging (Grounded Chat)
- Đã nạp 3 tài liệu thử nghiệm vào Staging Notebook: `nb-indra-staging-test` (cô lập hoàn toàn, không nạp lại kho dữ liệu production).
- Đã tạo hội thoại nghiệm thu: `CONV-INDRA-ECD1B9`.
- **Câu hỏi 1 (Vấn đề mã lỗi C6610):**
  - *Câu hỏi:* `"Trong tài liệu thực hành lỗi C6610 (PLM N00137687), mã linh kiện COUPLING CLAW và nguyên nhân gây lỗi C6610 là gì?"`
  - *Kết quả truy hồi:* Trả lời chính xác số PLM `N00137687`, linh kiện `COUPLING CLAW`, mã phụ tùng `302ND31540-01` (`30C2G31011-01`), và nguyên nhân hỏng hóc/tiếp xúc khớp nhả sấy. Toàn bộ thông tin được truy xuất trực tiếp từ các đoạn văn bản mà Indra OCR bóc tách từ 31 trang scan thuần.
- **Câu hỏi 2 (Sơ đồ mạch điện tử 7PA1187DCZ):**
  - *Câu hỏi:* `"Trong sơ đồ mạch 7PA1187DCZ, hãy liệt kê thông tin về mã linh kiện ASSY, bo mạch PWB và các ghi chú sửa đổi kỹ thuật."`
  - *Kết quả truy hồi:* Trích xuất chính xác mã cụm lắp ráp `ASSY 303TD47030`, mã bo mạch `PWB 7PA1187DCZ+GH01`, cùng bảng lịch sử sửa đổi kỹ thuật bằng tiếng Nhật.

### 5.2. Danh mục ảnh chụp màn hình giao diện thật (Browser Proof)
Ảnh chụp tự động bằng Playwright Chromium headless trên giao diện Streamlit Workspace Chat (`http://localhost:58839`):

| Tên tệp ảnh | Kích thước | SHA-256 Checksum | Nội dung minh chứng |
| :--- | :---: | :---: | :--- |
| **`anh-desktop-indra-ocr-01-c6610.png`** | 138,894 bytes | `7907943c2ae281d2561e06241c0417d7e2928f0313d8f6dc6d87d32f1363ccd9` | Giao diện câu hỏi và câu trả lời C6610 truy hồi mã linh kiện `COUPLING CLAW 302ND31540-01` từ PDF scan thuần 31 trang. |
| **`anh-desktop-indra-ocr-02-sodo-mach.png`** | 89,804 bytes | `3366c9bbbeaa1a501abdf41413d3f68482293ba22ec046a09d14191d2954f60f` | Giao diện cuộn xuống câu hỏi và câu trả lời Sơ đồ mạch 7PA1187DCZ trích xuất `ASSY 303TD47030` và `PWB 7PA1187DCZ+GH01`. |
| **`anh-desktop-indra-ocr-03-full-conversation.png`** | 275,913 bytes | `e7ae45709d39c6a4fbb181ad381acafb70f7db670d4183102b123518efb7dc9d` | Toàn cảnh hội thoại hoàn chỉnh gồm 2 câu hỏi - đáp RAG và thanh bên Sidebar hiển thị 3 nguồn tài liệu Indra OCR đã nạp. |

*Tất cả 3 ảnh đã được lưu tại cả hai kho:*
- `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\`
- `D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\`
- Manifest băm SHA256 lưu tại: `hop-thu/lan-desktop/ket-qua/indra_screenshots_manifest.json`.

---

## 6. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG NGUYÊN VĂN (VERBATIM TEST OUTPUT)

Đã chạy toàn bộ test suite cho module `document_extractors` và `indra_ocr_adapter` bằng lệnh:
`pytest tests/test_document_extractors.py tests/test_indra_ocr_adapter.py -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0 -- D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 40 items

tests/test_document_extractors.py::test_extract_excel_with_shapes PASSED [  2%]
tests/test_document_extractors.py::test_extract_pdf_with_text PASSED     [  5%]
tests/test_document_extractors.py::test_extract_pdf_empty_scanned PASSED [  7%]
tests/test_document_extractors.py::test_extract_text_chunks_from_pdf PASSED [ 10%]
tests/test_document_extractors.py::test_extract_pdf_missing_dependency PASSED [ 12%]
tests/test_document_extractors.py::test_route_pdf_pages_uses_pdf_inspector_markdown PASSED [ 15%]
tests/test_document_extractors.py::test_route_pdf_pages_falls_back_to_pymupdf PASSED [ 17%]
tests/test_document_extractors.py::test_route_pdf_pages_rescues_false_positive_ocr PASSED [ 20%]
tests/test_document_extractors.py::test_pptx_adapter_extracts_slide_text_and_notes PASSED [ 22%]
tests/test_document_extractors.py::test_xml_cleanup_flag_defaults_off_and_cleans_markup PASSED [ 25%]
tests/test_document_extractors.py::test_pptx_xml_cleanup_preserves_text_outside_and_inside_nested_t_nodes PASSED [ 27%]
tests/test_document_extractors.py::test_pptx_xml_cleanup_keeps_text_facts_and_strips_long_namespaces PASSED [ 30%]
tests/test_document_extractors.py::test_clean_pptx_chunks_are_unchanged_when_xml_cleanup_is_enabled PASSED [ 32%]
tests/test_document_extractors.py::test_xml_cleanup_handles_nested_cdata_entities_and_multiline_tags PASSED [ 35%]
tests/test_document_extractors.py::test_pptx_xml_cleanup_strips_pretty_printed_truncated_markup PASSED [ 37%]
tests/test_document_extractors.py::test_excel_drawing_xml_cleanup_strips_truncated_multiline_markup PASSED [ 40%]
tests/test_document_extractors.py::test_docx_adapter_extracts_paragraphs_and_tables PASSED [ 42%]
tests/test_document_extractors.py::test_html_adapter_keeps_mermaid_and_removes_script PASSED [ 45%]
tests/test_document_extractors.py::test_registry_routes_and_fallback_metadata_only PASSED [ 47%]
tests/test_document_extractors.py::test_metadata_only_fallback_schema PASSED [ 50%]
tests/test_document_extractors.py::test_image_metadata_or_ocr_safe PASSED [ 52%]
tests/test_document_extractors.py::test_normalization_reduces_coordinate_garbage_and_preserves_multilingual PASSED [ 55%]
tests/test_document_extractors.py::test_ocr_router_prefers_rapidocr_and_stops_after_quality_pass PASSED [ 57%]
tests/test_document_extractors.py::test_ocr_router_escalates_after_failed_quality_gate PASSED [ 60%]
tests/test_document_extractors.py::test_fast_mode_never_loads_heavy_fallbacks PASSED [ 62%]
tests/test_document_extractors.py::test_deep_pdf_mode_is_opt_in PASSED   [ 65%]
tests/test_document_extractors.py::test_excel_streaming_row_chunking_2000_rows PASSED [ 67%]
tests/test_document_extractors.py::test_excel_no_cell_count_truncation_30k_cells PASSED [ 70%]
tests/test_document_extractors.py::test_document_extractors_excel_streaming_integration PASSED [ 72%]
tests/test_document_extractors.py::test_excel_extraction_config_custom_chunk_size PASSED [ 75%]
tests/test_indra_ocr_adapter.py::test_is_indra_enabled_toggle PASSED     [ 77%]
tests/test_indra_ocr_adapter.py::test_evaluate_pdf_gate_disabled_config PASSED [ 80%]
tests/test_indra_ocr_adapter.py::test_evaluate_pdf_gate_non_pdf PASSED   [ 82%]
tests/test_indra_ocr_adapter.py::test_evaluate_pdf_gate_short_doc PASSED [ 85%]
tests/test_indra_ocr_adapter.py::test_evaluate_pdf_gate_skipped_long_doc PASSED [ 87%]
tests/test_indra_ocr_adapter.py::test_evaluate_pdf_gate_zero_char_pages_long_doc PASSED [ 90%]
tests/test_indra_ocr_adapter.py::test_stats_recorded_and_attached_to_chunks PASSED [ 92%]
tests/test_indra_ocr_adapter.py::test_workspace_chat_ingest_contains_indra_metadata PASSED [ 95%]
tests/test_indra_ocr_adapter.py::test_disabled_by_config_reverts_exact_old_behavior PASSED [ 97%]
tests/test_indra_ocr_adapter.py::test_local_capabilities_reports_indra PASSED [100%]

============================= 40 passed in 24.38s =============================
```

---

## 7. BẢO ĐẢM PHÂN QUYỀN VÀ BẤT BIẾN AN TOÀN

1. **Không re-ingest kho production:** Toàn bộ quá trình kiểm thử và đo lường chỉ thực hiện trên staging store và các tệp độc lập trong `C:\tmp\indra_test_files`.
2. **Không chạm tới máy PC0575:** Indra OCR chỉ cài đặt và kiểm thử nội bộ trên máy nhà H410ASROCK.
3. **Không chỉnh sửa `expert_roles.yaml`:** Giữ nguyên 100% cấu hình vai trò chuyên gia.
4. **Không can thiệp đường trả lời hay định dạng ngoài PDF:** Các định dạng DOCX, PPTX, XLSX... giữ nguyên pipeline ban đầu.
5. **CPU thuần túy:** Toàn bộ quy trình inference và OCR chạy qua ONNX Runtime CPU, hoàn toàn không gọi GPU hay cài đặt PyTorch.

---

```json
{
  "ma_ve": "DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-21T15:25:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
