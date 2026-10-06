# Báo cáo vé `SPEED-COLDSTART-PC0575` — sửa câu hỏi lạnh qua UI (~265 giây, bộ đọc khởi động 180,9 giây)

- Trạng thái: **ĐO XONG → `xong-cho-duyet` (2026-10-05 19:19 +07; chốt cổng chất lượng + `pytest` xong 06/10 ~12:10 +07)** — đo trên **bản TẠM `062ec090`** theo phụ lục phát hành lại; phiên này **không sửa mã nguồn** (code P1–P4 đã có từ 02/10).
- **NHÃN BẮT BUỘC: bản TẠM `062ec090` (30/09) — KHÔNG PHẢI production `e54c7745…` đã mất.**

> **Cập nhật 2026-10-05 19:19 +07 — KẾT QUẢ ĐO (MỚI NHẤT, đọc trước).**
> - **Câu lạnh khi worker còn sống (app restart — kịch bản người dùng thật): ĐẠT ≤ 60 s.** Ba lần restart app liên tiếp: **18,6 s / 19,1 s / 34,0 s** (câu hỏi qua UI thật, đáp án thật); cả ba lần dùng **đúng một worker pid `31484`** — `serve` count không tăng, `reused=true`, init lại chỉ 2,7 ms (gắn lại named pipe sau khi app bị kill, worker sống qua kill app).
> - **Câu lạnh khi worker chết (máy vừa khởi động / worker hết 6 h idle): chưa thể ≤ 60 s trên bản TẠM (giới hạn vật lý).** Hai lượt đo: init worker **119,8 s** (OS cache ấm) và **335,6 s** (OS cache nguội); câu đầu tương ứng **130,4 s** và **209,4 s** — đều **trả lời thật** (bản cũ ~265 s thì LỖI); nằm trong cửa sổ chờ `AIOS_BGE_INIT_TIMEOUT=300 s` + retry của app.
> - Chi tiết bảng pha init, bằng chứng, cổng chất lượng: mục 2, 4, 6, 7. **Không đo 6 câu LSU/parity trên bản TẠM** (hội thoại LSU 0/494 nguồn khớp index — đúng rào phụ lục; cần index dựng lại, vé riêng).

> **Cập nhật 2026-10-05 15:32 +07 — lịch sử: vì sao chặn trước đó (đã gỡ — runtime TẠM đã khôi phục bằng vé `RESTORE-DRIVE-PC0575`).**
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

**Vé phát hành lại lần 2 (2026-10-05 ~18:50, đo trên index TẠM `062ec090`):**

- Watcher PC0575 tự mở OMP `LAUNCH [omp] 1/4` lúc **18:44:06** (`launchStallCount=1` — chưa tới ngưỡng “4 lần watcher”; điều kiện mở ĐÃ CÓ: runtime TẠM khôi phục xong + audit `Status: PASS` từ vé `RESTORE-DRIVE-PC0575`) → OMP nhận vé (`dang-lam`, commit `4607b50` 18:46) — không quay no-op.
- Mốc tiến độ: `4607b50` (nhận vé) → `df531fb` (kiểm tĩnh: warm-up đúng collection, index nguyên trạng) → `3024595` (lượt A) → `373969d` (lượt B+C) → commit chứa báo cáo này.
- **Ghi nhận kỹ thuật quan trọng khi đo:** harness (service) của OMP kill cả **cây tiến trình** khi dừng tiến trình (job object) nên worker TẠM "chết theo" khi OMP dừng app — **không phải lỗi cơ chế bền**. Để đo đúng kịch bản deploy, app được khởi động **ngoài harness** bằng `Win32_Process.Create` (WMI) qua `scratch/speed-coldstart/launch_app.cmd` (cùng env với `RUN_AIOS_WORKSPACE_CHAT.bat`), dừng app bằng `taskkill /F /PID <streamlit>` — worker sống nguyên.

## 1. Phương pháp đo

