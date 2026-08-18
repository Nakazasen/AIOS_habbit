# Sổ Tay Vận Hành Sản Xuất OCR (OCR Production Runbook)

## Pipeline

```text
PDF Inspector → Cứu hộ PyMuPDF gốc (native rescue) → RapidOCR
                                                   → PaddleOCR (tùy chọn)
                                                   → Tesseract (chỉ dùng khẩn cấp)

deep / auto_deep → Docling CPU
offline_max       → Marker CPU → Docling fallback
```

Truy xuất kết hợp BGE-M3 Hybrid không thay đổi. Mọi bộ phân tích OCR/deep parser đều chỉ dùng cục bộ (local-only).
Các mô hình được tải lười (lazily) và các engine chạy tuần tự để tránh làm cạn kiệt RAM 16 GB.

## Các Tầng Cài Đặt (Install tiers)

```powershell
# Cấu hình laptop khuyến nghị: PDF Inspector + RapidOCR/ONNX CPU
.\.venv\Scripts\python.exe -m pip install -e ".[rag-ingestion-cpu]"

# Dự phòng PaddleOCR tùy chọn (dung lượng lớn)
.\.venv\Scripts\python.exe -m pip install -e ".[ocr-paddle-cpu]"

# Bộ phân tích sâu Docling tùy chọn
.\.venv\Scripts\python.exe -m pip install -e ".[document-deep-cpu]"

# Cấu hình offline tối đa Marker + Docling tùy chọn (lớn nhất)
.\.venv\Scripts\python.exe -m pip install -e ".[document-offline-max]"
```

Không cài đặt PaddleOCR hoặc Marker trên cấu hình laptop mặc định trừ khi dữ liệu đo chuẩn (benchmark) cho thấy RapidOCR là chưa đủ.

## Các Chế Độ Runtime (Runtime modes)

Thiết lập `AIOS_OCR_MODE` trước khi nạp dữ liệu:

| Chế độ (Mode) | Hành vi (Behavior) | Khuyến nghị cho laptop |
|---|---|---|
| `fast` | Chỉ RapidOCR | Độ trễ/RAM thấp nhất |
| `balanced` | RapidOCR → PaddleOCR → Tesseract | **Mặc định** |
| `auto_deep` | Docling chỉ cho PDF dạng bảng/cột; còn lại dùng balanced | Tập ngữ liệu có cấu trúc |
| `deep` | Docling cho mọi PDF; dự phòng nhẹ khi thất bại | Tùy chọn thủ công |
| `offline_max` | Marker → Docling | Chỉ dùng cho máy trạm/xử lý theo lô |
| `legacy` | Chỉ Tesseract | Hoàn tác khẩn cấp |

Ví dụ PowerShell:

```powershell
$env:AIOS_OCR_MODE = "balanced"
$env:AIOS_OCR_CPU_THREADS = "4"
$env:AIOS_MAX_PDF_OCR_PAGES = "3"
$env:AIOS_DEEP_PARSE_TIMEOUT_SECONDS = "300"
```

`AIOS_OCR_ENGINE_ORDER` có thể ghi đè thứ tự balanced, ví dụ `rapidocr,tesseract`. Các tên không hợp lệ sẽ bị bỏ qua.

## Cổng Đo Chuẩn (Benchmark gate)

Render các trang PDF tiêu biểu thành hình ảnh, bao gồm tiếng Việt gốc, bản scan, góc xoay, bảng biểu và các trang độ phân giải thấp. Sau đó chạy các engine tuần tự:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_ocr_engines.py .\benchmark-pages `
  --engines rapidocr,paddleocr --threads 4 --output .\ocr_benchmark.jsonl
```

Đánh giá độ chính xác văn bản tuyệt đối so với sự thật thực tế (ground truth) của con người bên cạnh độ tin cậy (confidence) và độ trễ. Chỉ thăng cấp PaddleOCR nếu mức cải thiện độ chính xác đo được bù đắp được dung lượng cài đặt và mức sử dụng bộ nhớ. Tuyệt đối không bao giờ đo chuẩn nhiều engine đồng thời trên laptop 16 GB.

## Hành Vi Khi Thất Bại (Failure behavior)

- Thiếu các engine tùy chọn không bao giờ làm crash quá trình nạp.
- Phân tích cú pháp sâu (deep parse) thất bại sẽ tự động dự phòng về PDF Inspector/PyMuPDF/RapidOCR.
- Văn bản OCR dưới ngưỡng tin cậy hiện có sẽ bị từ chối.
- Chỉ số lượng trang scan tối đa đã cấu hình mới được OCR trên mỗi PDF.
- Provenance ghi lại engine thực tế đã dùng (`rapidocr`, `paddleocr`, `tesseract`, `docling-cpu`, hoặc `marker-cpu`).


