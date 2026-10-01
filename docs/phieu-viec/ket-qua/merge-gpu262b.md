# Vé `merge-gpu262b` — nhập 14 tài liệu mới từ delta GPU-262b vào production (`KDTVN-PC0575`)

## 0. Kết luận ngắn — **ĐẠT** (kèm 1 phát hiện đã xử lý, ghi rõ để Muse kiểm)

- Delta GPU-262b **khớp ghim** (zip + sqlite), dry-run PASS, backup `ok`, merge 1 transaction PASS:
  **+2.207 chunk** (chunks / retrievable / dense / sparse / FTS đều +2.207), **5 ID cũ không đổi một dòng**,
  `integrity_check` / `foreign_key_check` / FTS integrity-check đều `ok`.
- **Phát hiện sau merge (đã xử lý):** delta xuất **thiếu cột `source_fingerprint`** → cổng phủ nghiêm ngặt
  của pipeline chặn mọi truy vấn (`semantic_index_coverage_incomplete`). Đã **stamp `source_fingerprint` cho
  đúng 2.207 dòng của 14 ID mới** (chỉ sửa dữ liệu, không sửa code); cơ sở: bất biến
  `document_id = wsc-<sha256(text)[:24]>` và 14/14 file materialized có sha256 bắt đầu đúng 24 ký tự của
  `document_id`. Không đụng 5 ID cũ. Sau sửa: cổng phủ `valid=True`, mọi kiểm tra tính toàn vẹn `ok`.
- Sau merge, app ghi nhận **33/35 nguồn đang bật ở trạng thái `ready`** (trước merge: 10/35).
- Production: SHA trước `5260c043…b512b` (2.565.955.584 B) → sau merge `f347f373…b0865` (2.611.253.248 B)
  → **sau stamp (chốt) `b9a4b987…1705` (2.611.515.392 B)**.
- Smoke UI LAN và trạng thái cuối: xem mục 7.

## 1. Verify file delta (bước 1)

| Mục | Giá trị |
| --- | --- |
| Nguồn | Drive `AIOS_Data` (link trong `upload-delta-drive.md`), tải bằng `curl` ẩn danh (HTTP 200) |
| File | `scratch/gpu-262b-delta-20261001.zip` — 20.867.536 B |
| SHA-256 zip | `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85` — **khớp ghim** |
| Bung ra | `C:/tmp/gpu-262b-delta/` (ổ C, không đụng production) |
| File trong zip | `gpu-262b-delta-20261001.sqlite` 57.020.416 B + `gpu-262b-manifest-20261001.json` |
| SHA-256 sqlite | `b4b6f0bf059f544b606cfb7c33b315d72a5dc9c3a9b9a3591dc4cbfc47cf944a` — **khớp ghim** |
| Manifest | 19 tài liệu / 2.883 chunk; 14 ID nhập + 5 ID skip; `integrity_check: ok` |

## 2. Dry-run (bước 2, chỉ đọc) — `scratch/merge_gpu262b_dryrun.py`

- Fingerprint delta trên **cả 2 bảng vector** = `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` (khớp backend đang chạy).
- 14 ID merge: **vắng mặt hoàn toàn** trong production (`prod=0`), số chunk mỗi ID **khớp manifest**; tổng **2.207 chunk**.
- 5 ID skip có đủ `retrievable` + dense + sparse **đúng bằng manifest** (15 / 11 / 345 / 274 / 31); phần dư trong
  production là chunk `retrievable=0` (không tính).
- **0 trùng `chunk_id`** giữa 2.207 chunk sẽ nhập và production.

## 3. Backup (bước 3)

- Dừng app (port 8501 free) trước khi ghi.
- Bản sao: `library.sqlite.bak-20261001-1215` (cùng thư mục collection), 2.565.955.584 B.
- SHA-256 backup = `5260c043…b512b` — **khớp production trước merge**.
- `PRAGMA integrity_check` trên backup = `ok` (444 giây).

