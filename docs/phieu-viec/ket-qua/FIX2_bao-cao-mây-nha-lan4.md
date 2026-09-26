# FIX 2 vòng 4 — ONNX fp32 thành model mặc định khi bật backend

Ngày: 2026-09-26. Branch: `phieu-viec/rag-fix1`.

## Thay đổi

- `src/aios_habit/rag_v2/bge_onnx_backend.py`: đổi `ONNX_DIR_NAME` từ
  `bge-m3-onnx-int8` sang `bge-m3-onnx-fp32`. Khi `AIOS_BGE_ONNX_MODEL_PATH`
  không đặt và người dùng chọn ONNX, runtime giờ tìm model fp32 đã nghiệm thu.
- Checksum không có hằng số cứng trong runtime: `resolve_onnx_checksum()` đọc
  `AIOS_BGE_ONNX_MODEL_CHECKSUM` nếu đặt, nếu không thì lấy sidecar cạnh model.
  Default path mới vì vậy tìm `models/bge-m3-onnx-fp32.sha256`; checksum đã xác
  minh vòng 3 là `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
- Giữ nguyên `_BACKEND_ALIASES`: `BGE_BACKEND=onnx` và `onnx_int8` cùng chọn
  backend ONNX; class/error strings `OnnxInt8…`/`onnx_int8_*` không đổi.
- Hai thư mục int8 giữ nguyên làm tùy chọn thử nghiệm. Default output của script
  exporter int8 cũng giữ nguyên vì script đó tạo model quantized, không phải
  runtime model mặc định.
- Khi `BGE_BACKEND` unset, runtime vẫn dùng `pytorch`; không thay hành vi mặc định.

## Kiểm thử

- Tập trung: `uv run --no-sync --group dev pytest tests/test_rag_v2_bge_onnx.py -q`
  — **7 passed**.
- Full suite: `uv run --no-sync --group dev pytest tests/ -q` —
  **3120 passed, 2 skipped, 23 failed** trong 432.95 s.
- 23 failures ở các nhóm không đổi bởi patch này:
  - `tests/test_bge_subprocess_client.py` (3) và `tests/test_bge_subprocess_worker.py` (6): worker `stdout_eof` lúc init.
  - `tests/test_commit_d_wheel_and_packaging.py` (3): `uv.lock --check` báo lockfile cần cập nhật; 2 desktop smoke không import được `aios_habit` trong venv cô lập.
  - `tests/test_graphify_adapter.py` (9): Graphify package `graphifyy==0.9.50` không khả dụng.
  - `tests/test_owner_workflow_cli.py` (2): tiến trình `.venv\Scripts\python.exe` không import được `aios_habit`.
- Các lỗi suite nêu trên là lỗi package/import/lockfile; không có test ONNX nào fail.
  Không sửa `pyproject.toml` hoặc `uv.lock`.

## Flag và rollback

- Default: `BGE_BACKEND` unset → **PyTorch**.
- ONNX fp32: đặt `BGE_BACKEND=onnx` (hoặc alias cũ `onnx_int8`); nếu không đặt
  `AIOS_BGE_ONNX_MODEL_PATH`, default là `models/bge-m3-onnx-fp32/`.
- Checksum: unset `AIOS_BGE_ONNX_MODEL_CHECKSUM` để đọc sidecar
  `models/bge-m3-onnx-fp32.sha256`, hoặc đặt checksum tường minh.
- Rollback: unset `BGE_BACKEND` hoặc đặt `BGE_BACKEND=pytorch`.