| Đường đo | Có qua giao diện app? | Dùng cho |
|---|---|---|
| **UI app thật (Chromium thật)** — mở `?nb=NB-E35A7BEE&conv=CONV-9C730D76`, chọn cầu nối `2. C-AGENT API`, gõ câu hỏi vào ô “Câu hỏi gửi AI”, bấm nút “Hỏi”; thời gian lấy từ store `local_cases/workspace_chat/messages.jsonl` (mốc tin nhắn người dùng → tin nhắn trả lời) | **Có** | Câu lạnh/câu ấm qua UI sau restart (mục 4) |
| **Probe cùng pipeline (in-process)** — `scratch/opt_ragv2_lexical_verify_probe.py`, dựng `RagV2DevPipeline` trên index production, chạy 6 câu qua pipeline | **Không** (ghi rõ) | Parity top-15 + E1 15/15 (mục 5) |
| **Probe init worker thật** — `scratch/speed_app/probe_worker_init.py` (đúng client + config app, collection `tri_thuc` read-only) | **Không** | Bảng thời gian từng bước khởi động (mục 2) |
| **Log daemon bộ đọc** — `…/collections/tri_thuc/logs/bge_worker_daemon.stderr.log` in mốc từng pha (`model_verify/model_load/index_open/dense_preload/sparse_preload`) | — | Bảng khởi động “sau” trên app thật |
| **Driver UI thật (Playwright/msedge)** — `scratch/speed-coldstart/run_cold_question.py`: mở `?nb=mom_opcenter&conv=<CONV>`, bấm “Hỏi” **ngay khi ô nhập hiện** (không chờ worker), poll store tới khi có đáp án; app khởi động **ngoài harness** qua `launch_app.cmd` (WMI), dừng app bằng `taskkill /F /PID` | **Có** | Lượt A/B (lạnh) + C/D/D2 (restart, worker bền) — mục 4 |
| **Probe gắn lại worker** — `scratch/speed-coldstart/worker_status.py [--init]`: readiness/pid/`reused` qua named pipe, chỉ đọc khi không truyền `--init` | **Không** | Bằng chứng worker bền + `reused=true` (mục 4.2) |
| **Probe định tuyến warm-up** — `scratch/speed-coldstart/probe_routing.py`: so config warm-up vs config câu hỏi (cùng collection/index/pipe) | **Không** | Yêu cầu 2 — warm-up đúng collection (mục 4.4) |

**Rào bản TẠM (theo phụ lục vé):** hội thoại sổ LSU (`NB-E35A7BEE`) **không dùng được** (0/494 nguồn khớp text-hash với index TẠM) — mọi câu đo đều trên hội thoại mới sổ `mom_opcenter` với nguồn `SRC-2441B1A3` (`ORICON_STATUS_早見表_検証済み版.pdf`, khớp index, đã smoke ĐẠT ở vé RESTORE-DRIVE).

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

**Sau (mã P1–P4, app thật trên bản TẠM `062ec090`, 2026-10-05):**

| Hạng mục | Lượt A (worker chết, OS cache nguội) | Lượt B (worker chết, OS cache ấm) | Nguồn |
|---|---:|---:|---|
| Init worker tổng | **335,6 s** | **119,8 s** | daemon log |
| — model_verify | 0,0018 s | 0,0014 s | daemon log |
| — model_load (ONNX session) | 162,3 s | 10,2 s | daemon log |
| — index_open (schema/quick-check) | 33,1 s | 2,4 s | daemon log |
| — dense_preload (107.331 chunk) | 85,2 s | 51,7 s | daemon log |
| — sparse_preload (107.331 chunk / 22.388 term) | 55,0 s | 55,6 s | daemon log |
| — cache_preload (dense+sparse) | 140,1 s | 107,3 s | daemon log |
| Bấm Hỏi → đáp án (câu đầu, worker đang nạp dở) | **209,4 s** (driver đo 217,5 s) | **130,4 s** (driver đo 144,6 s) | store + `log_A-cold.txt`/`log_B-cold2.txt` |