## 4. Apply (bước 4) — `scratch/merge_gpu262b_apply.py`

- 1 transaction `BEGIN IMMEDIATE`: kiểm lại trùng `chunk_id` (0) → insert `chunks` / `chunk_embeddings` /
  `chunk_sparse_embeddings` từ delta cho đúng 14 ID → verify số dòng = kỳ vọng → `COMMIT`.
- Insert: **2.207 / 2.207 / 2.207** (đúng manifest). Không đụng 5 ID cũ (không có câu lệnh nào nhắm vào chúng).

## 5. Phát hiện `source_fingerprint` thiếu + xử lý (minh bạch)

- Smoke lần 1 (12:30:37) trả "⚠️ AIOS đã tự làm nóng bộ đọc và thử lại một lần nhưng chưa xong";
  log worker nguyên văn: `SemanticBackendUnavailable: semantic_index_coverage_incomplete`.
- Đo chỉ đọc (`scratch/coverage_diag.py`): cổng phủ fail `document_identity_mismatch` **đúng 14 ID vừa merge**;
  các dòng merge trong index có `source_fingerprint = NULL` (delta xuất thiếu trường), trong khi 5 ID cũ có đủ.
- **Cơ sở sửa:** app định danh tài liệu bằng `document_id = "wsc-" + sha256(text.strip().utf-8)[:24]`
  (`workspace_chat_rag_v2_adapter.py:740`). 14/14 file materialized hiện tại có SHA-256 **bắt đầu đúng 24 ký tự**
  của `document_id` tương ứng ⇒ text hai máy khớp nhau ⇒ SHA-256 đầy đủ của file materialized chính là
  `source_fingerprint` đúng.
- **Sửa:** chỉ `UPDATE chunks SET source_fingerprint = <sha256> WHERE document_id = <14 ID> AND source_fingerprint IS NULL`
  (2.207 dòng), trong 1 transaction, không nhắm vào ID nào khác (`scratch/merge_gpu262b_fix_fingerprint2.py`).
- **Sự cố giữa chừng (đã xử lý an toàn):** lần chạy đầu bị tool-timeout cắt giữa transaction → SQLite
  (journal mode `delete`) tự rollback khi mở lại → DB về đúng trạng thái sau merge (kiểm lại: 2.207 dòng NULL,
  đủ 136.087 chunk). Nguyên nhân chậm: trigger `chunks_fts_update` là `AFTER UPDATE` **mọi cột**, nên mỗi dòng
  UPDATE phải xoá + chèn lại FTS (≈ trung bình ~1,7 giây/dòng). Cách làm lại: **tạm `DROP TRIGGER chunks_fts_update`**
  → UPDATE 2.207 dòng trong **0,7 giây** → **tạo lại trigger đúng nguyên văn DDL gốc** (so khớp `True`) → kiểm
  FTS integrity-check `ok`.
- Sau sửa: `NULL = 0`, cổng phủ `valid=True` cho 19 tài liệu / 2.883 chunk (dense + sparse đủ, fingerprint `016c5255…`).

## 6. Verify sau merge (bước 5)

| Hạng mục | Trước merge | Sau merge |
| --- | --- | --- |
| `chunks` | 133.880 | **136.087** |
| `retrievable` | 108.007 | **110.214** |
| dense = sparse | 108.347 | **110.554** |
| `chunks_fts` | 108.007 | **110.214** |
| 5 ID skip (`retrievable`) | 15 / 11 / 345 / 274 / 31 | **không đổi** |

- 14/14 ID mới: `retrievable` = dense = sparse = manifest (4, 11, 69, 196, 213, 217, 155, 137, 108, 4, 568, 7, 210, 308).
- `PRAGMA integrity_check` = `ok` (747 giây trên bản sau stamp); `foreign_key_check` = rỗng;
  FTS `integrity-check` = `ok` (258 giây, chạy trên kết nối ghi).
- SHA-256 production chốt = `b9a4b987413ff38f9d81e589c1450e5d4abc36b8a5e626e2b318bba3501d1705` (2.611.515.392 B).

