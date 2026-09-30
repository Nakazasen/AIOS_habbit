# Vé GPU-262b — Báo cáo tiến độ

- Trạng thái: `xong-cho-duyet`; đã nhúng, xác minh và đóng gói đủ 2.883/2.883 mảnh. Gói chưa được nhập vào production.
- Mốc cập nhật: 2026-10-01 01:34 +07.

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
- Kiểm tra: `integrity_check=ok`, không có lỗi khóa ngoại; 2.883 mảnh / 19 tài liệu, tất cả `retrievable=1`, chỉ mục FTS có 2.883 dòng; vector đặc và vector thưa đều bằng 0.
- Kích thước tệp: **34.512.896 byte**. Nội dung văn bản lấy nguyên từ tệp lọc; đường dẫn nguồn là siêu dữ liệu logic do export thiếu `source_path` và nhãn riêng tư. Nhãn `local_only` chỉ để phân loại nội bộ, không tự chặn định tuyến.
- Không ghi vào production, staging cũ hoặc ổ D.
- Bản sao dự phòng trước nhúng: `C:\AIOS_staging_262b\library.sqlite.bak-20261001-gpu262b-preembed`, `integrity_check=ok`, 2.883 mảnh / 19 tài liệu, SHA-256 `e6222918005ea42477f8fa48361e19d98f339b6b32099fe0316143c7aa9996a4`.

## 4. Kiểm tra và nhúng GPU
- Kiểm tra khô lúc 00:41:23 +07: ONNX Runtime và siêu dữ liệu gói đều `1.28.0`; cây mô hình khớp `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`; revision dùng `5617a9f61b028005a4858fdac845db406aefb181`; fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`; `pending=2883`, `retrievable=2883`, `already_onnx=0`. Phiên mở với `CUDAExecutionProvider` đứng đầu, `CPUExecutionProvider` dự phòng; `dry_run=không ghi dữ liệu`.
- Bộ đệm kiểm tra cây mô hình được chuyển sang `C:\tmp\gpu-262b\model-verify-cache-20261001.json` trên C; không ghi ổ D. Lượt chạy khô chưa nhúng mảnh nào.
- Lần gọi đầu sau lượt khô dừng vì bộ đệm kiểm tra mô hình trên C đã tồn tại; staging không đổi. Lượt nhúng chính xác thực bộ đệm qua `verify_model_tree` trước khi chạy.
- Lượt nhúng chính: 00:46:33–00:53:36 +07, **2.883/2.883 mảnh**, 422,7 giây, **6,8203 mảnh/giây**, 29 mẻ ghi. `CUDAExecutionProvider` đứng đầu phiên; `CPUExecutionProvider` dự phòng. Bản sao trước nhúng được công cụ chọn, `integrity_check=ok`.

## 5. Xác minh và đóng gói

- Xác minh chỉ đọc đạt: `integrity_check=ok`, lỗi khóa ngoại 0, 19/19 mã tài liệu, 2.883/2.883 mảnh `retrievable=1`, FTS 2.883; vector đặc và vector thưa đều đủ 2.883/2.883. Fingerprint đúng trên cả hai bảng vector; revision đúng trên toàn bộ vector đặc. Mọi dòng nguồn khớp mảnh staging.
- Kiểu vector đặc lưu `float32-le`, kích thước 1.024 chiều. So khớp 57 mẫu CPU (3 mẫu/tài liệu) với vector GPU: cosine nhỏ nhất/lớn nhất đều `1.000000` (ngưỡng `0,999`).
- Delta SQLite: `C:\AIOS_staging_262b\gpu-262b-delta-20261001.sqlite`, 57.020.416 byte, SHA-256 `b4b6f0bf059f544b606cfb7c33b315d72a5dc9c3a9b9a3591dc4cbfc47cf944a`.
- Gói ZIP: `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip`, 20.867.536 byte, SHA-256 `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85`; CRC đạt, gồm delta SQLite và tệp kê khai `C:\AIOS_staging_262b\gpu-262b-manifest-20261001.json`.
- Tệp kê khai ghi 19 tài liệu / 2.883 mảnh; nhập 14 mã mới và bỏ qua 5 mã đã có, tuyệt đối không ghi đè:
  `wsc-154101d384acc2d01009025d`, `wsc-9e3e7cbc01ed57332c1384eb`, `wsc-a1a89391eee709a956a46130`, `wsc-58589483c646877fdb341f46`, `wsc-cc7d383bb6f7b9127bcaef00`.
- Chưa nhập gói vào production; không ghi production, staging GPU-262 cũ hoặc ổ D.

## 6. Cổng kiểm tra kho mã

- Python `3.11.14`; `compileall src tests` đạt; `scripts/check_docs.py` trả `DOCUMENTATION_CONTRACT=PASS`; CLI audit trả `status=PASS`; import `aios_habit.workspace_chat_app` đạt với `PYTHONPATH=src`.
- `pytest -q` lần chạy đầy đủ cuối (wheel nội bộ trên C, đường dẫn `src` cho tiến trình con): **3.377 đạt, 4 bỏ qua, 25 thất bại, 14 lỗi**. 14 lỗi do hai tệp Excel cục bộ không có trên máy. Các lỗi còn lại gồm BGE worker kết thúc sớm, kiểm thử đóng gói thiếu `torch`/`FlagEmbedding`, kiểm thử phụ thuộc mạng, mã băm manifest `src-quality-process` không khớp và một số assertion quyền riêng tư. Không sửa mã ngoài vé; toàn bộ suite không đạt `PASS`.
