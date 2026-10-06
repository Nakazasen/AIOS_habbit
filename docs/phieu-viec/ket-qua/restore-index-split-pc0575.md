# Báo cáo vé `RESTORE-INDEX-SPLIT-PC0575` — tải 5 khối index từ Drive, hợp lại thành `library.sqlite` chính, thay index TẠM

- Máy: `KDTVN-PC0575` (Windows 11 Pro build `10.0.26200` x64, **CPU-only**), user `kdtvn\tvn183660`.
- Nhánh: `phieu-viec/rag-fix1`. Thời gian thực hiện: 2026-10-06 ~12:23–13:35 +07.
- Kết quả: 5/5 file SHA-256 khớp 100% → hợp 4 khối `integrity_check=ok` (**889 tài liệu / 149.800 chunk**) → thay bản TẠM (đã backup nguyên trạng) → audit `Status: PASS` → **smoke 1 câu hỏi thật qua UI ĐẠT** (trả lời 1.142 ký tự, trace `valid`, index nguyên trạng sau phiên).

## 0. Cổng gate (vòng watcher)

- Watcher PC0575 tự mở OMP `LAUNCH [omp] 1/4` lúc **12:23:30** (`launchStallCount=1`) — **chưa tới ngưỡng 4 lần** (ngưỡng này chỉ dùng cho nhánh `cho-muse`); điều kiện mở có (vé đã phát hành, bước 1 làm được ngay) → OMP nhận vé, không quay no-op.
- Rào mạng của vé: OMP ghi **YÊU CẦU CHUYỂN MẠNG KT_CHETAO** vào `trang-thai.md` lúc **12:26** (commit `485a61a`) → điều phối viên Muse xác nhận **"đã chuyển mạng KT_CHETAO, tiếp tục tải"** lúc **~12:31** (OMP dò thấy lượt kiểm đầu tiên, commit `2effc2b`) → **đủ điều kiện mới bắt đầu tải** (đúng thứ tự rào cứng của vé). Máy cũng đang sẵn Wi-Fi `KT_CHETAO` (`netsh`: `connected`, signal 90%).
- Nhánh 4 lần tự mở không xảy ra: sau khi nhận xác nhận mạng, mọi bước đều có tiến triển + push đúng quy ước (mốc 12:26 → 12:33 → 12:40 → 12:56 → 13:13 → 13:30 → chốt vé). Statut giữ `dang-lam` suốt phiên, không đặt `cho-muse`.

## 1. Bước 1 — Rào mạng trước khi tải (làm TRƯỚC bước tải)

- Dòng đã ghi vào `docs/phieu-viec/mailbox-pc0575/trang-thai.md`:
  "**YÊU CẦU CHUYỂN MẠNG KT_CHETAO: sắp tải ~4,4GB từ Drive** (5 khối index thư mục `index-split-r5-backup`). **DỪNG CHỜ** dòng `ghi_chu` của điều phối viên (Muse) xác nhận… **không tải trước xác nhận**."
- Bộ dò chạy mỗi ~3 phút (`scratch/restore-index-split/poll_confirm.sh`, log `poll.log`): lượt 1 lúc 12:31:21 đã bắt được dòng xác nhận của Muse.
- Số liệu thực tế: tổng 5 file = **2.857.570.037 B (~2,66 GiB)** — vé ghi ước lượng "~4,4GB"; bản thật nhỏ hơn, không ảnh hưởng thao tác.

## 2. Bước 2 — Tải đủ 5 file từ Drive

- 3 file nhỏ tải trực tiếp bằng ID đã có trong báo cáo upload; 2 file lớn **vẫn bị Drive chặn lấy link chia sẻ cấp file** (đúng như báo cáo `upload-split-drive-home.md` §8) → lấy ID bằng cách đọc HTML thư mục con:
  - `https://drive.google.com/embeddedfolderview?id=<FOLDER_ID>#list` → `entry-<FILE_ID>`, `>library.sqlite<`.
  - Ngăn `lsu` (`10gL0Zbwbm1oko7gckrizFUoU8dR0_Yno`) → file ID **`1pSXureuu_l8u1MamMKchRIFxrVKMMHW0`**
  - Ngăn `dieu_tra_loi` (`1MeM7BWGeDO1skAusH6DVrBAOwHvVZrLp`) → file ID **`117q3P2kuP7bLR3XbS8KMxNkQDuUP_L7Y`**
  - (3 file nhỏ: `mom` `1Ew6pZTXL41hr-mn5x_Sm3qXU4X2oPBtf`; `tong_hop` `1fcmGxVZ6zwWc_04JITDZPWikO7py27PK`; manifest `1iAWjsdQHOgJzLJlZHOe_u14L0w4neTHB`.)
