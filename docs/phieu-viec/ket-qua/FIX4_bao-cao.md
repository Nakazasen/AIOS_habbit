# FIX 4 — Báo cáo fallback bền cho drain chuẩn bị nguồn

## 1. Tóm tắt thay đổi

Sửa `src/aios_habit/workspace_chat_rag_v2_adapter.py`. Drain vẫn đọc `_SOURCE_CACHE` trước. Khi `AIOS_RAG_V2_DRAIN_DURABLE_FALLBACK` bật và cache không có text, `_load_durable_context_source` đọc `notebook_sources.jsonl` hoặc `temporary_sources.jsonl` theo `source_scope` + `source_id`. Chỉ còn ghi `source_text_unavailable` khi bản ghi bền cũng không có text. Flag tắt thì đường cũ giữ nguyên.

Test: `tests/test_workspace_chat_rag_v2_adapter.py::test_drain_reloads_durable_text_only_when_flag_is_on`.

## 2. Bảng benchmark trước/sau

Vector dày đếm trên chunk `retrievable=1` trong `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`. Trước lấy từ báo cáo bổ sung cùng ngày. Sau đo lúc `MAX(created_at) = 2026-09-25T05:34:08.410009+00:00`.

| Mã | `wsc-*` | Vector trước | Vector sau | Sổ cái notebook sau |
| --- | --- | ---: | ---: | --- |
| F01 | `wsc-50e045acef39dbcd38aff8fb` | 0 | 14 | ready |
| F02 | `wsc-f5317d657bb48200fe0fa217` | 0 | 3 | ready |
| F03 | `wsc-72b177b9dab655fc0371095f` | 0 | 44 | ready |
| F04 | `wsc-a6d76176e0998559e07f7072` | 0 | 25 | ready |
| F05 | `wsc-51548ca220d6ccc9ec419c8c` | 0 | 58 | ready |
| F06 | `wsc-015a1b6d9a94dc147ca10588` | 0 | 30 | ready |
| F07 | `wsc-1e085174af345d01afbf88d6` | 78 | 78 | ready |
| F08 | `wsc-6349bfab87ce7a5eb246e10f` | 9 | 9 | ready |
| F09 | `wsc-2d528c22ed8a8466fba9c9bd` | 0 | 84 | ready |
| F10 | `wsc-d320e16fa80ee7e311b42fb7` | 3 | 3 | ready |
| F11 | `wsc-b4f7ba061c5c7e3bb4b84eb3` | 0 | 29 | ready |
| F12 | `wsc-e9d27b6c728c286f2cf0ef93` | 10 | 10 | ready |

12/12 có vector dày > 0. Sáu dòng temporary F02–F06 và F09 cũng `ready`, `last_error` rỗng. Không còn `failed` / `source_text_unavailable` cho 12 file này.

`prepare_workspace_chat_sources` cho 8 file F01, F02, F03, F04, F05, F06, F09, F11 mất 2474233.361 ms. F07, F08, F10, F12 đã có vector từ lần bổ sung trước, không nhúng lại.

Toàn sổ cái vẫn còn 940 dòng `failed` / `source_text_unavailable` của nguồn khác. Không drain hàng pending còn lại.

## 3. So sánh chất lượng

Không đo recall. Tiêu chí của fix này là vector và sổ cái. Trước: 6 file 0 vector và F01/F11 vô hình trong collection. Sau: đủ 12 mã `wsc-*` có vector dày trong `library.sqlite` của `tri_thuc`.

## 4. Kết quả `pytest tests/`

`pytest -q tests` trong 467.81 giây: **3125 passed, 3 skipped, 4 failed**. Không có test mới nào đỏ. `test_drain_reloads_durable_text_only_when_flag_is_on` nằm trong số passed.

Bốn lỗi không nằm trong diff của FIX 4, cùng lớp đã ghi ở FIX 2 và FIX 3:

- `tests/test_commit_d_wheel_and_packaging.py::TestDependencyManifestLockIntegrity::test_uv_lock_check_succeeds`: `uv lock --check` báo lockfile cần cập nhật.
- `tests/test_commit_d_wheel_and_packaging.py::TestBgeM3ModelPackPackaging::test_bge_m3_model_pack_verification_and_discovery`: cây model cục bộ hash ra `sha256:697a97c…`, test cứng pin cũ.
- `tests/test_commit_d_wheel_and_packaging.py::TestCleanMachineSmokeScript::test_clean_machine_full_isolated_venv_installation`: pip không tìm thấy `streamlit>=1.60.0`.
- `tests/test_mom_local_pilot.py::test_document_extractor_png_ocr_local_or_safe_unsupported`: lỗi phụ thuộc thứ tự đã ghi từ trước.

## 5. Flag rollback

- `AIOS_RAG_V2_DRAIN_DURABLE_FALLBACK`: mặc định không đặt, tức tắt. `1` / `true` / `yes` / `on` bật. Tắt là drain chỉ dùng cache RAM và vẫn fail `source_text_unavailable` khi cache trống.
- Không đổi `BGE_BACKEND` và `AIOS_RAG_V2_SUMMARY_FIRST`.

## 6. Điểm khác với yêu cầu

- Không gọi `_drain_preparation_queue` trên sổ cái thật. Hàng đó còn nguồn `pending` khác. Drain toàn cục sẽ nhúng hoặc fail những nguồn đó.
- Drain theo `source_scope=temporary` ghi vào sqlite hồ sơ, không vào collection `tri_thuc`. Vì vậy 6 file được nhúng từ bản ghi notebook, không từ dòng temporary. Dòng temporary được đánh `ready` sau khi vector đã có, để drain sau không fail lại.
- Trước khi nhúng, đã dừng `python.exe` PID 23308, là Workspace Chat (`streamlit run src\aios_habit\workspace_chat_app.py`) đang giữ `.aios-library-writer.lock`. Không có drain nào khác chạy trong lúc đếm.

## 7. Đánh giá

Đạt phần code và phần vector: flag mặc định tắt, test khóa cả hai phía, 12/12 file MOM có vector dày > 0 trong collection `tri_thuc`. Chưa gọi là đã dọn toàn bộ sổ cái, vì các nguồn khác vẫn `source_text_unavailable` khi flag tắt.
