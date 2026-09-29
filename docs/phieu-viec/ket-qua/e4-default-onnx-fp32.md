# Vé E4 — Bộ xử lý mặc định ONNX fp32: kiểm chứng + bù test

Ngày chạy: 2026-09-30. Máy: `h410asrock` (Windows), Python `3.11.14`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn: **không đổi** — default ONNX fp32 và fail-closed đã đúng nguyên từ chuỗi FIX3 (`d202c1d` + `77c804b`).
Test: `9de4cac` (3 test mới), `26a2d2b` (siết 2 test cũ). Trạng thái vé: `docs/phieu-viec/mailbox/trang-thai.md`.

## 1. Đối chiếu từng việc vé yêu cầu

| # | Yêu cầu vé | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đổi default backend sang `onnx_fp32` (hoặc tên tương đương) | **Đã có sẵn, giữ nguyên** | `DEFAULT_BGE_BACKEND = "onnx"` tại `src/aios_habit/rag_v2/bge_onnx_backend.py:37` (đây là ONNX fp32; int8 tách riêng `onnx_int8`); alias `auto → onnx`; `RagV2DevConfig.bge_backend` mặc định theo hằng này (`pipeline.py:217`); adapter workspace-chat soi fingerprint theo cùng default (`workspace_chat_rag_v2_adapter.py:132`, `:598`); quét `src/` + `scripts/` không nơi nào truyền `bge_backend=` đè |
| 2 | Giữ `BGE_BACKEND` làm override | **Đã có sẵn** | probe runtime ở mục 2 |
| 3 | Fail-closed khi thiếu/sai model, không fallback lén | **Đã có sẵn** | `require_onnx_model_dir` (thiếu thư mục/tệp/checksum → `SemanticBackendUnavailable` kèm đường dẫn + gợi ý `BGE_BACKEND=pytorch`); `_resolve_embedding_backend` không có nhánh fallback; worker BGE báo `pinned_model_unavailable` |
| 4 | Viết 4 test theo danh sách | **3 test mới + 2 test siết setup** | mục 3 |
| 5 | Chạy full test liên quan, tất cả pass | **Đạt** | mục 4 |

Vì sao **không đổi tên literal** thành `onnx_fp32`: vé cho phép "tên tương đương"; đổi tên sẽ đổi giá trị `runtime_backend` trong `index_build_compatibility()` và descriptor → lệch fingerprint với chỉ mục thật đang có (107.331 chunk, fingerprint `016c5255…`) và phải embed lại toàn bộ. Vé cấm ghi index nên không đổi.

## 2. Probe runtime (không nạp model)

```
$ PYTHONPATH=src uv run --no-sync --group dev python -c "…resolve_bge_backend_name()…"
DEFAULT_BGE_BACKEND = onnx
unset      -> onnx
auto       -> onnx
pytorch    -> pytorch
onnx_int8  -> onnx_int8
bogus      -> SemanticBackendUnavailable: BGE_BACKEND must be pytorch, onnx, onnx_int8 or auto
```

## 3. Test

Test mới (commit `9de4cac`, `tests/test_rag_v2_bge_onnx.py`):

| Test | Kịch bản | Kết quả |
|---|---|---|
| `test_onnx_default_backend_runs_on_cpu_when_no_gpu_provider_exists` | Session mở đúng `providers=["CPUExecutionProvider"]` với tệp `model.onnx` (fp32), descriptor `device="cpu"`, embed ra vector khi máy không có provider GPU | pass |
| `test_onnx_default_backend_load_failure_is_fail_closed_with_clear_message` | ONNX load hỏng → `SemanticBackendUnavailable` lời rõ "failed to load" (không crash mù) | pass |
| `test_onnx_default_backend_reports_missing_onnxruntime_clearly` | Thiếu gói `onnxruntime` → lời rõ "onnxruntime is unavailable; install the retrieval-lab extra" | pass |

Siết 2 test cũ (commit `26a2d2b`, `tests/test_workspace_chat_backend_fingerprint_gate.py`) — **chỉ đổi setup, giữ nguyên assertion, không đổi mã nguồn**:

| Test | Trước | Sau |
|---|---|---|
| `test_expected_fingerprint_empty_without_model` | đỏ trên máy có cây model mặc định (fingerprint xác định được, khác `""` mong đợi) | trỏ `AIOS_BGE_ONNX_MODEL_PATH` vào thư mục thiếu → đúng nghĩa "thiếu model" → `""` (fail-closed) |
| `test_reconcile_preserves_row_when_backend_unknown` | đỏ cùng lý do | như trên → row READY giữ nguyên, gate báo `pending` |