- Endpoint tải (đã chứng minh từ vé RESTORE-DRIVE): `https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t` — curl 8.21 (Windows), có `-C -` resume + `--retry 8 --retry-all-errors`; magic bytes `SQLite format 3` kiểm trước khi tải lớn.
- **Khác biệt so với 05/10:** qua mạng KT_CHETAO, `drive.google.com` **thông** (HTTP 200) nên đọc được HTML thư mục; lượt tải rất nhanh (`lsu` 1,08 GiB xong trong ~44 s; `dieu_tra_loi` 1,53 GiB ~78 s).
- Nơi lưu: `scratch/restore-index-split/` (gitignored) — hiện giữ 4 khối đã tải + `domain_manifest.json` làm bằng chứng (có thể xóa sau khi Muse chốt).

## 3. Bước 3 — Đối chiếu SHA-256 (khớp 100%, không lệch byte nào)

| File | Byte | SHA-256 thực tế | Khớp báo cáo upload |
|---|---:|---|---|
| `lsu/library.sqlite` | 1.155.637.248 | `5982a4f1b99a455e89d30bb87095a3ab6f4617b50325a2da10c6d8f4b3c4eabb` | ✓ |
| `dieu_tra_loi/library.sqlite` | 1.643.761.664 | `3bb7b10b5bb2d9345e6ba2baf95d6d6f25575639805504bda66284c36e569651` | ✓ |
| `mom/library.sqlite` | 21.598.208 | `9e796f79e20ee152cb48a56815149243fddfe165e0917f0303c2bf076840d14c` | ✓ |
| `tong_hop/library.sqlite` | 36.081.664 | `4ad4bb35a2367eda4c0a78c0459ed6cf0b0d2d8f2b22f0c36685ba95dd76e73b` | ✓ |
| `domain_manifest.json` | 491.253 | `54f916944c4f2a720300ae0845399d196b3053fe537558f68e2f9f7915531e88` | ✓ |

- `PRAGMA quick_check` từng khối = `ok`; đếm khớp manifest r5: **92 + 681 + 44 + 72 = 889 tài liệu**; **71.945 + 74.439 + 1.014 + 2.402 = 149.800 chunk**.

## 4. Bước 4 — Hợp 4 khối thành `library.sqlite` hoàn chỉnh

- Công cụ: `scratch/restore-index-split/merge_blocks.py` — **phép đảo của `src/aios_habit/split_index_by_domain.py`** (không sửa mã nguồn repo): tạo schema đầy đủ từ 1 khối (đã kiểm 4 khối schema giống nhau từng ký tự, 19 object), chèn `chunks` trước (trigger `chunks_fts_insert` tự đổ FTS) rồi mới các bảng còn lại.
- **Test đối xứng TRƯỚC khi chạy thật** (`test_merge_blocks.py`): dựng fixture bằng **đúng DDL thật** trích từ `library.sqlite` hiện hành → tách bằng chính mã repo → hợp lại → so **từng bảng theo multiset dòng** + FTS `MATCH` + `integrity_check` → **PASS**. Test bắt được 1 lỗi thật trước khi chạm dữ liệu thật: nếu copy nhầm bảng FTS ảo thì mỗi chunk thành **2 dòng FTS** (đã sửa: bỏ FTS khỏi danh sách copy, chỉ đối chiếu số dòng sau trigger).
- Kết quả hợp (log `merge.log`):
  - `chunks` **149.800 / 149.800** (khớp tổng khối)
  - `chunk_embeddings` **121.671 / 121.671**; `chunk_sparse_embeddings` **121.671 / 121.671**
  - `chunk_multivector_embeddings` 0 / 0 (bảng rỗng như nguồn)
  - `chunks_fts` **121.331 / 121.331** (trigger tự dựng lại)
  - **`PRAGMA integrity_check` = `ok`**; `foreign_key_check` 0 vi phạm
  - Manifest khớp đếm: **`docs_match=True`, `chunks_match=True`** → 889 tài liệu / 149.800 chunk
- File hợp: **2.853.646.336 B**; report JSON: `scratch/restore-index-split/build/library.merge-report.json`.

## 5. Bước 5–7 — Dừng app, backup bản TẠM, thay bản hợp vào đúng path

