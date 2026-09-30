# Vé GPU-262b — Báo cáo tiến độ

- Trạng thái: `dang-lam`; staging GPU-262b đã tạo, schema khớp, chưa nhúng.
- Mốc cập nhật: 2026-10-01 00:41 +07.

## 1. Dừng lượt GPU-262 cũ

- Lượt cuối hết giới hạn chạy vào khoảng 00:06 +07 ngày 01/10/2026. Truy vấn chỉ đọc lúc 00:06:47 xác nhận có **20.300/52.979 mảnh** với đủ vector đặc và vector thưa.
- Tiến trình GPU-262 đã dừng; giữ nguyên `C:\AIOS_staging_262\library.sqlite`, không xóa và không tiếp tục nhúng tại đó.

## 2. Tái sử dụng và lọc tệp nguồn

- Tệp nguồn hiện có: `C:\tmp\gpu-262\text_export.jsonl`, **81.531.448 byte**, SHA-256 `95aecf07297bfdf2e4f7462fd477fa052a89aa3eaaa462c53cbce40d341bb505`; kích thước và mã băm khớp vé. Không tải lại từ Drive.
- Quy tắc lọc: giữ dòng có `source_name` không kết thúc bằng `.csv`, không phân biệt chữ hoa/thường; ghi nguyên dòng JSONL, không sửa văn bản.
- Kết quả: **52.979 dòng nguồn**; loại **50.096 dòng CSV / 87 tên tệp**; giữ **2.883 dòng / 19 `document_id` / 19 tên nguồn**. Số dòng từng tài liệu và toàn bộ tên nguồn khớp bảng trong prompt.
- Tệp lọc: `C:\tmp\gpu-262b\export_19.jsonl`, **2.925.790 byte**, SHA-256 `0d1907c3e4cf21eaced480f35443cc7f9d6c7874e8edf904f765a4ec8a165ed2`. Nội dung chỉ lưu cục bộ, không đưa vào Git.

## 3. Tạo staging mới

- Đã tạo `C:\AIOS_staging_262b\library.sqlite`; toàn bộ định nghĩa lược đồ SQLite khớp collection `tri_thuc` hiện tại.
- Kiểm tra: `integrity_check=ok`, không có lỗi khóa ngoại; 2.883 mảnh / 19 tài liệu, tất cả `retrievable=1`, chỉ mục FTS có 2.883 dòng; dense và sparse đều bằng 0.
- Kích thước tệp: **34.512.896 byte**. Nội dung văn bản lấy nguyên từ tệp lọc; đường dẫn nguồn là metadata logic do export thiếu `source_path` và nhãn riêng tư. Nhãn `local_only` chỉ để phân loại nội bộ, không tự chặn định tuyến.
- Không ghi vào production, staging cũ hoặc ổ D.
- Bản sao dự phòng trước nhúng: `C:\AIOS_staging_262b\library.sqlite.bak-20261001-gpu262b-preembed`, `integrity_check=ok`, 2.883 mảnh / 19 tài liệu, SHA-256 `e6222918005ea42477f8fa48361e19d98f339b6b32099fe0316143c7aa9996a4`.

## 4. Bước kế
- Kiểm tra khô lúc 00:41:23 +07: ONNX Runtime và siêu dữ liệu gói đều `1.28.0`; cây mô hình khớp checksum đã ghim `9f81075f…b11093`; revision dùng `5617a9f61b028005a4858fdac845db406aefb181`; fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`; `pending=2883`, `retrievable=2883`, `already_onnx=0`. Phiên mở với `CUDAExecutionProvider` đứng đầu, `CPUExecutionProvider` dự phòng; `dry_run=không ghi dữ liệu`.
- Cache kiểm tra cây mô hình được chuyển sang `C:\tmp\gpu-262b\model-verify-cache-20261001.json` trên C; không ghi ổ D. Chưa nhúng mảnh nào trong lượt chạy khô.
- Kiểm tra khô đạt; bắt đầu nhúng 2.883 mảnh bằng runner Vé 0.3 sau khi đẩy mốc này.