Kiểm chứng đỏ-trước-xanh-sau:
- Mục 3 test mới: lật `providers` sang `CUDAExecutionProvider` + đổi 2 thông báo lỗi → **đúng 3 test đỏ**; hoàn nguyên → **20/20** xanh ở tệp backend.
- 2 test siết: đỏ ở baseline đã chứng minh độc lập bằng đối chứng stash (cất thay đổi của vé → vẫn đỏ y hệt) và bằng lần chạy toàn bộ trước khi siết; sau siết → **18/18** xanh ở tệp gate.

## 4. Cổng

- `uv run --no-sync --group dev python -m compileall -q src tests` → không lỗi.
- `PYTHONPATH=src … python -m aios_habit.cli audit` → `"status": "PASS"`, không lỗi, không cảnh báo.
- `PYTHONPATH=src … python -c "import aios_habit.workspace_chat_app"` → `IMPORT_OK`.
- Nhóm test liên quan (backend, worker/client, pipeline, migrate, gate): **75 đạt / 9 lỗi** — 9 lỗi đều là `bge_worker_init_stdout_eof` do thiếu `PYTHONPATH` trong tiến trình con; chạy lại 2 tệp worker + client với `PYTHONPATH` tuyệt đối → **16/16 đạt**.
- `pytest -q` toàn bộ (kèm `PYTHONPATH` trỏ `xlrd` như lần chạy E3): **3.265 đạt, 3 bỏ qua, 37 lỗi, 10 error** (221,41 giây). So lần chạy toàn bộ gần nhất của E3 trên cùng máy (`3.262 đạt / 37 lỗi / 10 error`): **+3 đạt đúng 3 test mới, số lỗi không đổi**; không bài nào đỏ ở vùng E4 (backend ONNX, CPU-only, fail-closed, gate fingerprint). 37 lỗi + 10 error còn lại là có sẵn (thiếu `graphifyy`, tiến trình BGE worker, `uv.lock`/đóng gói, thiếu dữ liệu `test_error_cases_f4`, nhóm workspace-chat, eval/mom pilot, fixtures) — cùng nhóm E3 đã liệt kê.

## 5. Smoke thật CPU-only (cây model thật)

- Không set env nào; `require_onnx_model_dir()` → `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32`.
- Session providers = `['CPUExecutionProvider']`; ORT máy này chỉ có `AzureExecutionProvider` + `CPUExecutionProvider` (không có CUDA) → "tắt GPU đi vẫn chạy" đúng nghĩa.
- Load model 26,99 giây (nguội), query 0,44 giây, dense 1024 chiều norm 1,0, sparse 20 token.
- Cache xác minh cây model còn nguyên (mtime `2026-09-27 01:15`, không băm lại 2,2 GB).

## 6. Ràng buộc vé

- Không ghi index, không embed, không `--apply`; không merge `main`; không hardcode GPU (session CPU-only, chứng minh ở mục 5).
- Chỉ sửa/tạo tệp test + tài liệu trong repo (ổ D), không ghi dữ liệu ngoài repo; tệp tạm trên ổ C (`C:/tmp/e3-py311` tái dùng cho `xlrd`).
- Cổng gate watcher: watcher tự mở OMP **1/4 lần** (`LAUNCH` lúc 01:45:08); vé làm được ngay trên máy này → cổng mở, OMP nhận vé ngay và cập nhật 4 mốc tiến độ; **không chuyển `cho-muse`, không quay no-op**. (Log watcher sau ~02:01 bị GitHub API 403 tạm thời — không ảnh hưởng `git push`/Muse.)

## 7. Đề xuất (ngoài phạm vi vé)

- Nhóm 37 lỗi + 10 error có sẵn của suite cần vé riêng xử lý (trùng đề xuất E3): thiếu `graphifyy==0.9.50`, tiến trình BGE worker trên Windows, `uv.lock` cần cập nhật, dữ liệu `test_error_cases_f4`, nhóm workspace-chat còn lại, eval/mom pilot.
- Muốn tuyệt đối hoá tên gọi `onnx_fp32` (thay vì `onnx`) cần vé riêng kèm kế hoạch embed lại chỉ mục — hiện không cần vì vé cho phép tên tương đương.