- **Path đích resolve bằng code app (không hardcode):** `WorkspaceChatRagV2CanaryConfig.from_env()` → `runtime_root` + `requested_profile` → `workspace_chat_store.collection_runtime_layout()`:
  `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- **Dry-run trước** (`place_index_restore.py` — mặc định dry-run): xác nhận **không có tiến trình app/worker nào chạy**; build chuẩn (889/149.800, quick_check ok); bản TẠM đúng size.
- **Backup bản TẠM (KHÔNG xóa):** md5 bản TẠM trước/sau copy đều = **`7392ef9a54d82926f59569a9e664458f`** (khớp nguyên trạng phiên trước — chứng minh chưa bị ai ghi từ 05/10) → lưu `local_runs/backup_index_tam_062ec090_2026-10-06/library.sqlite` + `GHI-CHU.txt`.
- **Thay:** xóa file TẠM tại path app → chuyển file hợp vào (cùng ổ đĩa); file `.aios-library-writer.lock/.info` giữ nguyên (app tự quản khi chạy).
- **Verify sau thay:** size 2.853.646.336 B; `quick_check` = `ok`; 889 tài liệu; 149.800 chunk; md5 **`a7c7c2325949c05d3396ab5371e42e64`**. Report: `scratch/restore-index-split/place_report.json`.

## 6. Bước 8 — Audit + Smoke

- Audit deployment (đúng module vé yêu cầu): `PYTHONPATH=src .venv\Scripts\python.exe -B -m aios_habit.workspace_chat_rag_v2_deployment` → **`Status: PASS`** (`model_path_exists` ✓, `profile_match` ✓, `model_revision_match` ✓, `fail_closed` ✓; `adaptive_enabled=False` là bình thường).
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"`, không warning.
- Cổng repo: `compileall src tests` → **exit 0**; `import aios_habit.workspace_chat_app` → OK.
- **Smoke 1 câu hỏi thật qua UI** (app chạy đúng env của `RUN_AIOS_WORKSPACE_CHAT.bat`, thêm `--server.headless true` để không tự mở cửa sổ trình duyệt; bridge `antigravity_sidecar` bật `direct`; UI điều khiển bằng trình duyệt ẩn của công cụ OMP — không cài thêm gì):
  - Worker BGE nạp **index mới**: `init_ms=332.026` ms (~5,5 phút: model_load 11,5 s; index_open 4,5 s; **dense_preload 177,2 s / 121.331 chunk**; **sparse_preload 138,9 s / 22.890 term**).
  - Nguồn smoke `SRC-2441B1A3` trạng thái **`ready`** ("Đã chuẩn bị xong 1/1 tài liệu") trên index mới.
  - Câu hỏi nguyên văn **"ORICON STATUS là gì?"** (hội thoại `CONV-4D340116`) gửi **13:26:21** (`MSG-928093DF`) → **trả lời thật lúc 13:31:15** (`MSG-F6039AF8`), **1.142 ký tự** tiếng Việt bám tài liệu (định nghĩa ORICON STATUS 16 HEX/64 bit, quy tắc hiển thị bit vàng, phán quyết "全OK", các lỗi RFID/vận chuyển/trọng lượng) — tổng **~4 phút 54 giây** (nhanh hơn lượt smoke TẠM 05/10 là 6 phút 30).
  - Trace `trc_abc4ca630e29`: `status=valid`, `cited_count=2`, `insufficient_evidence=False`.
  - Ảnh UI: `scratch/restore-index-split/smoke_ui_answer.webp`.
  - **Index nguyên trạng sau smoke:** md5 trước = sau = **`a7c7c2325949c05d3396ab5371e42e64`** (size y nguyên) → lượt hỏi không ghi vào index (nguồn đã `ready` nên không kích hoạt chuẩn bị).
- Sau smoke: dừng app (đúng nếp phiên trước); worker BGE tắt theo cây tiến trình của phiên OMP này (không phải lỗi cơ chế bền — khi user mở app bằng `RUN_AIOS_WORKSPACE_CHAT.bat` như thường lệ thì worker persist hoạt động bình thường).

## 7. Đối chiếu nguồn ↔ index (bằng chứng phụ, ngoài yêu cầu vé — để Muse/user biết trước)

`scratch/restore-index-split/check_sources_vs_index.py` (đọc-only, so `document_id` = sha256 text nguồn theo đúng hàm `_document_id` của app):

| Sổ | Bản TẠM `062ec090` | Index mới |
|---|---:|---:|
| `NB-E35A7BEE` (LSU) | 0/494 nguồn khớp | **35/494** |
| `mom_opcenter` | 16/150 | **27/150** |

- Nguyên nhân phần còn lại chưa khớp: index mang **dấu vân tay text theo thời điểm build ở máy nhà**; bản text nguồn lưu trên máy công ty đã khác với bản đã đánh index (ví dụ đúng ca đã ghi 05/10: cùng file `Tài liệu đào tạo LSU_2019.01.18_K.pptx`, index chứa `wsc-cfe180f30fae3c031ffd5951`, bản hiện tại hash ra `wsc-154101d384acc2d01009025d`).
- Hệ quả vận hành: mở hội thoại có nguồn chưa khớp sẽ khiến app **chuẩn bị lại** (đọc text + nhúng + ghi vào index) — đây là thiết kế chuẩn khi chạy trên **kho thật** (khác bản TẠM stopgap trước đây); sẽ tốn thời gian ở lần mở đầu. Không phải lỗi của vé này.
- Ghi chú kỹ thuật cho vé sau: 2 file `lsu`/`dieu_tra_loi` **không có link chia sẻ cấp file** — dùng đúng 2 file ID ở mục 2 nếu cần tải lại.