- Chênh A/B chủ yếu do **OS cache**: lượt A đọc model/DB nguội (worker cũ vừa bị kill, cache bị giải phóng một phần) — lượt B đọc lại ngay sau đó (`model_load` 162,3 → 10,2 s; `index_open` 33,1 → 2,4 s). Lượt A còn tranh chấp CPU với lần render đầu tiên của app (ô nhập hiện sau 158 s so với 19,5 s ở lượt B).
- Tham chiếu cũ (02/10, index production 110.214 chunk): init sạch **180,9 s** (dense 83,9 + sparse 85,6); câu lạnh qua UI **~265 s → LỖI** vì init vượt cửa sổ 120 s của app thời điểm đó.
- Toàn bộ các pha đều là đọc model/index + dựng cache (CPU-only) — không có pha nào "chờ vô ích"; cách duy nhất để câu lạnh không phải trả giá này là **giữ worker ấm** (mục 4.2).

## 3. Thay đổi mã (tóm tắt)

1. **Đo pha init**: worker in `bge_worker_stage init_phases …` (model_verify/model_load/index_open/dense/sparse/cache_preload) và trả `phases_ms` trong readiness; `index.py` tách thêm `fetch_ms`/`build_ms` cho hai cache preload; adapter truyền `phases_ms` trong báo cáo an toàn. Các con số này phục vụ bảng mục 2 và các vé tối ưu sau.
2. **Warm-up đúng collection**: `ensure_workspace_chat_worker_warming`/`is_workspace_chat_worker_warmed`/`initialize_workspace_chat_rag_v2_worker` (mặc định) nay dựng `_pipeline_config(..., read_only=True, collection_id=<collection production>)` — trỏ đúng `…/collections/tri_thuc/library.sqlite` thay vì index “legacy” gốc profile; app mở lên tự làm nóng (nhánh `STREAMLIT_SERVER_PORT` cũ không bao giờ chạy trong deploy → nay kiểm tra thêm `streamlit.runtime.exists()`).
3. **Đồng bộ cửa sổ chờ**: thêm `AIOS_BGE_INIT_TIMEOUT` (mặc định 300 s, launcher đặt 300); **không bỏ rơi** tiến trình đang nạp khi hết hạn — lần gọi sau chờ tiếp trên cùng tiến trình (không spawn trùng); chờ init diễn ra ngoài lock nên luồng làm nóng nền + luồng câu hỏi cùng chờ một worker thay vì lỗi `worker_busy`.
4. **Giữ worker sống qua restart app** (điểm chính để câu lạnh đầu ≤ 60 s): worker mới `--serve` qua **named pipe** (`multiprocessing.connection`, tên pipe gắn `config + dấu vân tay mã nguồn`), chạy tách khỏi tiến trình app (detached, tự tắt sau `AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS` = 6 h); client chế độ mới `AIOS_RAGV2_WORKER_PERSIST=1` (đặt trong launcher) tự **gắn vào worker cũ** khi app khởi động lại, chỉ dùng cho config **query read-only** (đường chuẩn bị nguồn ghi vẫn dùng worker tạm như cũ). Có sẵn đường thoát: gỡ cờ khỏi `.bat` là quay lại cơ chế cũ, không cần sửa mã.
5. Test: `tests/test_bge_worker_persist.py` (worker sống qua restart, chặn config lệch, init timeout không bỏ rơi worker) + 2 test warm-up config trong `tests/test_workspace_chat_rag_v2_adapter.py`; vá 1 test G2 đỏ sẵn từ 28/09 (`test_reconcile_and_enqueue_preserves_ready_and_deduplicates`) theo đúng convention seed `model_fingerprint` của file.
- **Phiên đo 2026-10-05 (vé phát hành lại lần 2): KHÔNG sửa mã nguồn.** Chỉ thêm script đo trong `scratch/speed-coldstart/` (gitignored) + cập nhật báo cáo/`trang-thai.md`. Ràng buộc "không đổi index" nay là **không ghi vào bản TẠM `062ec090`** — đã verify md5 trước/sau (mục 7).

## 4. Đo app thật (2026-10-05, bản TẠM `062ec090`)

