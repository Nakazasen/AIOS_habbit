# Vé GPU-262b — Báo cáo tiến độ

- Trạng thái: `dang-lam`; staging GPU-262b đã tạo, schema khớp, chưa nhúng.
- Mốc cập nhật: 2026-10-01 00:34 +07.

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

## 4. Bước kế

- Đối chiếu trước khi nhúng: phiên bản ONNX Runtime, revision mô hình, mã băm cây ONNX và việc backend tự chọn CUDA; sau đó nhúng 2.883 mảnh.
