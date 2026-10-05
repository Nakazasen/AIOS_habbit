# Báo cáo vé `RESTORE-DRIVE-PC0575` — khôi phục runtime TẠM từ Drive (bản cũ `062ec090` 30/09)

- Máy: `KDTVN-PC0575` (Windows 11 Pro build `10.0.26200` x64, **CPU-only**), user `kdtvn\tvn183660`.
- Nhánh: `phieu-viec/rag-fix1`. Thời gian thực hiện: 2026-10-05 ~16:50–18:45 +07.
- **NHÃN BẮT BUỘC: bản TẠM `062ec090` (30/09) — KHÔNG PHẢI bản production `e54c7745…` đã mất.**

## 0. Cổng gate (vòng watcher)

- Watcher PC0575 tự mở OMP `LAUNCH [omp] 1/4` lúc **16:50:06** cho vé này (`launchStallCount=1`) — **chưa tới ngưỡng "4 lần watcher"**; điều kiện mở có (vé hành động trực tiếp, file nguồn Muse verify trên Drive ~16:50) → OMP nhận vé, không quay no-op.
- Trạng thái mailbox cập nhật + push đúng quy ước tại các mốc: `bf3ddac` (nhận vé) → `e594598` (Bước 1) → `a398113`/`5f6a13f` (Bước 2) → `49fc729` (interim smoke + phát hiện lệch bản dữ liệu).

## 1. Bước 1 — Tải 2 file từ Drive (command line)

- `drive.google.com` **timeout TCP** từ PC0575 (`curl` code 000, kết nối treo) — nhưng **command line KHÔNG bị chặn hoàn toàn**: endpoint `https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t` trả `206` + binary đúng (magic `SQLite format 3`/`PK`). Đã dùng endpoint này.
- Kết quả tải + verify (size chính xác từng byte + md5):

| File | Size (byte) | md5 thực tế | Khớp bảng vé |
|---|---:|---|---|
| `library.sqlite` | 2.552.659.968 | `7392ef9a54d82926f59569a9e664458f` | ✓ |
| `bge-m3-onnx-fp32.zip` | 1.326.939.447 | `db7baa786e5d485a57eb95619ea6eb7b` | ✓ |

- Thư mục tạm: `scratch/restore-drive/` (gitignored).
- **Cây ONNX đã có sẵn trên máy** (`models/bge-m3-onnx-fp32`, 9 file, 2.289.625.694 B) — hash tươi `sha256_model_tree` = `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`, **khớp sidecar** `models/bge-m3-onnx-fp32.sha256`. Giải nén zip Drive ra `scratch/restore-drive/onnx-extract/bge-m3-onnx-fp32` → hash **trùng đúng** `9f81075f…` ⇒ cây sẵn có chính là cây nghiệm thu, **giữ nguyên (không ghi đè)**.
- Cây model HF `BAAI/bge-m3` @ `5617a9f61b028005a4858fdac845db406aefb181`: tải đủ **30 file / 4.587.317.404 B** (đúng size từng file theo HF API) về `local_runs/retrieval_models/bge-m3-5617a9f`; hash tươi `sha256_model_tree` = **`sha256:697a97c33326734d8152b6f026297cd1421587039c301f52c39c34896bd40fda`** — khớp checksum đã duyệt trong `config/workspace_chat_rag_v2.local.json`.

## 2. Bước 2 — Đặt đúng path app/audit mong đợi

Đọc từ `aios_habit.workspace_chat_rag_v2_deployment` + `config/workspace_chat_rag_v2.local.json` + `workspace_chat_store.collection_runtime_layout` (không hardcode):

| Thành phần | Path đã đặt | Verify |
|---|---|---|
| Index TẠM | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | size 2.552.659.968 ✓; md5 `7392ef9a…` ✓; `PRAGMA quick_check`=`ok`; 133.144 chunk / 496 tài liệu |
| Model base | `D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f` (30 file HF) | `sha256_model_tree` = `697a97c3…` (checksum duyệt) |
| Cây ONNX fp32 | `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32` (đã có sẵn; zip Drive đối chiếu trùng hash) | `sha256_model_tree` = `9f81075f…` (khớp sidecar) |

- Ledger `workspace_chat.sqlite` (runtime root) không cần khôi phục — app tự tạo khi chạy (kiểm chứng: app đã tạo trong phiên).

## 3. Bước 3 — Audit + smoke

