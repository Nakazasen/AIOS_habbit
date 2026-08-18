# Chiến Lược Bộ Chuyển Đổi Trích Xuất AIOS (AIOS Extraction Adapter Strategy)

## Giao Diện Bộ Chuyển Đổi Trích Xuất (Extractor Adapter Interface)

Một Bộ chuyển đổi Trích xuất (Extractor Adapter) của AIOS cung cấp giao diện nhất quán cho các thư viện bên thứ ba trong khi vẫn bảo vệ phần còn lại của ứng dụng khỏi các lệnh import phụ thuộc cụ thể.
Mỗi adapter bắt buộc phải:
1. Nhận một đường dẫn `Path` và một thư mục gốc `root`.
2. Trả về một danh sách các đối tượng `ExtractionResult`.
3. Không làm sập ứng dụng nếu thiếu phụ thuộc tùy chọn; thay vào đó, nó phải trả về kết quả lỗi hoặc không hỗ trợ.
4. Hỗ trợ chuyển tiếp an toàn (gracefully failover) sang adapter tiếp theo trong chuỗi fallback.

## Schema Phần Tử Chung (Common Element Schema)

Mọi kết quả trích xuất đều được chuẩn hóa thông qua `build_elements_from_extracted_payload` vào schema `RAGDocumentElement`, bao gồm:
- `element_id`, `document_id`, `text`
- `source_title`, `source_path`, `relative_path`, `file_type`
- `privacy_mode`
- `extractor_name`, `extraction_status`, `warnings`
- `metadata`

## Chuỗi Dự Phòng Theo Loại Tệp (Fallback Chain by File Type)

### Excel (.xlsx, .xlsm)
1. Trích xuất ô / bảng hiện có bằng `openpyxl`.
2. Bổ sung phân tích cú pháp `zipfile` của thư viện chuẩn để trích xuất văn bản từ hình vẽ / hộp văn bản (shapes/textboxes) trong `xl/drawings/drawing*.xml`.
3. (Tùy chọn) Khung nhìn bảng Pandas nếu được kích hoạt.
4. Dự phòng (Fallback): Chỉ trích xuất metadata nếu trích xuất nội dung thất bại.

### PDF (.pdf)
1. `PyMuPDF4LLM` (nếu đã cài đặt, tùy chọn).
2. Trích xuất lớp văn bản hiện có bằng `PyMuPDF` (`fitz`).
3. Trích xuất OCR hiện có bằng `PyMuPDF` + `pytesseract`.
4. (Tùy chọn) `Docling`.
5. Dự phòng: Chỉ trích xuất metadata.

### PPTX (.pptx)
1. Sử dụng `python-pptx` hiện có (thông qua parse XML) để trích xuất văn bản trang chiếu và ghi chú.
2. (Tùy chọn) `Docling` hoặc `MarkItDown`.
3. Dự phòng: Chỉ trích xuất metadata.

### Hình ảnh (.png, .jpg, v.v.)
1. OCR hiện có qua `pytesseract` + `PIL`.
2. Dự phòng: Chỉ trích xuất metadata.

## Bảo Tồn Metadata Trích Dẫn (Preserving Citation Metadata)

Để duy trì khả năng truy xuất nguồn gốc nghiêm ngặt, `ExtractionResult` thu thập ngữ cảnh ánh xạ vào các thuộc tính `RAGDocumentElement`:
- **page**: Đặt `ExtractionResult.page` -> ánh xạ tới `page_number` trong `metadata`.
- **sheet**: Đặt `ExtractionResult.sheet` -> ánh xạ tới `sheet_name`.
- **row_range / cell_range**: Đặt `ExtractionResult.row_range` -> ánh xạ tới `metadata['row_range']`.
- **slide**: Đặt `ExtractionResult.slide` -> ánh xạ tới `metadata['slide']`.
- **shape_id / image_id**: Đưa vào `metadata`.
- **extractor_name**: Ánh xạ trực tiếp tới `extractor_name`.

## Đánh Dấu Độ Tin Cậy Trích Xuất (Marking Extraction Confidence)

Trạng thái trích xuất phải rõ ràng:
- **Cao (High)**: `extracted_success`
- **Trung bình / Một phần (Medium/Partial)**: `extracted_partial`, `ocr_partial`
- **Thấp / Thất bại (Low/Failed)**: `failed_with_reason`, `unsupported_no_local_tool`
- **Chỉ Metadata (Metadata Only)**: Trả về văn bản trống nhưng đặt `extraction_status = "metadata_only"` (hoặc xử lý tương tự trong luồng fallback của `notebooklm_compare.py`).

## Tránh Làm Hỏng Các Bài Kiểm Thử Hiện Có

- Không xóa hoặc thay đổi chữ ký hàm của các hàm hiện có (`extract_text_chunks_from_file`, `_extract_excel`, v.v.).
- Bổ sung vào kết quả hiện có. Đối với Excel, chỉ cần nối `ExtractionResult` từ việc phân tích XML bản vẽ vào danh sách trả về bởi `_extract_excel`.
- Trả về chuỗi rỗng hoặc xử lý lỗi một cách an toàn bên trong adapter để bộ lập chỉ mục không bị sập.

## Giữ Các Phụ Thuộc Nặng Ở Trạng Thái Tùy Chọn

- Tuyệt đối chưa thêm các phụ thuộc nặng (như `docling` hoặc `unstructured`) vào `pyproject.toml` hoặc `requirements.txt`.
- Sử dụng `importlib.util.find_spec` hoặc khối `try/except` khi import các adapter tùy chọn.