## 7. App sau merge + smoke UI LAN

- App khởi động lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat` (env `AIOS_RAG_V2_NUMPY_DENSE=1`,
  `AIOS_BGE_QUERY_TIMEOUT=1200`), listener `0.0.0.0:8501`, `/_stcore/health` = `ok`;
  trang "Hỏi tài liệu" ghi **33/35 nguồn ready** (trước merge 10/35).
- Số đo truy vấn trên index đã merge (worker thật + shim log, chỉ đọc, câu E1):
  `worker init 46,7 s`; `rag_v2.stage search path=numpy chunks=110214 variants=1 embed_ms=6540 load_ms=172966 score_ms=206 fuse_ms=818 total_ms=181048`;
  lượt dense thứ hai trong cùng câu `total_ms=3517`; `synthesis mode=full` 43 ms; **tổng truy vấn 891,6 giây**.
  Vì vậy đã nâng `AIOS_BGE_QUERY_TIMEOUT` từ 900 → **1.200 giây** (số đo + margin) và restart app trước smoke cuối.
- Smoke UI LAN (hội thoại `CONV-9C730D76`):
  - E1 ("Lỗi Beam径 NG… nguyên nhân…") qua app **không xong trong 1.200 giây** (log app: `bge_worker_query_timeout`,
    worker init 31,9 s) — trong khi **cùng câu hỏi gọi thẳng worker chỉ hết 891,6 giây** (số đo ở trên).
    `[INFERENCE]` khác biệt nằm ở đường app: câu E1 được router xếp hạng "deep/causality" nên kế hoạch truy vấn
    của app nhiều biến thể hơn bản mặc định của probe; cần Muse xác minh khi tối ưu (không kết luận chắc).
  - Smoke chốt bằng câu E3 (đường retrieval thường, có dùng tài liệu vừa merge): xem dòng kết quả cuối mục này.
- **Mục tiêu "tra cứu dưới 1 phút" tiếp tục bị đe dọa trên máy CPU-only** — 3 vòng Python trong
  `rag_v2/index.py` (lexical fetchall toàn bảng kèm text, sparse chấm điểm Python, nạp lại ma trận dense mỗi câu)
  là nút thắt; vé tối ưu của Muse vẫn cần.

## 7.1 Kết quả smoke chốt

| Mục | Kết quả |
| --- | --- |
| Câu hỏi smoke | "Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?" |
| Gửi → trả lời | 14:09:21 → 14:25:32 = **971 giây (16m11s)** |
| Đáp án (tóm tắt) | Đo nghiêng LD mirror bằng máy 3D (OK/NG) + kẹp SIM vào LD mirror; dùng JIG BEAM đổi trục quang; kiểm tra Lens CYLINDRICAL / POLYGON / Lens F — khớp nội dung tài liệu, không bịa |
| Nguồn trích dẫn | Trace `trc_62af68f84597` — **`valid`, cited_count = 3**: `[1]` `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx`, `[2]` `Dữ_liệu_tổng_hợp.xlsx`, `[3]` `RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg` |
| Trạng thái app sau smoke | `/_stcore/health` = `ok`; `http://10.170.157.180:8501/` (IP LAN hiện tại) → HTTP 200; listener `0.0.0.0:8501` |
| Ghi chú | Trang "Hỏi tài liệu" hiển thị **33/35 nguồn ready** sau merge (trước merge 10/35) |

## 8. Đề xuất cho Muse

1. Exporter delta ở máy nhà nên mang theo `source_fingerprint` cho mọi dòng (hoặc app reconcile tự stamp khi
   thấy `NULL` + `document_id` khớp prefix sha256), để lần merge sau không phải stamp tay.
2. Trigger `chunks_fts_update` nên giới hạn cột (như `chunks_embeddings_content_update` đã làm) để UPDATE
   metadata không phải dựng lại FTS — hiện mỗi dòng UPDATE bị phạt ~1,7 giây.