- Audit chính thức: `PYTHONPATH=src .venv\Scripts\python.exe -B -m aios_habit.workspace_chat_rag_v2_deployment` → **`Status: PASS`** (exit 0; checks: `model_path_exists` ✓, `profile_match` ✓, `model_revision_match` ✓, `fail_closed` ✓; `adaptive_enabled=False` là bình thường).
- `python -m aios_habit.cli audit` → `{"status": "PASS", "errors": [], "warnings": []}`.
- App khởi động: service Streamlit với đúng env của `RUN_AIOS_WORKSPACE_CHAT.bat` → `/_stcore/health`=`ok`, trang chính `HTTP 200`; worker bền nạp model lúc 17:17:36, dense cache 107.331 chunk lúc 17:24:43 (log `…/collections/tri_thuc/logs/bge_worker_daemon.stderr.log`).
- Smoke 1 câu hỏi đơn giản: **ĐẠT** theo đúng nghĩa vé (app khởi động được, hỏi 1 câu có trả lời thật):
  - Hội thoại mới `CONV-4D340116` (sổ `mom_opcenter`), nguồn bật duy nhất `SRC-2441B1A3` (`ORICON_STATUS_早見表_検証済み版.pdf`, 6/6 chunk qua cổng coverage), câu hỏi nguyên văn: **“ORICON STATUS là gì?”**.
  - Lượt 1 (17:33–17:59) **chưa đạt**: câu hỏi vượt hạn client `AIOS_BGE_QUERY_TIMEOUT=1200 s` → `bge_worker_persist_timeout` (worker xong pha dense lúc 17:51:58 nhưng tổng các pha vượt hạn; đĩa lúc đó chậm ~3–4× baseline do tải/copy nền + worker “chuẩn bị” nguồn LSU chạy chồng). Không tính là lỗi khôi phục.
  - Lượt 2 (app restarted sạch 18:16, chỉ mở hội thoại smoke): worker bền hoàn tất nạp **18:26:44**; bấm “Hỏi” **18:26:48**; **trả lời lúc 18:33:18** (≈ **6 phút 30 giây**), nội dung 1.025 ký tự tiếng Việt bám tài liệu (“ORICON STATUS là dãy 16 chữ số HEX tương đương 64 bit (Bit 0–63)…”, “全OK không bảo đảm hoàn tất nhập kho Opcenter/InterStock/ACR…”).
  - Bằng chứng phiên trả lời: `messages.jsonl` (`MSG-CC31BDD4` user 18:26:51 → `MSG-AB584282` assistant 18:33:18), trace `trc_400dcf24da14`: `status=valid`, `insufficient_evidence=false`, `cited_count=2`, lane `direct` (“Gemini Web Stream” qua cầu nối). Ảnh UI: `scratch/restore-drive/ui_smoke2_final.png`.
  - Sau smoke: index vẫn **nguyên trạng** `md5=7392ef9a54d82926f59569a9e664458f`.

### 3.1 Phát hiện quan trọng — lệch bản dữ liệu giữa index TẠM và nguồn hiện tại

Bản TẠM `062ec090` là index dựng 29/09; text nguồn hiện lưu trong `local_cases` đã khác so với bản đã đánh index ở **một phần** tài liệu (định danh tài liệu = sha256 của text nguồn):

| Sổ | Nguồn có text | Khớp `document_id` với index TẠM |
|---|---:|---:|
| `mom_opcenter` (MOM/Opcenter) | 150 | **16** |
| `NB-E35A7BEE` (Điều tra lỗi LSU) | 494 | **0** |

- Ví dụ: cùng file `Tài liệu đào tạo LSU_2019.01.18_K.pptx` — index TẠM chứa id `wsc-cfe180f30fae3c031ffd5951` (45 chunk), còn text nguồn hiện tại hash ra `wsc-154101d384acc2d01009025d` ⇒ không khớp.
- Hệ quả: các hội thoại sổ LSU (`CONV-9C730D76`, …) **không thể tìm thấy căn cứ trên bản TẠM** cho tới khi index được dựng lại/đồng bộ bản nguồn; cổng chuẩn bị nguồn (coverage) sẽ chặn/khởi động chuẩn bị lại (không phù hợp để chạy trên bản TẠM chỉ-đọc).
- Với sổ `mom_opcenter`, 16 nguồn khớp và **qua được cổng coverage** (dense == retrievable == sparse, ví dụ `SRC-2441B1A3` 6/6).

### 3.2 Đường “chuẩn bị nguồn” của app có ghi vào index TẠM (đã phục hồi nguyên trạng)

