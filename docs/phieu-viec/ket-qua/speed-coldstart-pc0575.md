# Báo cáo vé `SPEED-COLDSTART-PC0575` — sửa câu hỏi lạnh qua UI (~265 giây, bộ đọc khởi động 180,9 giây)

- Trạng thái: **CHẶN ĐO NGHIỆM THU — chuyển `cho-muse` ngày 2026-10-05** (mất dữ liệu runtime production trên PC0575; xem cập nhật đầu báo cáo).

> **Cập nhật 2026-10-05 15:32 +07 — vì sao chặn (MỚI NHẤT, đọc trước).**
> OMP nhận lại vé qua watcher (`LAUNCH 1/4` lúc 14:42); chuỗi trong ngày watcher đã tự mở/leo thang ≥4 lần liên tiếp không tiến triển (log `D:\Sandbox\agent-mailbox\watcher-mailbox-pc0575.log` 09:04→14:40, leo thang 4/4…8/4). Kiểm cổng gate trong phiên: **điều kiện mở KHÔNG còn — dữ liệu runtime của app đã biến mất khỏi PC0575**:
> - `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\` (index production SHA `e54c7745…`, 2.842.415.104 B, mtime 2026-10-01 15:46; ledger; log worker) và `local_runs\retrieval_models\bge-m3-5617a9f` (model) — **không còn** (`Test-Path` = False; thư mục `local_runs` hiện chỉ còn `dieu_tra` + `workspace_chat_rag_v2_canary` do test tạo lúc 15:14 hôm nay, KHÔNG có index production). Quét toàn ổ C và D không thấy bản `library.sqlite` production nào khác.
> - Audit chính thức của app: `.venv\Scripts\python.exe -B -m aios_habit.workspace_chat_rag_v2_deployment` (PYTHONPATH=src) → `Status: FAIL` / `deployment_model_unavailable`.
> - Bản còn lại trên máy: `C:\AIOS_p5\library.sqlite.bak-20260930` (2.552.659.968 B — bản `062ec090…` ngày 29–30/09, **không phải** bản production `e54c7745…`).
> - Hệ quả: bảng "Sau" mục 2, mục 4 (đo lạnh qua UI), mục 5 (parity) và mục 7 chưa thể hoàn tất; code P1–P4 (`2f52359` + `24973e7`) giữ nguyên giá trị — khi dữ liệu được khôi phục chỉ cần chạy lại các mục đo.
> - Trạng thái mailbox: `cho-muse` (theo đúng cổng gate "4 lần watcher" của user — không quay no-op). Đề xuất Muse/user: khôi phục dữ liệu runtime production lên PC0575 rồi phát hành lại vé đo.
- Máy: `KDTVN-PC0575` — Windows 11 Pro build `10.0.26200` x64, **CPU-only**, 16 GB RAM; app chạy theo deploy Bước 0–5 (`RUN_AIOS_WORKSPACE_CHAT.bat`, `AIOS_FEATURE_CHAT_ACTION=1`, `AIOS_ERROR_CASES_DB=C:\tmp\b0-dict\error_cases_dict.db`).
- Nhánh: `phieu-viec/rag-fix1`. Mã nguồn: `2f52359` (P1+P2) + `24973e7` (P3) — trong phiên **có sửa `src/` và `tests/`** theo đúng vé (vé yêu cầu sửa warm-up/init).
- Ràng buộc giữ nguyên: không merge `main`, không force-push, **không ghi index production**, không chạy `--apply`, index production mở **read-only**.

## 0. Cổng gate (vòng khép kín)

- Watcher PC0575 (`D:\Sandbox\agent-mailbox\`) tự mở OMP `LAUNCH 1/4` lúc **17:54:22** (`launchStallCount=1`) khi thấy vé `moi`; **điều kiện mở đã tới**: verdict `OPT-RAGV2-SPEED-APP-PC0575` **ĐẠT** (15:47) + app CPU-only đang chạy `/_stcore/health`=`ok` → OMP nhận vé (`dang-lam`, commit `bb8c0cf` 17:58 +07) — **không chạm ngưỡng “4 lần watcher”/`cho-muse`, không quay no-op**.
- Các mốc tiến độ được cập nhật + push đúng quy ước: `bb8c0cf` (nhận vé) → `2f52359`+`29f30c2` (P1+P2) → `24973e7`+`5886f4b` (P3+P4).

## 1. Phương pháp đo

| Đường đo | Có qua giao diện app? | Dùng cho |
|---|---|---|
| **UI app thật (Chromium thật)** — mở `?nb=NB-E35A7BEE&conv=CONV-9C730D76`, chọn cầu nối `2. C-AGENT API`, gõ câu hỏi vào ô “Câu hỏi gửi AI”, bấm nút “Hỏi”; thời gian lấy từ store `local_cases/workspace_chat/messages.jsonl` (mốc tin nhắn người dùng → tin nhắn trả lời) | **Có** | Câu lạnh/câu ấm qua UI sau restart (mục 4) |
| **Probe cùng pipeline (in-process)** — `scratch/opt_ragv2_lexical_verify_probe.py`, dựng `RagV2DevPipeline` trên index production, chạy 6 câu qua pipeline | **Không** (ghi rõ) | Parity top-15 + E1 15/15 (mục 5) |
| **Probe init worker thật** — `scratch/speed_app/probe_worker_init.py` (đúng client + config app, collection `tri_thuc` read-only) | **Không** | Bảng thời gian từng bước khởi động (mục 2) |
| **Log daemon bộ đọc** — `…/collections/tri_thuc/logs/bge_worker_daemon.stderr.log` in mốc từng pha (`model_verify/model_load/index_open/dense_preload/sparse_preload`) | — | Bảng khởi động “sau” trên app thật |

## 2. Bảng thời gian từng bước khởi động (trước → sau)

**Trước (baseline phiên này, mã cũ, index `tri_thuc` read-only):**

| Hạng mục | Số đo | Nguồn |
|---|---:|---|
| Init worker tổng (đĩa bận) | **408,5 s** | probe `baseline_before` 18:12 |
| — dense preload | 83,9 s (mốc sạch) / không tách trong lượt bận | báo cáo SPEED-APP + probe |
| — sparse preload | 85,6 s (mốc sạch) | báo cáo SPEED-APP |
| — model + mở index (phần dư) | ~11,4 s | suy ra từ 180,9 s và log init rỗng |
| Init worker tổng (mốc sạch 13:24) | **180,9 s** | báo cáo SPEED-APP đã duyệt |
| Câu L1 qua worker (đĩa bận) | 128,7 s | probe 18:21 |
| Câu lạnh đầu qua UI (mã cũ) | **~265 s → LỖI** | báo cáo SPEED-APP (2 lượt) |

**Sau (mã mới, cùng index, cùng máy):** _(điền từ log daemon + probe sau khi đo)_

| Hạng mục | Số đo | Nguồn |
|---|---:|---|
| Init worker tổng (app thật, lạnh hoàn toàn) | _PENDING_ | daemon log |
| — model_verify / model_load / index_open / dense / sparse | _PENDING_ | daemon log |

## 3. Thay đổi mã (tóm tắt)

1. **Đo pha init**: worker in `bge_worker_stage init_phases …` (model_verify/model_load/index_open/dense/sparse/cache_preload) và trả `phases_ms` trong readiness; `index.py` tách thêm `fetch_ms`/`build_ms` cho hai cache preload; adapter truyền `phases_ms` trong báo cáo an toàn. Các con số này phục vụ bảng mục 2 và các vé tối ưu sau.
2. **Warm-up đúng collection**: `ensure_workspace_chat_worker_warming`/`is_workspace_chat_worker_warmed`/`initialize_workspace_chat_rag_v2_worker` (mặc định) nay dựng `_pipeline_config(..., read_only=True, collection_id=<collection production>)` — trỏ đúng `…/collections/tri_thuc/library.sqlite` thay vì index “legacy” gốc profile; app mở lên tự làm nóng (nhánh `STREAMLIT_SERVER_PORT` cũ không bao giờ chạy trong deploy → nay kiểm tra thêm `streamlit.runtime.exists()`).
3. **Đồng bộ cửa sổ chờ**: thêm `AIOS_BGE_INIT_TIMEOUT` (mặc định 300 s, launcher đặt 300); **không bỏ rơi** tiến trình đang nạp khi hết hạn — lần gọi sau chờ tiếp trên cùng tiến trình (không spawn trùng); chờ init diễn ra ngoài lock nên luồng làm nóng nền + luồng câu hỏi cùng chờ một worker thay vì lỗi `worker_busy`.
4. **Giữ worker sống qua restart app** (điểm chính để câu lạnh đầu ≤ 60 s): worker mới `--serve` qua **named pipe** (`multiprocessing.connection`, tên pipe gắn `config + dấu vân tay mã nguồn`), chạy tách khỏi tiến trình app (detached, tự tắt sau `AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS` = 6 h); client chế độ mới `AIOS_RAGV2_WORKER_PERSIST=1` (đặt trong launcher) tự **gắn vào worker cũ** khi app khởi động lại, chỉ dùng cho config **query read-only** (đường chuẩn bị nguồn ghi vẫn dùng worker tạm như cũ). Có sẵn đường thoát: gỡ cờ khỏi `.bat` là quay lại cơ chế cũ, không cần sửa mã.
5. Test: `tests/test_bge_worker_persist.py` (worker sống qua restart, chặn config lệch, init timeout không bỏ rơi worker) + 2 test warm-up config trong `tests/test_workspace_chat_rag_v2_adapter.py`; vá 1 test G2 đỏ sẵn từ 28/09 (`test_reconcile_and_enqueue_preserves_ready_and_deduplicates`) theo đúng convention seed `model_fingerprint` của file.

## 4. Đo app thật (điền sau khi chạy xong)

### 4.1 Lạnh hoàn toàn (khởi động app sạch, hỏi ngay) — `coldstart_s1`
_PENDING_

### 4.2 Restart app nhiều lần, GIỮ worker sống (kịch bản người dùng thật) — ×3
_PENDING_

### 4.3 Đủ 6 câu L1–E3 qua UI
_PENDING_

## 5. Parity + E1 + toàn vẹn

_PENDING_

## 6. Cổng chất lượng

- `compileall src tests`: **PASS** (20:0x).
- `pytest -q`: 3647 passed / 37 skipped; **18 failed + 19 errors** — **đã chứng minh pre-existing/environment**: chạy lại đúng bộ file đó với `src` revert về `bb8c0cf` cho **cùng 18 tên fail**; 19 errors là thiếu dữ liệu VM (`\home\hatch\workspace\aios_data\…`), 6 fail là model-pack checksum chưa duyệt trên máy này, còn lại là mạng/OCR/privacy khi thiếu provider — không liên quan thay đổi của vé.
- `cli audit`: **PASS** (`"status": "PASS"`, không lỗi/cảnh báo).
- `import aios_habit.workspace_chat_app`: **OK**.

## 7. An toàn dữ liệu

_PENDING — SHA index trước/sau, health, không ghi index._

## 8. Kết luận & đề xuất

_PENDING_

## 9. Bằng chứng

- `scratch/speed_app/pc0575_coldstart_restart.ps1`, `read_chat_times.py`, `persist_smoke.py`, `app_coldstart_s1.log`.
- `scratch/speed_app/worker_init_baseline_before.json` (baseline trước).
- Daemon log: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/logs/bge_worker_daemon.stderr.log`.
- Parity: `scratch/opt_ragv2_lexical_<label>.json` + `scratch/opt_ragv2_lexical_compare.py`.