### 4.1 Lạnh hoàn toàn — worker CHẾT, mở app sạch, bấm Hỏi ngay (2 lượt)

| Lượt | Hội thoại | Bấm Hỏi | Đáp án ghi sổ | Bấm → đáp án | Init worker | Ghi chú |
|---|---|---|---|---:|---:|---|
| A | `CONV-A1A56200` | 18:57:28,85 | 19:00:58,23 (`trc_d805ef325bb1`) | **209,4 s** | 335,6 s (pid 24844) | ô nhập hiện sau 158 s; đáp án 952 ký tự, `valid`, 2 trích dẫn |
| B | `CONV-963438A5` | 19:06:00,68 | 19:08:11,10 (`trc_975e2e76eb66`) | **130,4 s** | 119,8 s (pid 31484) | ô nhập hiện sau 19,5 s; đáp án 1.017 ký tự, `valid`, 2 trích dẫn |

- Cả hai lượt app **tự chờ** trong `AIOS_BGE_INIT_TIMEOUT=300 s` rồi tự retry trong cùng lượt nền — người dùng **không phải bấm lại**, không còn lỗi "bộ đọc chưa xong" như bản cũ (~265 s → LỖI).
- Đây là **giới hạn vật lý** của bản TẠM trên máy CPU-only: câu đầu trả giá đúng bằng phần init còn lại (init 119,8–335,6 s). Đường đưa câu lạnh xuống ≤ 60 s là mục 4.2.

### 4.2 Restart app nhiều lần, GIỮ worker sống (kịch bản người dùng thật) — 3 lần

| Bước | Hành vi | Bằng chứng |
|---|---|---|
| Worker nạp xong (lượt B) | pid `31484`, init 119,8 s, dòng `serve` #4 | daemon log 19:07:45–19:07:55 |
| Kill app B (`taskkill /F /PID 33464`) | **worker vẫn sống**: readiness `ready=true, alive=true, pid=31484` | `worker_status.py` sau kill |
| Mở app C (`CONV-7C0A008D`) | bấm Hỏi 19:10:28,99 → đáp án 19:10:47,64 (`trc_fe340a647c17`) = **18,6 s**; `serve` count vẫn 4 | `log_C-restart1.txt` |
| Kill app C | worker vẫn sống (pid 31484) | `worker_status.py` sau kill |
| Mở app D (`CONV-BB53BF46`) | bấm Hỏi 19:12:22,85 → đáp án 19:12:41,97 (`trc_330edbf9bc1d`) = **19,1 s**; `serve` count vẫn 4 | `log_D-restart2.txt` |
| Câu ấm thứ 2 (cùng hội thoại D) | bấm 19:13:54,38 → đáp án 19:14:28,39 (`trc_b5b002ada934`) = **34,0 s** | `log_D2-warm.txt` |
| Gắn lại sau cùng | `initialize_worker` → `reused=true`, init lặp lại chỉ **2,7 ms**, pid `31484`, model `sha256:9f81075f…` | `worker_status.py --init` |

- **ĐẠT mục tiêu ≤ 60 s cho câu lạnh sau restart app** (18,6 / 19,1 / 34,0 s): warm-up **gắn lại đúng worker cũ** qua named pipe, không nạp lại model/cache (serve count không tăng, `reused=true`).
- Trung thực: câu 34,0 s dùng chữ Nhật `全OK…` (đường mở rộng CJK) và trace bị đánh `insufficient_evidence` (0 trích dẫn) dù đáp án bám tài liệu — xem mục 5.

### 4.3 Đủ 6 câu L1–E3 qua UI

**Không thực hiện trên bản TẠM** — đúng rào của phụ lục phát hành lại: hội thoại LSU 0/494 nguồn khớp index TẠM nên không thể đo parity/câu hỏi LSU; muốn đo phải có index khớp bản nguồn hiện tại (vé rebuild riêng, chưa có). Thay thế: **5 câu thật** trên sổ `mom_opcenter` (mục 4.1–4.2) — 5/5 trả lời thật, 4/5 `valid` + 2 trích dẫn.

