# Báo cáo vé `INDEX-LOCALCOPY-FIX-HOME` — loại bản sao cũ 28/09 khỏi mọi đường đọc mặc định

- Vé: `INDEX-LOCALCOPY-FIX-HOME` (máy nhà `h410asrock`, nhánh `phieu-viec/rag-fix1`, không merge `main`).
- Mức hoàn thành: **XONG chờ duyệt** — sửa đúng 3 điểm trong prompt, không xoá bản sao, không đụng tệp production, không ghi index.
- Căn cứ: báo cáo `index-localcopy-check-home.md` (ĐẠT 08/10) — bản sao `local_runs/.../library.sqlite` là bản ghim cũ 28/09 (496 tài liệu / 133.144 mảnh).
- Rào giữ: không xoá/di chuyển/đổi tên bản sao cũ; không đụng tệp production; không ghi index.

## 1. Việc đã làm (đúng 3 điểm)

### Điểm 1 — `scripts/workspace_chat_rag_v2_activation.py`
- Trước: `DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"` làm mặc định `--runtime-root` → chạy không tham số lặng lẽ dùng bản cũ.
- Sau:
  - Giữ hằng cũ chỉ để ghi chú bản cũ, thêm `_LEGACY_STALE_RUNTIME_ROOT` + hàm `resolve_runtime_root()`.
  - `--runtime-root` mặc định `None`. Khi `prepare`/`activate` mà `None` → đọc `runtime.root` từ `config/workspace_chat_rag_v2.local.json`, chỉ nhận khi là đường tuyệt đối và thư mục tồn tại; thiếu thì dừng với `ActivationError` tiếng Việt (yêu cầu truyền `--runtime-root` production thật, nêu rõ không dùng bản cũ 28/09 thiếu 16.656 mảnh).
  - `status`/`rollback`/`promote` không ép resolve (không cần runtime).
- Lý do: đúng yêu cầu vé — ưu tiên production thật ở ổ C, thiếu thì dừng rõ ràng, tuyệt đối không lặng lẽ dùng bản cũ.

### Điểm 2 — `scripts/benchmark_adaptive_reranking.py:593`
- Trước: `effective_runtime = str(runtime_root or (deployment.runtime_root if ... else PROJECT_ROOT / "local_runs/..."))` → thiếu cả hai vẫn ghi provenance là bản cũ.
- Sau:
  - Thêm `_LEGACY_STALE_RUNTIME_ROOT`, `_PRODUCTION_MANIFEST`, hàm `_resolve_production_runtime_root()` (đọc `runtime.root` từ config, chỉ nhận khi tồn tại).
  - Thứ tự: `runtime_root` truyền tay → `deployment.runtime_root` → production từ config → rỗng + thêm `blocked_reasons` tiếng Việt + `is_ready=False`.
  - Không còn fallback `local_runs` nào. Đường `BLOCKED` ghi `runtime_root=""`, đường thật ghi production.
- Lý do: cùng nguyên tắc điểm 1 — trỏ production thật hoặc dừng rõ ràng (BLOCK), không bịa provenance bản cũ.

### Điểm 3 — `tests/test_index_status.py`
- Chọn **hướng (a)**: đọc đúng tệp production theo config, bỏ qua sạch khi không có.
- Thêm `_resolve_production_db_path()`: đọc `runtime.root` + `requested_profile` từ `config/workspace_chat_rag_v2.local.json`, ghép `<root>/<profile>/collections/tri_thuc/library.sqlite` (đường app thật đã chứng minh ở `INDEX-PROD-HOME`). Thiếu config/file → `pytest.skip` tiếng Việt.
- Lý do chọn (a) thay vì (b): tên test là `matches_real_db` — real DB phải là production app đang đọc; giữ đọc bản local rồi khẳng định tính "cũ" sẽ khóa test vào bản ghim 28/09, mất ý nghĩa kiểm production. Hướng (a) giữ đúng ý nghĩa, skip sạch trên CI/VM không có ổ C, xanh thật trên máy nhà có production.

## 2. Kiểm chứng (chạy thật trên máy này)

- Python: `3.11.14` qua `uv` (đúng cổng).
- Mặc định mới không trỏ `local_runs`:
  - `build_parser().get_default('runtime_root')` = `None` (trước là `local_runs/...`).
  - `resolve_runtime_root(None)` = `C:\AIOS_workspace_chat_rag_v2_production`.
  - `_resolve_production_runtime_root()` benchmark = `C:\AIOS_workspace_chat_rag_v2_production`.
  - `grep` parser không còn `default=DEFAULT_RUNTIME_ROOT`.
- `tests/test_index_status.py -v`: **9 passed in 34.20s**, gồm `test_index_status_matches_real_db_if_present` PASSED (đọc production thật 889/149.800, không còn đỏ oan).
- Cổng repo:
  - `compileall src tests`: sạch.
  - `cli audit`: `{"status": "PASS"}`.
  - `import aios_habit.workspace_chat_app`: thành công (`import OK`).
  - Hồi quy chạm tới: `tests/test_workspace_chat_rag_v2_deployment.py`: **25 passed**.
- Chế độ an toàn 2 script: `--help` hiện `--runtime-root` không còn mặc định bản cũ; `resolve` ra production; `status` không đụng index. Không chạy `prepare`/`activate` thật (tránh chạm production theo rào).
- Không đổi UI: vé này sửa mặc định script/test, không đổi giao diện; đã chứng minh bằng chạy thật script + test trên production thật thay vì ảnh chụp UI.

## 3. Rào cứng đã giữ

- Không xoá/di chuyển/đổi tên bản sao cũ `local_runs/.../library.sqlite` (chỉ đọc kiểm, không ghi).
- Không đụng tệp production `C:\AIOS_workspace_chat_rag_v2_production\...\library.sqlite` ngoài đọc chỉ-đọc qua test (mode ro của `get_index_status_info`).
- Không ghi index, không merge `main`.
- Không secret, không commit dữ liệu thật.
