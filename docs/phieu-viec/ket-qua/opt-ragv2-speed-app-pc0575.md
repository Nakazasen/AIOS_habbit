# Báo cáo vé `OPT-RAGV2-SPEED-APP-PC0575` — đo tốc độ hỏi đáp app thật + hồ sơ nút thắt

- Trạng thái: **đo xong, chờ Muse duyệt** (`xong-cho-duyet`).
- Máy: `KDTVN-PC0575` — Windows 11 Pro build `10.0.26200` x64, **CPU-only**, 16 GB RAM; app đang chạy theo deploy Bước 0–5 (`RUN_AIOS_WORKSPACE_CHAT.bat`, `AIOS_FEATURE_CHAT_ACTION=1`, `AIOS_ERROR_CASES_DB=C:\tmp\b0-dict\error_cases_dict.db`).
- Nhánh: `phieu-viec/rag-fix1`. Mã nguồn đo: `80f55071` (đỉnh lúc nhận vé) — trong phiên **không sửa `src/`/`tests/`**.
- Ràng buộc giữ nguyên: **không merge `main`, không force-push, không ghi index production, không chạy `--apply`, không tạo bảng/index mới trong production**; index production mở **read-only**.

## 0. Cổng gate (vòng khép kín)

- Watcher PC0575 (`D:\Sandbox\agent-mailbox\`) tự mở OMP `LAUNCH 1/4` lúc **12:44:08** (`launchStallCount=1`) khi thấy vé `moi`; **điều kiện mở đã tới**: verdict `DEPLOY-BUOC05-PC0575` **ĐẠT** (2026-10-02) + app CPU-only đang chạy, `/_stcore/health`=`ok` → OMP nhận vé (`dang-lam`, commit `ae7919c` 12:46 +07) — **không dùng nhánh “4 lần watcher”/`cho-muse`, không quay no-op**. Các mốc tiến độ được cập nhật + push đúng quy ước (`f76de2e`, `a431325`).

## 1. Phương pháp đo (nói thẳng cái nào là app thật, cái nào là probe)

| Đường đo | Có đi qua giao diện app? | Dùng cho |
|---|---|---|
| **UI app thật (Chromium thật)** — mở sổ `Điều tra lỗi LSU` → hội thoại `CONV-9C730D76` (19 tài liệu ready), gõ câu hỏi vào ô “Câu hỏi gửi AI”, gửi bằng `Ctrl+↵`, đo từ lúc gửi đến khi bong bóng trả lời hiện | **Có** | Hành vi lạnh sau restart (mục 2) |
| **Probe cùng pipeline** — `scratch/speed_app/probe_worker_init.py`: đúng `WorkspaceChatRagV2CanaryConfig.from_env()` → `_pipeline_config(read_only=True, collection=tri_thuc)` → `initialize_workspace_chat_rag_v2_worker()` → `_SUBPROCESS_CLIENT.query_ready()` — tức **đúng client + subprocess worker + index production mà app dùng**, chỉ khác là gọi từ tiến trình đo chứ không qua UI | **Không** (ghi rõ: không gọi là app thật) | Thời gian init worker thật + 1 câu qua worker (mục 3) |
| **Probe cùng pipeline (in-process)** — `scratch/opt_ragv2_lexical_verify_probe.py` (đúng script đã dùng ở vé LEXICAL/PYLOOPS): dựng `RagV2DevPipeline` trên index production, chạy 6 câu qua `RagV2DevPipeline.query` | **Không** | Bảng 6 câu lạnh/ấm, breakdown từng kênh, parity top-15 (mục 4–6) |

**Vì sao không có số hỏi–đáp RAG “qua giao diện app thật”:** đường app thật **không trả lời được câu RAG nào sau restart trên máy này** — nguyên nhân đo được ở mục 2. Đây là phát hiện chặn của vé, không phải OMP bỏ qua yêu cầu “đo app thật”.

## 2. App thật (đúng như đang deploy) — câu lạnh sau restart: **LỖI, ~265 s/câu, không ra câu trả lời**

### 2.1 Số đo UI thật

| Lượt | Câu | Gửi lúc | Trả lời lúc | Tổng (UI) | Kết quả |
|---|---|---|---|---|---|
| 1 | `LSU là gì và gồm những bộ phận quang học chính nào?` | 12:58:14 | 13:02:39 | **269 s** (UI) / 265 s (store) | ⚠️ “AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong. Hãy chờ giây lát rồi bấm Hỏi lại, không cần khởi động lại AIOS.” |
| 2 | (lặp lại y hệt) | 13:03:55 | 13:08:21 | **266 s** (store) | ⚠️ cùng thông báo; **không** sinh câu trả lời RAG |

- Thời gian trên là thời gian UI thật (browser tự bấm nút “Hỏi”), khớp với mốc lưu message trong store (`local_cases/workspace_chat/messages.jsonl`).
- Trong lúc chờ, UI hiện trạng thái “Hủy câu hỏi đang chờ”; hết ~265 s thì trả về thông báo nhắc bấm lại — **không cần khởi động lại AIOS**, nhưng bấm lại cũng lỗi y hệt (lượt 2).

### 2.2 Vì sao — chuỗi bằng chứng (không phải suy đoán)

1. **App không tự làm ấm worker khi mở trang.** `workspace_chat_app.py:878` chỉ gọi `ensure_workspace_chat_worker_warming()` khi `STREAMLIT_SERVER_PORT` có trong env; lần chạy bằng `RUN_AIOS_WORKSPACE_CHAT.bat` (đúng như deploy) **không set biến này** (đã đọc env tiến trình app PID 13664: chỉ có `STREAMLIT_BROWSER_GATHER_USAGE_STATS`, `STREAMLIT_SERVER_FILE_WATCHER_TYPE`, `STREAMLIT_SERVER_RUN_ON_SAVE`). ⇒ worker chỉ được khởi động bởi chính câu hỏi.
2. **Cửa sổ init của app là 120 s, trong khi init worker thật đo được 180,9 s** (mục 3) — và mỗi lần timeout, client **quên** tiến trình đang nạp (`_close_internal` → `_process=None`), nên lần hỏi sau **spawn worker mới** chứ không tái dùng; worker cũ nạp xong thì đọc lệnh “close” và thoát. Log worker của 2 lượt (`…/collections/tri_thuc/logs/bge_worker.stderr.log`) đều **rỗng**, file được tạo lại lúc 13:00:37 và 13:04:01 — tức chưa nạp xong preload đã bị bỏ.
3. **Đường làm ấm nền (nếu có) dùng sai cấu hình**: `ensure_workspace_chat_worker_warming` gọi `_pipeline_config(config, profile)` **không** truyền `collection_id` ⇒ worker được init cho index “legacy” ở gốc profile (`…/bge_m3_hybrid/workspace_chat.sqlite`, đã thấy file rỗng được tạo lúc 13:06:13), còn câu hỏi chạy trên collection `tri_thuc` (`…/collections/tri_thuc/library.sqlite`). Hai `RagV2DevConfig` khác nhau (khác `runtime_root`, `index_filename`, `index_read_only`, `ensure_embeddings_on_open`) ⇒ **không bao giờ tái dùng được** (`bge_subprocess_client.py` so sánh `self._active_config != config`).
4. Hệ quả vận hành: sau mỗi lần restart, câu hỏi RAG đầu tiên (và các câu tiếp theo cho tới khi có đường khác nạp worker) đều **tốn ~4,4 phút rồi báo lỗi**; người dùng không nhận được câu trả lời. Đây là **lỗi app/warm-up**, không phải lỗi nội dung RAG (retrieval chạy tốt — mục 3–4).

### 2.3 Đối chứng lịch sử (để Muse khoanh vùng)

- Cùng hội thoại `CONV-9C730D76` ngày 01/10 có các câu RAG trả lời được qua UI (trace có trích dẫn nguồn): `17:28:21→17:28:48` (27 s), `17:30:25→17:38:22` (477 s), `17:39:58→17:46:38` (400 s), `17:47:46→17:55:38` (472 s), `16:45:17→16:57:54` (757 s). ⇒ Khi worker **đã ấm sẵn** thì app trả lời được; cái chết là **đường làm ấm sau restart**.
- Các thông báo lỗi tương tự đã xuất hiện rải rác ngày 01–02/10 (`10:14`, `10:56`, `12:31`, `13:29`, `14:08`, `09:11`), xen kẽ các lượt thành công — tức đây là lỗi **đã tồn tại**, vé này đo được số và chỉ ra cơ chế.

## 3. Init worker thật + 1 câu qua worker (probe đúng client/config của app)

`scratch/speed_app/probe_worker_init.py` — env như app (`AIOS_RAG_V2_NUMPY_DENSE=1`, `OMP/MKL=1`, `AIOS_BGE_QUERY_TIMEOUT=1200`, `AIOS_RAGV2_LEXICAL_V2=0`), index `tri_thuc` **read-only**:

| Hạng mục | Số đo | Ghi chú |
|---|---:|---|
| materialize nguồn | 0,0 s | đã có bản materialize sẵn |
| **init worker (tổng)** | **180,9 s** | `init_latency_ms=180868`; log worker: `backend=onnx init_ms=180426` |
| — dense preload | 83,9 s | `dense_preload_chunks=120452` |
| — sparse preload | 85,6 s | `sparse_preload_chunks=120452` |
| **câu L1 qua worker (v2off)** | **65,7 s** | `candidate_count=38`, `returned_count=15`, backend `hybrid_rrf` |
| Cửa sổ init của app | **120 s** | `_run_profile` (`initialize_workspace_chat_rag_v2_worker(..., timeout_s=120.0)`) và `ensure_workspace_chat_worker_warming(blocking=True, timeout_s=120.0)` |

## 4. Số đo 6 câu qua probe cùng pipeline (in-process, index production)

Môi trường: PC0575 CPU-only, `scratch/opt_ragv2_lexical_verify_probe.py`, 6 câu L1–L3/E1–E3, hội thoại `CONV-9C730D76`/sổ `NB-E35A7BEE`, **không gọi LLM** (`synthesis_provider=None`). Cache token `(data_version, write_seq)` giữ `(1, 0)` suốt cả 6 câu ở cả hai lượt ⇒ **dense/sparse không nạp lại giữa câu** (Phase A của vé LEXICAL còn hiệu lực); cột dense/sparse dưới đây là 1–9 s chứ không còn 100–160 s như baseline.

Hai lượt chạy độc lập, mỗi lượt một tiến trình (preload xong mới chạy 6 câu liên tiếp):

| Câu | `v2off` tổng (s) | lex / dense / sparse (s) | `v2on` tổng (s) | lex / dense / sparse (s) | candidates |
|---|---:|---|---:|---|---:|
| L1 | 118,3 | 108,2 / 3,6 / 0,8 | **44,3** | 39,1 / 1,7 / 0,5 | 38 |
| L2 | 169,1 | 152,1 / 8,7 / 1,3 | **31,7** | 29,1 / 1,4 / 0,4 | 39 |
| L3 | 133,9 | 124,2 / 2,0 / 0,6 | **10,7** | 7,9 / 1,4 / 0,5 | 40 |
| E1 | 201,8 | 47,1 / 4,4 / 0,8 | **35,9** | 15,1 / 1,1 / 0,6 | 38 |
| E2 | 55,5 | 50,2 / 1,6 / 0,6 | 68,9 | 65,0 / 1,7 / 0,7 | 37 |
| E3 | 95,2 | 89,4 / 2,2 / 0,6 | 160,5 | 153,9 / 2,0 / 0,6 | 44 |

- **L1 = câu lạnh sau khi pipeline/worker vừa init** (đo ngay sau preload); các câu sau ấm dần trong cùng tiến trình.
- Preload (nằm trong worker init, không nằm trong câu hỏi): `v2off` dense 99,4 s + sparse 115,8 s (~215 s); `v2on` dense 119,7 s + sparse 148,3 s (~268 s).
- `v2on` **4/6 câu dưới 60 s** (L1 44,3 · L2 31,7 · L3 10,7 · E1 35,9); vượt ngưỡng: **E2 68,9 s** (fts_match 60,1 s) và **E3 160,5 s** (eligibility 112,9 s — dải nhiễu I/O của máy, xem mục 6).
- `v2off` chỉ **E2 55,5 s** dưới 60 s; các câu còn lại 95–202 s.
- Tách chặng lexical (ms, `SearchSummary.lexical_breakdown_ms`):

| Câu | Chế độ | eligibility_ms | fts_match_ms | like_prefilter_ms | python_score_ms | temp_build_ms |
|---|---|---:|---:|---:|---:|---:|
| L1 | v2off | 88.694 | 18.070 | — | 151 | 28 |
| L1 | v2on | 23.900 | 15.014 | — | 112 | 21 |
| L2 | v2off | 90.856 | 59.246 | — | 307 | 73 |
| L2 | v2on | 5.110 | 23.759 | — | 93 | 56 |
| L3 | v2off | 82.090 | 41.297 | — | 138 | 40 |
| L3 | v2on | 4.087 | 3.613 | — | 101 | 52 |
| E1 | v2off | 33.886 | — | 11.049 | 1.020 | — |
| E1 | v2on | 3.779 | — | 10.456 | 663 | — |
| E2 | v2off | 11.548 | 37.798 | — | 126 | 36 |
| E2 | v2on | 4.382 | 60.098 | — | 211 | 52 |
| E3 | v2off | 50.773 | 37.533 | — | 120 | 31 |
| E3 | v2on | 112.905 | 40.552 | — | 151 | 65 |

- E1 (CJK) đi đường `deterministic_scan` + `LIKE` prefilter (951 lần chấm `_score_candidate`, không có `fts_match`); các câu còn lại đi FTS5 bm25 (100 lần chấm).
- `temp_build_ms` chỉ 21–73 ms cho 2.878 dòng ⇒ **bảng tạm không còn là nút thắt** (khớp kết luận vé LEXICAL).

### 4b. Lạnh vs ấm lặp lại (2 lượt trong cùng một tiến trình)

`scratch/speed_app/probe_cold_warm.py` — lượt “cold” chạy ngay sau preload, lượt “warm” lặp y hệt 6 câu trong cùng pipeline (cache dense/sparse giữ nguyên, token `(1, 0)` không đổi):

| Câu | `v2off` lạnh → ấm (s) | `v2on` lạnh → ấm (s) |
|---|---:|---:|
| L1 | 97,1 → **52,2** | 157,8 → 104,3 |
| L2 | 152,7 → **50,8** | 133,4 → 134,6 |
| L3 | 155,9 → **54,3** | 179,4 → 181,4 |
| E1 | 132,6 → 61,0 | 483,9 → 277,1 |
| E2 | 53,8 → **29,6** | 176,0 → 102,2 |
| E3 | 117,4 → **13,3** | 105,9 → 112,4 |

- Top-15 của lượt ấm **trùng 100 %** lượt lạnh ở cả hai chế độ (parity không đổi theo trạng thái cache).
- **Cảnh báo nhiễu I/O (đọc kèm số lượt A)**: lượt đo này trùng thời điểm đĩa bận — preload `v2on` 370 s so với 268 s ở lượt A; chính các câu `v2on` cũng chậm 3–10 lần (E1 lạnh 483,9 s). Cùng chế độ `v2on`, lượt A (13:39–13:49) cho L1 44,3 / L2 31,7 / L3 10,7 / E1 35,9; lượt này (14:22–14:57) cho 104–277 s. Vì vậy **kết luận tốc độ phải đọc theo dải**, không lấy một con số: khi đĩa rảnh, câu ấm rơi vào **10–55 s**; khi đĩa bận, cùng câu lên **100–280 s**. Đây là đặc tính máy CPU-only + HDD, không phải khác biệt do mã.

## 5. Parity top-15 so với baseline `scratch/opt_ragv2_verify_new.json`

Lệnh: `python scratch/opt_ragv2_lexical_compare.py scratch/opt_ragv2_verify_new.json scratch/opt_ragv2_lexical_speed-v2off.json scratch/opt_ragv2_lexical_speed-v2on.json` (exit code **0**).

| Câu | `v2off` vs baseline | `v2on` vs baseline | candidates (baseline → run) |
|---|---|---|---|
| L1 | **trùng 100% từng vị trí** | **trùng 100% từng vị trí** | 38 → 38 |
| L2 | **trùng 100%** | **trùng 100%** | 39 → 39 |
| L3 | **trùng 100%** | **trùng 100%** | 40 → 40 |
| **E1 (CJK)** | **15/15 đúng thứ tự** | **15/15 đúng thứ tự** | 38 → 38 |
| E2 | **trùng 100%** | **trùng 100%** | 37 → 37 |
| E3 | **trùng 100%** | **trùng 100%** | 44 → 44 |

- **ĐẠT tiêu chí parity**: không lệch câu nào, E1 đủ 15/15 đúng thứ tự ở **cả hai** chế độ ⇒ không phải cân nhắc kill-switch `AIOS_RAG_V2_CJK_PREFILTER`.
- Ghi chú môi trường (minh bạch): lượt đo này thấy **33/33 nguồn non-empty đang ở trạng thái `ready`** (ledger production `workspace_chat.sqlite`: 32 dòng ready + 2 failed), trong khi baseline 01/10 ghi `19/33` ready. Dù tập nguồn đầu vào khác, **top-15 của cả 6 câu vẫn trùng khít baseline** ⇒ với bộ câu này, phần nguồn thêm vào không đổi kết quả.

## 6. Nút thắt còn lại (số đo + EXPLAIN QUERY PLAN)

Số đo (mục 4) tách được 3 nút thắt, tất cả đều nằm trong chặng lexical (dense/sparse đã hết nạp lại):

1. **Quét eligibility toàn bộ 120.452 dòng `chunks`** mỗi câu — `SELECT chunk_id, document_id, source_path, privacy_labels_json, source_fingerprint FROM chunks WHERE retrievable = 1` (v2on, narrow) hoặc `SELECT * FROM chunks WHERE retrievable = 1` (v2off, full row).
   - Đo: `v2off` 11,5–90,9 s; `v2on` 3,8–112,9 s. Đây là **I/O-bound trên DB 2,84 GB** (không phải Python: `indexed_rows=120.452` đọc xong mới lọc còn `eligible_rows=2.878`).
2. **`chunks_fts MATCH` + `bm25` + JOIN bảng tạm** cho câu non-CJK: 3,6–60,1 s (`fts_match_ms`), trong khi xây bảng tạm chỉ 21–73 ms.
3. **Câu CJK (E1)** đi đường `deterministic_scan`: `LIKE` prefilter 10,5–11,0 s trên 4 cột ghép (`normalized_text/source_name/source_path/metadata_json`) + 951 lượt `_score_candidate` (0,66–1,02 s).

Phần Python thuần (`python_score_ms` 0,09–1,02 s) và fusion/assembly (≤0,1 s) **không đáng kể**. Dải dao động giữa các câu là **nhiễu I/O của máy** (cùng chế độ `v2on`: E3 112,9 s eligibility so với L3 4,1 s), khớp ghi chú ±40 % của vé LEXICAL.

**EXPLAIN QUERY PLAN** (chạy read-only trên đúng index production, `scratch/speed_app/explain_bottleneck.json`):

| Truy vấn | Kế hoạch (detail) | Số thô |
|---|---|---|
| eligibility (narrow/full) | `SEARCH chunks USING INDEX idx_chunks_retrievable (retrievable=?)` | khớp **120.452/148.807 dòng** nên đọc gần hết bảng: **73,2 s** lượt nguội / **26,5 s** lượt ấm page cache |
| `chunks_fts MATCH` + `bm25` (E3) | `SCAN f VIRTUAL TABLE INDEX 0:M5` + `SEARCH eligible USING COVERING INDEX sqlite_autoindex_…(chunk_id=?)` + `USE TEMP B-TREE FOR ORDER BY` | **40,8 s** cho `LIMIT 100` (khớp `fts_match_ms` 37,5–60,1 s của probe) |
| CJK LIKE prefilter (E1) | `SEARCH chunks USING INDEX idx_chunks_retrievable` + biểu thức `LIKE` trên 4 cột ghép | **23,0 s**, **23.515 dòng** khớp (lượt nguội; probe ấm 10,5–11,0 s) |

- Quy mô bảng: `chunks` **148.807** · `chunks_fts` **120.452** · `chunk_embeddings` **120.792** · `chunk_sparse_embeddings` **120.792**.
- Ghi chú: kế hoạch **có** dùng index `idx_chunks_retrievable` (không phải full-table scan), nhưng vì `retrievable=1` chiếm 81 % số dòng nên chi phí gần như đọc cả bảng. Bảng tạm của đường FTS chỉ chứa **2.878 dòng eligible** (xây 21–73 ms) — nếu đổ cả 120.452 dòng thì tốn ~30 s (đã đo trong script EXPLAIN), nên đừng nới rộng bảng tạm.

Đây là các hướng Muse có thể cân nhắc (số ở trên là cơ sở, OMP không tự code trong vé này):

- **Bỏ quét 120k dòng cho mỗi câu**: giữ một bảng “dải eligibility” hẹp (chunk_id, document_id, source_path, privacy_labels_json, source_fingerprint — không kèm cột TEXT lớn) hoặc index covering `chunks(retrievable)`, cập nhật lúc ingest; hoặc cache map eligibility theo token `(data_version, write_seq)` để câu thứ 2 trở đi không đọc lại 120k dòng.
- **FTS5 bm25**: cache kết quả MATCH theo tập term + token index (mỗi câu hiện chấm lại toàn bộ tài liệu khớp), hoặc tách bảng FTS hẹp chỉ chứa chunk của hội thoại/collection đang dùng.
- **CJK**: chuyển prefilter LIKE sang bảng trigram (`chunks_fts_trigram`) nếu chấp nhận ghi index theo lane riêng (dry-run + backup + user duyệt) — như đề xuất đã có ở vé LEXICAL.
- **Cold start**: init worker 180,9 s (dense 83,9 s + sparse 85,6 s) là chi phí cố định sau mỗi restart. Có thể lưu cache dense/sparse ra đĩa (npy/mmap) để init chỉ còn nạp model; hoặc chấp nhận lazy-load có trần thời gian.

## 7. An toàn dữ liệu — ĐẠT

| Hạng mục | Trước (12:52 +07) | Sau (15:01 +07) | Kết luận |
|---|---|---|---|
| Index production `…/collections/tri_thuc/library.sqlite` | SHA-256 `e54c7745b86cb360d903c5e211827126b6c8d69606c8809bcdd7f90737c47fe7` · 2.842.415.104 B · mtime `2026-10-01 15:46:42` | **y nguyên** (SHA + size + mtime) | **Không đổi ✔** |
| `/_stcore/health` (app đang chạy) | `ok` | `ok` | ✔ |

- Mọi probe của vé mở index `mode=ro` (read-only) và chỉ ghi bảng `TEMP`; không ghi vector/chunk vào index production, không chạy `--apply`, không tạo bảng/index mới trong production, không merge `main`, không sửa `src/`/`tests/`.
- **Ghi nhận trung thực tác dụng phụ ngoài index production** (đều do **đường chuẩn bị nguồn nền của chính app**, không phải probe ghi vào index):
  - Khi hỏi qua UI (12:58/13:03), app gọi `schedule_workspace_chat_source_preparation(...)` → drain nền của app khởi động lại và chạy trong suốt phiên: ledger nguồn `…/workspace_chat_rag_v2_production/workspace_chat.sqlite` tăng 34 → **180 dòng** (133 ready · 44 pending · 1 processing · 2 failed) và index “legacy” ở gốc profile `…/bge_m3_hybrid/workspace_chat.sqlite` được ghi tới **57 MB** (2.954 chunk / 2.417 embedding) — **không phải** file `collections/tri_thuc/library.sqlite` mà câu hỏi dùng.
  - Các file runtime khác: `materialized_sources/` (đã có sẵn), `…/collections/tri_thuc/logs/bge_worker.stderr.log` (log stderr của worker, 176 B), `scratch/speed_app/*` (git-ignore).
  - Đề nghị Muse để ý: drain nền vẫn đang chạy khi phiên này kết thúc (mtime 15:00:42) — vé này không dừng nó (không thuộc phạm vi).
- `git status`: chỉ `M uv.lock` (có sẵn từ đầu phiên, **không commit**) + file watcher untracked; `src/`, `tests/` sạch.

## 8. Kết luận & đề xuất cho Muse

1. **Chặn lớn nhất của “đo tốc độ app thật” trên PC0575 là đường làm ấm worker sau restart, không phải RAG.** App (đúng như deploy, `RUN_AIOS_WORKSPACE_CHAT.bat`) không tự làm ấm khi mở trang; câu RAG đầu tiên sau restart **luôn lỗi sau ~265 s** vì init worker thật đo được **180,9 s > cửa sổ 120 s** của app, và mỗi lần timeout lại spawn worker mới. Đề xuất cho Muse (thứ tự ưu tiên):
   - Cho phép cấu hình cửa sổ init/warm-up qua env (ví dụ `AIOS_BGE_INIT_TIMEOUT`) hoặc nâng mặc định ≥ 300 s cho máy CPU-only; **giữ** worker đang nạp thay vì `_close_internal` rồi bỏ;
   - Sửa đường làm ấm dùng **đúng cấu hình câu hỏi** (`collection_id` + `read_only=True`), hiện đang init cho index “legacy” ở gốc profile nên không bao giờ được tái dùng;
   - Cân nhắc lưu cache dense/sparse ra đĩa để cắt 180,9 s init (dense preload 83,9 s + sparse 85,6 s).
2. **RAG khi worker ấm đã nhanh hơn hẳn baseline** (dense/sparse 1–9 s thay vì 100–160 s; tổng câu 10–202 s so với 266–455 s baseline), **nhưng chưa đạt ổn định mốc <60 s/câu**:
   - Lượt A (13:22–13:49, đĩa rảnh): `v2on` **4/6 câu <60 s** (L1 44,3 · L2 31,7 · L3 10,7 · E1 35,9), `v2off` chỉ E2 55,5 s.
   - Lượt B (14:05–14:57, đĩa bận): `v2off` ấm **5/6 câu <60 s** (52,2 · 50,8 · 54,3 · 13,3 · 29,6; E1 61,0), `v2on` ấm lại 102–277 s.
   - ⇒ Nút thắt là **I/O đĩa của hai truy vấn SQL ở mục 6**, không phải logic; trạng thái tốt: câu ấm 10–55 s, trạng thái xấu: 100–480 s. **Không tuyên bố đạt tốc độ chỉ vì parity đạt.**
3. **Nút thắt còn lại là 2 truy vấn SQL đọc trên DB 2,84 GB** (không còn là Python): quét eligibility 120.452 dòng (11,5–112,9 s) và `chunks_fts MATCH`+bm25 (3,6–60,1 s); CJK thêm LIKE prefilter ~10,5 s. Đây là nơi cần tối ưu tiếp (mục 6).
4. **Parity ĐẠT 100% cả 6 câu ở cả hai chế độ, E1 đủ 15/15 đúng thứ tự** ⇒ số đo ủng hộ **bật `AIOS_RAGV2_LEXICAL_V2=1`** làm mặc định (quyết định thuộc Muse/user).
5. Index production **không đổi**; health `ok`; không ghi index; không merge `main`; không sửa `src/`/`tests/`.
6. **Kiến nghị vé tiếp theo cho Muse**: (a) vé code sửa đường warm-up/init của app (mục 2) để người dùng PC0575 hỏi được ngay sau restart; (b) vé tối ưu eligibility + FTS (mục 6) để kéo E2/E3 dưới 60 s.

## 9. Bằng chứng (git-ignore, trong `scratch/speed_app/`)

- `probe_worker_init.py`, `worker_init_init_v2off.json` — init worker + 1 câu qua worker (mục 3).
- `probe_speed_v2off.out`, `probe_speed_v2on.out`, `opt_ragv2_lexical_speed-v2off.json|v2on.json` — 6 câu probe (mục 4–5).
- `probe_cold_warm.py`, `coldwarm_*.json` — 2 lượt lạnh/ấm trong cùng tiến trình.
- `explain_bottleneck.py`, `explain_bottleneck.json` — EXPLAIN QUERY PLAN + timing thô (mục 6).
- `pc0575_speed_restart.ps1`, `sitehooks/sitecustomize.py` — công cụ restart đo (không dùng để sửa mã).
- Ảnh chụp / DOM của 2 lượt UI hỏng: log phiên đo trong hội thoại + `local_cases/workspace_chat/messages.jsonl` (mốc 12:58–13:08).