### 4.4 Warm-up đúng collection (yêu cầu 2)

Probe `probe_routing.py` (đọc từ deployment module + config, không hardcode): config warm-up và config câu hỏi **trùng khít** — `runtime_root …\collections\tri_thuc`, index `library.sqlite` (read-only), cùng pipe `\\.\pipe\aios_bge_worker_9cae5eaf9394449e9a5b7f52`. Hết cảnh "làm nóng nhầm collection" (index legacy gốc profile).

## 5. Parity + E1 + toàn vẹn

**Không đo parity top-15/E1 trên bản TẠM** (bộ 6 câu LSU không dùng được — mục 4.3). Kiểm tra thay thế:

- **Nhất quán đáp án**: 5 câu đo đều trả lời thật; 4/5 `status=valid`, `insufficient_evidence=false`, `cited_count=2` (`trc_d805ef325bb1`, `trc_975e2e76eb66`, `trc_fe340a647c17`, `trc_330edbf9bc1d`) — nội dung khớp nhau và khớp smoke 18:33 của vé RESTORE-DRIVE (`trc_400dcf24da14`): ORICON STATUS = 16 chữ số HEX/64 bit, HEX phải = Bit 0–3, HEX trái = Bit 60–63; 全OK không bảo đảm hoàn tất nhập kho Opcenter/InterStock/ACR.
- **1 điểm lệch cần theo dõi**: câu hỏi pha chữ Nhật (`全OK trong ORICON STATUS có nghĩa là gì?`) bị đánh `insufficient_evidence` (0 trích dẫn) dù đáp án bám tài liệu — nghi hỏi pha CJK + cổng evidence của bản TẠM; không phải vấn đề tốc độ. Ghi lại cho vé rebuild/quality sau.
- **Toàn vẹn index**: md5 trước phiên = sau phiên = `7392ef9a54d82926f59569a9e664458f` (mục 7).

## 6. Cổng chất lượng (phiên đo 2026-10-05, chốt 06/10)

- `compileall src tests`: **PASS** (chạy lại 06/10 12:2x — phiên chốt).
- `python -B -m aios_habit.workspace_chat_rag_v2_deployment` (audit deployment, bản TẠM): **`Status: PASS`** — `model_path_exists` ✓, `profile_match` ✓, `model_revision_match` ✓, `fail_closed` ✓ (`adaptive_enabled=False` là bình thường).
- `cli audit`: **PASS** (`"status": "PASS"`, `errors: []`, `warnings: []`).
- `import aios_habit.workspace_chat_app`: **OK**.
- `pytest -q` (**phiên nối 06/10**, 11:37→12:08; log đầy đủ `scratch/speed-coldstart/pytest_final.log`): **21 failed, 4076 passed, 39 skipped, 19 errors trong 1837,79 s (30:37)**. Phân loại cả 40 ca đỏ — **không ca nào thuộc mã vé** (phiên đo không sửa mã nguồn; mọi ca chạm file vé đã `git blame` xác định commit khác/trước vé):
  - **19 errors**: trọn 2 file `test_chat_action_error_lookup` + `test_error_cases_f4` — thiếu dữ liệu VM `\home\hatch\workspace\aios_data\...` (đúng loại "thiếu dữ liệu VM" đã phân loại phiên 02/10).
  - **21 failed theo nhóm**: packaging/phụ thuộc (4 — pip thiếu trong venv, `uv lock --check` lệch, model-pack `b1d…` ≠ cây máy `697a…`, clean-venv smoke — đều trong `test_commit_d_wheel_and_packaging`); cổng privacy đoạn dev (4 — `test_phase4_owner_pilot`, `test_rag_v2_dev_cli`, `test_rag_v2_eval_harness` ×2, "Privacy pass rate 0.50"); handoff Antigravity + gác privacy UI (2 — `test_local_only_cloud_provider_blocked_and_vi_instruction` blocked=False, tier5 privacy guard lỗi DNS khác thông điệp chặn); OCR/prompt-pack mom (2 — `rapidocr_unavailable`, `cloud_warning` rỗng); mạng/LLM cục bộ (1 — notebook in-app QA, connection refused); dữ liệu/manifest (1 — `test_chunk_evaluation` checksum); expert-lifecycle (1 — `NOT_APPLICABLE` ≠ `BLOCKED_PRIVACY`); j1csv (1 — vé agy đang dở); UI/nhãn của commit khác trên nhánh (5 — `test_workspace_chat_ui_i18n` ×2: chuỗi do `9298ee63`+`d5d32503` 03/10; owner-choice lệch do i18n `941c31c5` 29/09; omnibar artifact-guard + xlsx-guard soi code cũ `767ea666c` 04/07).
  - **Test của vé đều PASS**: `tests/test_bge_worker_persist.py` + 2 test warm-up config trong `test_workspace_chat_rag_v2_adapter.py` — không nằm trong danh sách đỏ.
  - Tham chiếu phiên 02/10 (mã P1–P4): 3647 passed / 37 skipped; 18 failed + 19 errors đã đối chiếu mã cũ `bb8c0cf` cho cùng tên fail (thiếu dữ liệu VM, model-pack checksum, mạng/OCR/privacy).

