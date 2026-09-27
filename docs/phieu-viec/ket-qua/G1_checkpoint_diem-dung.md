# Vé A — Chốt điểm dừng G1

Ngày đo: 2026-09-27. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã commit nhánh tại thời điểm chạy: `d2db518`. Hệ điều hành: Windows 10 build 18363, 64 bit. Python: `3.11.14`.

## Kết quả

- Chỉ mục: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.
- `PRAGMA integrity_check`: **`ok`**. Lần chạy đầu bị ngắt do hết hạn 180 giây; sau `quick_check=ok`, chạy lại `integrity_check` hoàn tất, trả đúng một dòng `ok` trong 8,2 giây.
- Kích thước trước/sau kiểm tra: **1.698.164.736 / 1.698.164.736 byte**. `mtime` quan sát được: `2026-09-27 13:19:25 +0700`. Không có tệp `-wal`, `-journal` hoặc `-shm` cạnh chỉ mục.
- Đếm trong SQLite chỉ-đọc: **496 tài liệu**, **133.144 chunk** tổng cộng, trong đó **107.331 chunk truy xuất được**.
- Dense ONNX `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`: **8.328 chunk**; sparse ONNX cùng mã: **8.328**.
- Dense PyTorch cũ `ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c`: **340 chunk**; sparse PyTorch cùng mã: **340**. Cả 340 chunk PyTorch đều cũng có vector ONNX; không có chunk chỉ mang vector PyTorch.
- Kế hoạch dry-run ONNX: **99.003 chunk pending**, khớp `107.331 - 8.328`; số đếm chính thức trong kế hoạch cũng đối chiếu `content_hash` với SHA-256 của nội dung chunk. Tất cả 8.328 vector ONNX thuộc chunk truy xuất được. Tổng cộng `8.328 + 99.003 = 107.331`.
- Theo độ phủ từng tài liệu: 74 tài liệu đã đủ ONNX, 197 đang có một phần, 225 chưa có vector ONNX; tổng 496 tài liệu.

## Điểm resume chính xác

Kế hoạch `scripts/migrate_vectors_to_onnx.py` sắp xếp danh sách pending theo `chunk_id`. Với batch mặc định 10, lần chạy mới sẽ bắt đầu từ **batch 1/9.901 của danh sách pending hiện tại**, ở vị trí 1, chunk:

- `document_id`: `wsc-9c82b1ca2e1898a8d9d03e8b`
- `chunk_id`: `1172f198bf3cc27b159ec9ece90d02d9e420bb37cf96f732a93401386e1c2bf6`
- Batch cuối theo số lượng hiện tại có 3 chunk. Đây là thứ tự của kế hoạch dry-run hiện tại, không phải số batch lịch sử của tiến trình đã dừng.

Ticket A không tiếp tục nhúng và không resume. Vé B mới quyết định có dùng GPU hay không.

## Cách đo và bằng chứng

- Mở SQLite bằng URI `mode=ro`; chạy `PRAGMA integrity_check` và `PRAGMA quick_check`.
- Đếm tài liệu/chunk bằng `COUNT(*)`, `COUNT(DISTINCT document_id)` và bộ lọc `retrievable=1` trên bảng `chunks`.
- Đếm dense/sparse theo `model_fingerprint` trên `chunk_embeddings` và `chunk_sparse_embeddings`; đối chiếu các chunk PyTorch/ONNX bằng `chunk_id`.
- Chạy dry-run, không có `--apply`:
  `uv run --no-sync --group dev python scripts/migrate_vectors_to_onnx.py "local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite"`
  Kết quả thật: `retrievable_chunks=107331`, `already_onnx=8328`, `pending_chunks=99003`, `dry_run: no changes written`.
- Kích thước chỉ mục được đọc trước và sau `integrity_check`; cả hai cùng là `1698164736` byte.
- Mã nguồn tại lúc đo: commit `d2db518`; SHA-256 của `scripts/migrate_vectors_to_onnx.py` là `b198f6516118f4d226c2d79f95e3c8765fda2009bcc13036ad3c32cedf6666b2`; SHA-256 của `src/aios_habit/rag_v2/bge_onnx_backend.py` đang chạy là `3ebdbb5b6ba3c8cd4370c0c82b48bd34bd55e26fe690227cf747a5f00f347589`. Thư mục làm việc đã có thay đổi cục bộ chưa commit trước khi nhận vé; các thay đổi đó được giữ nguyên, không đưa vào commit báo cáo.
- Chỉ mục không bị ghi; không chạy embed, không resume, không tạo bản sao hoặc thay đổi backend.

## Bàn giao

- Báo cáo được commit riêng và đẩy lên `phieu-viec/rag-fix1`; không đụng `main`.
- Commit báo cáo: cập nhật trong `trang-thai.md` sau khi commit.
