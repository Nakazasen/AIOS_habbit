# Phiếu việc E4 — Đổi bộ xử lý mặc định sang ONNX fp32

Ngày đo: 2026-09-27. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931`; sửa tiến trình hồ sơ từ khóa: `3aa4280fe1e968da635e86ba7b28dff760c6dc40`. Cả hai đã đẩy lên nhánh.
Ticket: `docs/phieu-viec/mailbox/prompt.md`. Không đụng `main`.

## Kết quả

- Khi `BGE_BACKEND` không đặt hoặc đặt `auto`, lựa chọn xử lý mặc định là ONNX fp32 (`onnx`); PyTorch chỉ chạy khi chọn tường minh `BGE_BACKEND=pytorch`.
- `BGE_BACKEND=onnx_int8` vẫn là lựa chọn riêng, tường minh: dùng `models/bge-m3-onnx-int8/model_quantized.onnx`, mã kiểm tra và mã định danh riêng. ONNX fp32 dùng `models/bge-m3-onnx-fp32/model.onnx`.
- Thiếu thư mục, tệp mô hình hoặc mã kiểm tra hợp lệ thì khởi tạo dừng với lỗi nêu đường dẫn và cách chọn PyTorch; không tự chuyển dự phòng.
- Tiến trình hồ sơ từ khóa không đòi thư mục ONNX khi không chạy hồ sơ BGE; có kiểm thử tiến trình con với đường mô hình cố ý không tồn tại.
- Mã định danh vector ONNX fp32 giữ nguyên `016c5255…`; PyTorch giữ `ce7fb53f…`. Chạy dò trước chuyển đổi ở chế độ chỉ đọc cho thấy 1.064/1.064 vector đã khớp, không cần tính lại.

## Thay đổi

- `src/aios_habit/rag_v2/bge_onnx_backend.py`: đặt `onnx` làm mặc định; `auto` trỏ về `onnx`; tách mô hình fp32/int8 theo thư mục, tên tệp và mã kiểm tra; kiểm tra tệp/mã kiểm tra trước khi khởi tạo.
- `src/aios_habit/rag_v2/pipeline.py`: giữ riêng lựa chọn `onnx`, `onnx_int8`, `pytorch`; kiểm tra mô hình trước khi dựng bộ nhúng; phân biệt lựa chọn xử lý trong thông tin tương thích chỉ mục.
- `src/aios_habit/rag_v2/bge_subprocess_worker.py`: chỉ kiểm tra mô hình BGE với hồ sơ `bge_m3_*`; hồ sơ từ khóa không phụ thuộc mô hình BGE.
- `scripts/migrate_vectors_to_onnx.py`: chỉ cho phép chế độ ONNX fp32 mặc định; từ chối lựa chọn rõ ràng `onnx_int8` và `pytorch`.
- `scripts/bench_fix2_onnx.py`: chọn rõ bộ nhúng int8 cho phép đo int8.
- Kiểm thử bao phủ mặc định/`auto`, lựa chọn tường minh, tệp mô hình/mã kiểm tra/mã định danh riêng, lỗi dừng an toàn, quy tắc di trú và tiến trình từ khóa không cần mô hình ONNX.

## Kiểm chứng

- Python: `3.11.14`.
- Bộ kiểm thử liên quan (nhúng, di trú, luồng xử lý và tiến trình con): 63 bài đạt.
- `uv run --no-sync --group dev python -m compileall src tests`: đạt.
- `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit`: `status=PASS`, không lỗi/cảnh báo.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` từ `src`: thoát mã 0.
- `uv run --no-sync --group dev python scripts/check_docs.py`: `DOCUMENTATION_CONTRACT=PASS`.
- `uv run --no-sync --group dev pytest -q`: 3.146 bài đạt, 2 bỏ qua, 23 lỗi trong 281,40 giây. Các lỗi được ghi nguyên trạng:
  - 9 bài kiểm thử tiến trình BGE kết thúc với `bge_worker_init_stdout_eof`; chạy riêng bộ kiểm thử tiến trình với `PYTHONPATH` tuyệt đối thì 16 bài đạt.
  - 9 bài kiểm thử Graphify báo thiếu gói `graphifyy==0.9.50`.
  - 1 bài kiểm thử `uv lock --check` báo `uv.lock` cần cập nhật.
  - 2 bài kiểm thử khói đóng gói và 2 bài `owner-workflow` không nạp được `aios_habit` trong tiến trình con.

## Đo trên chỉ mục thật — chỉ đọc

- Chỉ mục: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`; cấu hình chỉ đọc, không đặt biến chọn bộ xử lý hay đường mô hình, không gọi nhà cung cấp.
- Chạy dò trước chuyển đổi: mã định danh ONNX `016c5255…`, mã định danh PyTorch `ce7fb53f…`, truy xuất được 1.064 vector, đã khớp ONNX 1.064, chờ xử lý 0; không ghi thay đổi.
- Khởi tạo mặc định: lựa chọn `onnx`, 2,406 giây. Truy vấn B1: 0,675 giây; B5: 0,677 giây. Cả hai không từ chối trả lời. Bằng chứng truy xuất có các dấu dữ kiện mong đợi, nhưng câu trả lời tổng hợp không nêu đủ mọi mã kiểm tra; không xem đây là câu trả lời đầy đủ.
- Kích thước chỉ mục trước/sau: 29.851.648 byte. `integrity_check=ok` trước/sau. Không nạp lại nguồn, không chạy `--apply`, không tạo hoặc ghi vector.

## Bàn giao

- Mã E4 và sửa lỗi hồ sơ từ khóa đã đẩy lên `phieu-viec/rag-fix1`; không gộp vào `main`.
- Báo cáo: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`.
- Mailbox sẽ chuyển `xong-cho-duyet` sau khi đẩy báo cáo và trạng thái cuối; sau đó dừng theo ticket.