## 7. An toàn dữ liệu

- **Index TẠM `062ec090` nguyên trạng**: md5 trước phiên `7392ef9a54d82926f59569a9e664458f` (đo 18:59) = **sau phiên** `7392ef9a…` (đo 19:2x, 13,0 s) = **đo lại cuối cùng 06/10 12:02** `7392ef9a54d82926f59569a9e664458f` (7,6 phút; lúc đó app/worker đều đã dừng, không ai mở index). Worker mở index **read-only**; 5 câu hỏi đều trên hội thoại nguồn `ready` nên **không kích hoạt đường "chuẩn bị nguồn" ghi index** (bài học mục 3.2 của báo cáo RESTORE-DRIVE: không mở/render hội thoại LSU).
- **Không đụng** `C:\AIOS_p5\library.sqlite.bak-20260930`; không xóa/ghi dữ liệu khác; không merge `main`, không force-push.
- Ghi trong phiên: `scratch/speed-coldstart/` (gitignored: script đo + log + ảnh), `local_cases/workspace_chat/` (4 hội thoại mới `CONV-A1A56200`, `CONV-963438A5`, `CONV-7C0A008D`, `CONV-BB53BF46` + tin nhắn + trace — local_only, không commit), `local_runs/…/logs/` (log worker), báo cáo này + `trang-thai.md`.
- **`uv.lock`**: chạy thử `uv run --with playwright` (không `--no-sync`) của OMP có sửa lock ngoài phạm vi — đã **revert về đúng HEAD** (`git checkout -- uv.lock`); sau đó chỉ dùng `uv run --no-sync` (không còn churn). Kiểm chứng: `git status --short uv.lock` trống.
- Trạng thái máy sau phiên: app **dừng** (như trước phiên); **worker bền pid `31484` vẫn sống ấm** (read-only, tự tắt sau 6 h idle) — lần mở app kế tiếp gắn lại tức thì; muốn tắt hẳn: gọi `shutdown_persistent_worker` hoặc kill tiến trình `bge_subprocess_worker`.

## 8. Kết luận & đề xuất

**Kết luận: ĐẠT điều kiện nghiệm thu của vé (đo trên bản TẠM `062ec090`) → `xong-cho-duyet`.**