- Cơ chế thật của app: **mỗi lần mở trang hội thoại, app schedule chuẩn bị cho các nguồn đang bật** (`workspace_chat_app.py` mục “Only prepare enabled sources on page load”). Với hội thoại LSU (nguồn không khớp index), app đã spawn worker chuẩn bị và **ghi vào index TẠM**: `chunk` vẫn 133.144 / 496 tài liệu nhưng **md5 lệch** (`0f272f0c3298ecd1105cc10fa6dde647` so với gốc `7392ef9a…`; mtime 17:28).
- Đã xử lý: dừng app, **copy lại bản tải nguyên** vào đúng path, verify `md5=7392ef9a54d82926f59569a9e664458f` khớp gốc; lượt smoke 2 chỉ mở hội thoại có nguồn `ready` nên không phát sinh ghi; **sau smoke index vẫn nguyên trạng** (md5 ở trên).
- Khuyến nghị cho các vé sau: khi chạy trên bản TẠM, **không mở/render các hội thoại LSU** nếu không muốn index bị chuẩn bị lại; muốn cấm hẳn ghi có thể để runtime ở chế độ chỉ-đọc ở cấp thư mục (vé riêng, cần Muse duyệt).

## 4. An toàn dữ liệu

- Không xoá/ghi đè dữ liệu khác; **không đụng** `C:\AIOS_p5\library.sqlite.bak-20260930` (mới chỉ liệt kê, không đọc/ghi trong vé này).
- Chỉ ghi trong: `local_runs/workspace_chat_rag_v2_production/…` (runtime đích), `local_runs/retrieval_models/bge-m3-5617a9f`, `scratch/restore-drive/` (gitignored), `local_cases/workspace_chat/` (hội thoại smoke mới `CONV-4D340116` + 1 dòng bật nguồn — thao tác app bình thường).
- Index TẠM đã bị đường chuẩn bị nguồn của app ghi trong phiên (mục 3.2) và **đã phục hồi nguyên trạng từ bản tải** (md5 khớp lại gốc); sau đó giữ nguyên qua lượt smoke 2.
- Không merge `main`, không force-push; commit riêng nhánh `phieu-viec/rag-fix1`.

## 5. Bằng chứng

- `scratch/restore-drive/verify_drive_downloads.py` (JSON size/md5 + danh sách file zip), `place_runtime.py` (JSON path/quick_check/chunk count), `verify_onnx_zip.py`, `verify_onnx_tree.py`, `download_hf_tree.sh` + `hf_tree.json`.
- App chạy bằng: `.venv\Scripts\python.exe -m streamlit run src\aios_habit\workspace_chat_app.py` với đúng env của `RUN_AIOS_WORKSPACE_CHAT.bat` (`AIOS_RAG_V2_NUMPY_DENSE=1`, `AIOS_BGE_QUERY_TIMEOUT=1200`, `AIOS_BGE_INIT_TIMEOUT=300`, `AIOS_RAGV2_WORKER_PERSIST=1`, `AIOS_FEATURE_CHAT_ACTION=1`, `AIOS_DOMAIN_ROUTING_ENABLED=1`), bridge `antigravity_bridge` bật (health `direct_ready`).
- Log UI smoke lượt 1 + 2: `scratch/restore-drive/ui_smoke_log.txt`, `ui_smoke2_log.txt`; ảnh `ui_smoke2_final.png` (lượt 2); trace `trc_400dcf24da14` trong `local_cases/workspace_chat/traces.jsonl` (không commit — local_only).
- Log worker: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/logs/`.

## 6. Kết luận + đề xuất

- **Kết luận: ĐẠT → `xong-cho-duyet`.** Audit `Status: PASS`; runtime bản TẠM `062ec090` đặt đúng 3 path app/audit mong đợi, size/md5/hash khớp đủ; app khởi động và **hỏi–đáp 1 câu thật thành công** (mục 3); index **nguyên trạng** sau phiên (`md5=7392ef9a…`).
- Đề xuất cho Muse khi phát hành lại `SPEED-COLDSTART-PC0575`: (1) hội thoại LSU (`CONV-9C730D76`) **không khớp index TẠM** (mục 3.1) — muốn đo câu lạnh/parity phải dùng hội thoại khớp (ví dụ nhóm `mom_opcenter`) hoặc chấp nhận chỉ đo phần khởi động worker; muốn đo đúng 6 câu LSU cần index khớp bản nguồn hiện tại (rebuild/copy-deploy — vé riêng theo quy ước dry-run/backup). (2) Trên bản TẠM, không mở/render hội thoại có nguồn chưa khớp index để tránh app chuẩn bị lại + ghi vào index (mục 3.2).
- Số đo phụ (không thuộc phạm vi vé — vé ghi rõ “không cần đo tốc độ”): worker init lượt sạch 18:16→18:26:44 (~10,5 phút) và câu hỏi ~6,5 phút trong điều kiện đĩa máy chậm (baseline sạch 02/10: init 180,9 s) — ghi để Muse tham chiếu khi phát hành lại vé tốc độ.