## 8. An toàn dữ liệu

- Không commit `local_cases/`, `scratch/` (đã gitignored); không dán dữ liệu riêng tư vào báo cáo.
- Chỉ ghi trong: runtime đích `local_runs/workspace_chat_rag_v2_production/…` (index — có backup), `local_runs/backup_index_tam_062ec090_2026-10-06/` (mới), `scratch/restore-index-split/` (mới, gitignored), `local_cases/workspace_chat/` (2 tin nhắn smoke — thao tác app bình thường).
- **Bản TẠM không bị xóa** (backup md5 khớp); bản TẠM cũng còn nguyên bản tải trong lịch sử phiên trước tại `scratch/restore-drive/library.sqlite`.
- Không merge `main`, không force-push; mọi commit trên `phieu-viec/rag-fix1`.

## 9. Bằng chứng (đường dẫn)

- `scratch/restore-index-split/poll_confirm.sh` + `poll.log` — dò xác nhận Muse (mỗi 3 phút).
- `scratch/restore-index-split/lsu_folder.html`, `dtl_folder.html` — HTML thư mục chứa file ID 2 khối lớn.
- `scratch/restore-index-split/blocks/{lsu,dieu_tra_loi,mom,tong_hop}/library.sqlite` (+ `download/domain_manifest.json`) — 5 file đã tải, SHA khớp; `download/*.curl.log`.
- `scratch/restore-index-split/merge_blocks.py`, `test_merge_blocks.py`, `tam_schema.sql`, `merge.log`, `build/library.merge-report.json` — hợp khối.
- `scratch/restore-index-split/place_index_restore.py`, `place_report.json` — backup + thay index.
- `scratch/restore-index-split/source_match_report.json`, `check_sources_vs_index.py` — đối chiếu nguồn.
- `scratch/restore-index-split/smoke_ui_answer.webp` — ảnh UI lượt smoke; trace `trc_abc4ca630e29` trong `local_cases/workspace_chat/traces.jsonl` (local_only, không commit).
- `local_runs/backup_index_tam_062ec090_2026-10-06/` — backup bản TẠM + `GHI-CHU.txt`.

## 10. Kết luận + đề xuất

- **Kết luận: ĐẠT → `xong-cho-duyet`.** Đủ mọi tiêu chí vé: (1) rào mạng đúng thứ tự (xin trước — chỉ tải sau xác nhận Muse); (2) 5/5 file size + SHA-256 khớp báo cáo; (3) hợp khối `integrity_check=ok`, đúng **889 tài liệu / 149.800 chunk** theo manifest; (4) bản TẠM được backup nguyên trạng rồi mới thay; (5) index đặt đúng path app mong đợi (resolve bằng deployment module); (6) audit `Status: PASS` + `cli audit` PASS; (7) **smoke 1 câu hỏi thật qua UI ĐẠT** (trace `valid`, 2 trích dẫn), index nguyên trạng sau phiên.
- Đề xuất cho Muse/user:
  1. Nghiệm thu bằng cách mở app như thường lệ (`RUN_AIOS_WORKSPACE_CHAT.bat`); lần mở đầu worker cần ~5,5 phút nạp (đã đo trên index mới), sau đó giữ ấm theo cơ chế cũ — đề xuất giữ nguyên `AIOS_BGE_INIT_TIMEOUT` hiện tại; cân nhắc nâng lên 600 s như đề xuất trước đó nếu muốn câu hỏi đầu sau khi worker chết không bị timeout mềm.
  2. Các sổ có nguồn chưa trùng dấu vân tay index (LSU 35/494, mom 27/150) sẽ tự chuẩn bị lại khi mở — nếu muốn "khớp ngay từ đầu" cho toàn bộ sổ, cần vé riêng **đồng bộ nguồn ↔ index** (dựng lại text-id hoặc tái nhúng theo bản nguồn hiện tại).
  3. Dọn `scratch/restore-index-split/` (≈2,7 GiB: 4 khối đã tải + log/script) sau khi Muse chốt, nếu cần ổ đĩa; **giữ** `local_runs/backup_index_tam_062ec090_2026-10-06/` (2,4 GiB — bản TẠM dự phòng) tới khi user nghiệm thu xong.