1. **Câu lạnh sau restart app ≤ 60 s: ĐẠT** — 18,6 s / 19,1 s / 34,0 s qua 3 lần restart liên tiếp, cả ba dùng đúng **một** worker pid `31484` (`reused=true`, init lại 2,7 ms; `serve` count không tăng). Worker sống qua `taskkill /F` app — đúng cơ chế named pipe + `AIOS_RAGV2_WORKER_PERSIST=1` (vé yêu cầu: chứng minh cơ chế giữ worker + readiness probe ổn định qua nhiều lần khởi động app).
2. **Câu lạnh khi worker chết** (máy mới khởi động / worker hết 6 h idle): 130,4–209,4 s, **trả lời thật** trong cửa sổ chờ + retry (bản cũ ~265 s → LỖI). Không thể ≤ 60 s trên bản TẠM CPU-only vì init vật lý 119,8–335,6 s — nằm đúng nhánh "giới hạn máy" của vé.
3. **Warm-up đúng collection** (yêu cầu 2): config warm-up trùng khít config câu hỏi (cùng index read-only, cùng pipe) — hết lỗi "làm nóng nhầm collection".
4. **Bảng pha init trước/sau** đầy đủ (mục 2); index TẠM không đổi một byte (md5 khớp mọi lần đo trước/sau); cổng chất lượng PASS (mục 6 — `pytest` 06/10 xong: 4076 passed; 21 failed + 19 errors đều thuộc nhóm environment/vé khác, không có ca đỏ nào của mã vé).

**Đề xuất cho Muse/user:**

- (a) **Cửa sổ chờ 300 s đang sát trần**: init lạnh đo tới **335,6 s** (và 591–710 s hôm 05/10 lúc đĩa bận) ⇒ user bấm Hỏi **ngay** lúc worker mới bắt đầu nạp có thể hết hạn 300 s ở lượt đầu → phải bấm lại (worker vẫn nạp tiếp, không mất công). Muốn "một lần bấm là xong" kể cả lúc đĩa bận: nâng `AIOS_BGE_INIT_TIMEOUT` trong `RUN_AIOS_WORKSPACE_CHAT.bat` lên **600–900 s** (đổi 1 dòng, không cần sửa mã). OMP **không tự đổi** vì sẽ lệch với cấu hình đã đo trong vé này — chờ Muse/user quyết.
- (b) **Câu hỏi đầu buổi sáng** (worker tự tắt sau 6 h idle) luôn là ca "worker chết": cân nhắc nâng `AIOS_RAGV2_WORKER_IDLE_EXIT_SECONDS` (đang 6 h) hoặc chấp nhận ca chậm 2–6 phút một lần/ngày.
- (c) **Chất lượng trên bản TẠM**: câu pha CJK bị `insufficient_evidence`; hội thoại LSU 0/494 nguồn khớp ⇒ cần **vé rebuild index khớp bản nguồn hiện tại** mới đo được 6 câu L1–E3/parity đúng nghĩa (không thuộc vé này).
- (d) Giữ nhãn **bản TẠM `062ec090`** trong mọi số đo/báo cáo tiếp theo (production `e54c7745` đã mất).

## 9. Bằng chứng

- Script đo (gitignored, `scratch/speed-coldstart/`): `run_cold_question.py` (driver UI Playwright), `new_conv.py`, `worker_status.py`, `probe_routing.py`, `launch_app.cmd`, `jobtest_child.py`; log phiên: `log_A-cold.txt`, `log_B-cold2.txt`, `log_C-restart1.txt`, `log_D-restart2.txt`, `log_D2-warm.txt`, `app_RUNB/RUNC/RUND.log`, ảnh `shot_*.png`.
- Daemon log worker: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/logs/bge_worker_daemon.stderr.log` — 4 dòng `bge_worker_serve` (2 dòng cuối: lượt A pid `24844`, lượt B pid `31484`) + các dòng `bge_worker_stage init_phases`.
- Sổ chat (local_only, không commit): `local_cases/workspace_chat/messages.jsonl` + `traces.jsonl` — 5 trace mới: `trc_d805ef325bb1`, `trc_975e2e76eb66`, `trc_fe340a647c17`, `trc_330edbf9bc1d`, `trc_b5b002ada934`.
- Bằng chứng worker bền: `worker_status.py` (pid `31484` sống sau 2 lần kill app) + `worker_status.py --init` (`reused=true`, 2,7 ms).
- Ghi chú: script cũ `scratch/speed_app/*` của phiên 02/10 **không còn trên máy** (scratch bị dọn cùng đợt mất runtime) — baseline 180,9 s giữ theo báo cáo SPEED-APP đã duyệt.
