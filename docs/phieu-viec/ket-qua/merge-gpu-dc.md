# Vé `merge-gpu-dc` — nhập 329 tài liệu Điều chỉnh từ delta GPU-DC vào production (`KDTVN-PC0575`)

## 0. Kết luận ngắn — **ĐẠT**

- Delta GPU-DC **khớp ghim** (zip + sqlite), dry-run PASS, backup `ok`, merge 1 transaction PASS:
  **+12.720 mảnh** (10.238 retrievable có vector + 2.482 parent `retrievable=0` giữ ngữ cảnh),
  dense = sparse = +10.238; **không một dòng nào của production cũ bị ghi đè/xóa** (136.087 chunk cũ nguyên vẹn).
- **Stamp bổ sung (đã xử lý):** delta xuất **thiếu `source_fingerprint`** ở toàn bộ 12.720 dòng (lặp lại bài học
  262b). Sổ PC0575 **không chứa 329 nguồn DC** nên đã tái tạo `content_text` từ ZIP gốc bằng **đúng chuỗi
  trích xuất của app** và verify từng ID bằng bất biến `document_id = wsc-sha256(text)[:24]`:
  **329/329 khớp**. Đã stamp đúng 12.720 dòng (chỉ dòng `NULL` của 329 ID mới), `NULL=0`, trigger
  `chunks_fts_update` tạo lại **khớp nguyên văn DDL gốc**.
- Verify sau merge (chỉ đọc): `integrity_check` / `foreign_key_check` / FTS integrity-check = `ok`;
  329/329 ID đủ mảnh+retrievable+dense+sparse; **cổng phủ `valid=true`** (10.238/10.238 dense+sparse,
  không thiếu/không lệch ID nào, fingerprint `016c5255…`).
- Production: SHA trước merge `b9a4b987…1705` (2.611.515.392 B) → **sau merge `e54c7745…47fe7`
  (2.842.415.104 B)**.
- App restart + smoke UI LAN **ĐẠT**: câu E3 gửi 15:53:05 → trả lời 16:06:17 = **786 giây** (không chạm timeout
  1.200s), trace `trc_bef350a2629f` **`valid`, cited_count = 3** — đáp án khớp tài liệu, không bịa; app LAN
  health `ok`, `http://10.170.157.180:8501/` → HTTP 200 (chi tiết mục 7).

## 1. Verify file delta (bước 1)

| Mục | Giá trị |
| --- | --- |
| Nguồn | Drive `AIOS_Data` (link trong vé), tải bằng `curl` ẩn danh → `scratch/gpu-dc-delta-20261001.zip` |
| SHA-256 zip | `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3` (74.065.213 B) — **khớp ghim** |
| Bung ra | `C:/tmp/gpu-dc-delta/` (ổ C, không đụng production) |
| SQLite trong zip | 228.937.728 B, SHA-256 `a0ca1345b62a5d95867bb62f5790a40b3bd5f46704002323731c68822ad1cec3` — **khớp ghim** |
| Manifest | 329 tài liệu / 12.720 mảnh (10.238 retrievable + 2.482 parent) / `skip_existing_document_ids=[]`; `integrity_check: ok` |
| Fingerprint delta | `016c5255…274fb` trên **cả 2 bảng vector**; FTS 10.238 dòng |
| `source_fingerprint` trong delta | `NULL` toàn bộ **12.720** dòng → xử lý ở bước 5 |

## 2. Dry-run (bước 2, chỉ đọc) — `scratch/merge_gpu_dc_dryrun.py`

- Fingerprint delta cả 2 bảng đúng backend đang chạy; production có 2 fingerprint (ONNX `016c5255…` + bộ PyTorch cũ — thông tin, không chặn).
- **329/329 ID vắng mặt hoàn toàn** trong production; tổng mảnh + retrievable mỗi ID **khớp manifest**.
- **0 trùng `chunk_id`** giữa 12.720 mảnh sẽ nhập và production → **PASS**.
- Baseline production trước merge: chunks 136.087 / retrievable 110.214 / dense = sparse 110.554 / FTS 110.214.

## 3. Backup (bước 3)

- Dừng app trước khi ghi (port 8501 free; cây tiến trình streamlit + worker BGE đã tắt).
- Bản sao: `library.sqlite.bak-20261001-1504-gpu-dc-premerge` (cùng thư mục collection), 2.611.515.392 B.
- SHA-256 backup = `b9a4b987…1705` — **khớp production trước merge** (đối chứng SHA trước/sau copy bằng nhau).
- `PRAGMA integrity_check` + `quick_check` trên backup = `ok` (1.103 giây).

## 4. Apply (bước 4) — `scratch/merge_gpu_dc_apply.py`

- 1 transaction `BEGIN IMMEDIATE`: kiểm lại trùng `chunk_id` (0) → insert `chunks` / `chunk_embeddings` /
  `chunk_sparse_embeddings` từ delta cho đúng 329 ID → verify số dòng = kỳ vọng → `COMMIT`.
- Insert: **chunks 12.720 / dense 10.238 / sparse 10.238** (đúng manifest). FTS +10.238 qua trigger chuẩn.

| Hạng mục | Trước merge | Sau merge |
| --- | --- | --- |
| `chunks` | 136.087 | **148.807** |
| `retrievable` | 110.214 | **120.452** |
| dense = sparse | 110.554 | **120.792** |
| `chunks_fts` | 110.214 | **120.452** |
| chunks ngoài 329 ID | 136.087 | **136.087 (nguyên vẹn)** |

- `integrity_check` = `ok`; `foreign_key_check` = rỗng; FTS `integrity-check` = `ok`.
- 329/329 ID mới: mảnh + retrievable + dense + sparse khớp manifest.
- **5 ID cũ đối chứng trực tiếp backup ↔ production** (không đổi một dòng):

| ID | retrievable (backup → prod) | dense | sparse |
| --- | --- | --- | --- |
| `wsc-154101d384acc2d01009025d` | 15 → 15 | 15 → 15 | 15 → 15 |
| `wsc-9e3e7cbc01ed57332c1384eb` | 345 → 345 | 345 → 345 | 345 → 345 |
| `wsc-a1a89391eee709a956a46130` | 274 → 274 | 274 → 274 | 274 → 274 |
| `wsc-58589483c646877fdb341f46` | 11 → 11 | 11 → 11 | 11 → 11 |
| `wsc-cc7d383bb6f7b9127bcaef00` | 31 → 31 | 31 → 31 | 31 → 31 |

(Ghi chú: danh sách 5 ID của vé 262b xếp cặp số 15/11/345/274/31 theo **thứ tự liệt kê trong vé**, không phải
theo ID; đối chiếu từng ID ở trên mới là chuẩn.)

## 5. Stamp `source_fingerprint` (bước 5) — `scratch/merge_gpu_dc_stamp.py`

### 5.1 Vì sao tái tạo `content_text` từ ZIP gốc

Delta thiếu `source_fingerprint` (như 262b). Với 262b, nguồn text là các file materialized do app tạo từ
**nguồn sổ** — nhưng **sổ PC0575 không chứa 329 nguồn DC** (đã kiểm tra: 0/329 ID trong
`local_cases/workspace_chat/notebook_sources.jsonl`). Vì vậy OMP tải **ZIP gốc** từ Drive và chạy lại **đúng
chuỗi trích xuất của app** (theo báo cáo gpu-dc của máy nhà):

- Nguồn ZIP: 858.190.286 B, SHA-256 `f18bbae2…18b7` — **khớp ghim**; bung đúng **344 file / 650.894.980 B** (khớp báo cáo máy nhà).
- `.xlsx/.xls` → `workspace_chat_excel.extract_xlsx_text` (**tên file đã sanitize** qua `sanitize_filename` — tên file nằm trong text nên quyết định hash; lần chạy đầu không sanitize làm 138 ID lệch);
  riêng `Màn hình trắng Iris.xlsx` (40 MB) vượt guard 10 MB → nhánh dự phòng engine registry
  (`ConverterRegistry` → `_element_text` từng vùng ghép `\n\n`), text **16.083 byte** khớp đúng báo cáo máy nhà.
- `.msg` → `extract_outlook_msg`; `.pdf/.html/.png/.bmp` → `document_extractors.extract_text_chunks_from_file`
  ghép `"\n\n"`; `.csv` → decode UTF-8 (nhánh `.txt` của app, không cap 200 KiB — theo quyết định máy nhà).
- Kết quả: **329/329 ID khớp manifest** (0 thừa/0 thiếu); 9 file loại đúng như báo cáo máy nhà
  (5 ảnh thiếu OCR + 1 PDF scan + 2 file khoá `~$` + 1 workbook rỗng); 6 đường dẫn trùng nội dung gộp 1 ID;
  tổng text **7.237.017 byte** — khớp **chính xác** tổng text báo cáo gpu-dc.
- Mọi fingerprint tự kiểm bằng bất biến `fingerprint.startswith(document_id[4:])` (SHA-256 đầy đủ của
  `text.strip()`), lưu ở `scratch/gpu-dc-fingerprints.json` (329 dòng) + bản `.txt` tại `C:/tmp/gpu-dc/materialized/`.

### 5.2 Stamp

- `plan`: 329/329 fingerprint hợp lệ (prefix khớp).
- Tạm `DROP TRIGGER chunks_fts_update` (AFTER UPDATE mọi cột, rất chậm nếu để nguyên) → `BEGIN IMMEDIATE` →
  `UPDATE chunks SET source_fingerprint=? WHERE document_id=? AND source_fingerprint IS NULL` cho đúng 329 ID →
  **12.720 dòng trong 12,5 giây** → `COMMIT` → **tạo lại trigger đúng nguyên văn DDL gốc** (so khớp `True`).
- Verify: `NULL` trong 329 ID = **0**; stamped = 12.720; `distinct` fingerprint = **329**;
  `NULL` toàn DB = **328** — đúng bằng số dòng NULL **có sẵn từ trước** ngoài phạm vi vé (không đụng).

## 6. Verify sau merge (bước 6, chỉ đọc) — `scratch/merge_gpu_dc_verify.py`

- Tổng: chunks 148.807 / retrievable 120.452 / dense = sparse 120.792 / FTS 120.452.
- 329/329 ID khớp mảnh+retrievable+dense+sparse; parent `retrievable=0` = **2.482** (không vector, không FTS — đúng ngữ nghĩa production).
- Fingerprint từng ID = giá trị kế hoạch (329/329); mỗi ID đúng 1 giá trị.
- **Cổng phủ thật qua pipeline** (có backend ONNX):
  `{"valid": true, "reason": "", "document_count": 329, "retrievable_chunk_count": 10238, "missing_document_ids": [], "fingerprint_mismatch_document_ids": [], "documents_complete": true, "dense_embedding_count": 10238, "sparse_embedding_count": 10238, "dense_complete": true, "sparse_complete": true}`.
- SHA-256 production sau merge: `e54c7745b86cb360d903c5e211827126b6c8d69606c8809bcdd7f90737c47fe7` (2.842.415.104 B).

## 7. App sau merge + smoke UI LAN

- App khởi động lại bằng `RUN_AIOS_WORKSPACE_CHAT.bat` (env `AIOS_RAG_V2_NUMPY_DENSE=1`,
  `AIOS_BGE_QUERY_TIMEOUT=1200`), listener `0.0.0.0:8501`, `/_stcore/health` = `ok` sau 10 giây;
  truy cập LAN `http://10.170.157.180:8501/` bình thường.
- Trang sổ "Điều tra lỗi LSU" hiển thị **33/35 nguồn ready** (không đổi sau merge — 329 tài liệu Điều chỉnh
  **không phải nguồn sổ** nên không được bật/tính vào cổng phủ của hội thoại; đúng thiết kế "chỉ nguồn bật mới dùng khi trả lời").
- Smoke (hội thoại `CONV-9C730D76`): câu hỏi E3
  *"Khi beam diameter NG thì cần kiểm tra những hạng mục nào (LD mirror, trục quang, độ sâu chỉnh)?"*
  - Gửi: **15:53:05** (store ghi 15:53:11) → trả lời: **16:06:17** = **786 giây (13m06s)** theo mốc store
    (so sánh trực tiếp: smoke 262b là 971 giây) — không chạm timeout `AIOS_BGE_QUERY_TIMEOUT=1200`.
  - Đáp án (tóm tắt): đo nghiêng LD mirror bằng máy đo 3 chiều (so OK/NG) + kẹp SIM vào LD mirror trên máy
    NG ASSY; đổi trục quang bằng JIG BEAM; kiểm tra Lens CYLINDRICAL / POLYGON / Lens F — khớp nội dung tài
    liệu, không bịa. Bằng chứng UI: screenshot trang trả lời (chụp trong phiên OMP).
  - Trace `trc_bef350a2629f` — **`valid`**, `cited_count = 3`, `insufficient_evidence = False`:
    `[1]` `Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx`, `[2]` `Dữ_liệu_tổng_hợp.xlsx`,
    `[3]` `RE__Iris_LSU_Beam径NG多発_異常品質会議2回目.msg` (đúng bộ 3 nguồn như smoke 262b).
  - Trạng thái app sau smoke: `/_stcore/health` = `ok`; `http://10.170.157.180:8501/` → HTTP 200;
    log app (`scratch/app_lan_merge_gpu_dc_20261001.log`) không có dòng lỗi/timeout.
  - Ghi chú phạm vi: 329 tài liệu Điều chỉnh **không được bật làm nguồn** trong hội thoại này (không phải
    nguồn sổ) nên smoke chỉ chứng minh app + index sau merge hoạt động đúng trên tập nguồn bật — muốn hỏi đáp
    trực tiếp trên bộ Điều chỉnh cần bật nguồn (mục 8).

## 8. Đề xuất cho Muse

1. Exporter delta (máy nhà) nên mang theo `source_fingerprint` cho mọi dòng (đã đề xuất từ 262b, lặp lại —
   lần này OMP phải tái tạo chuỗi trích xuất từ ZIP gốc để tính; tốn thêm một vòng tải 858 MB + chạy extraction).
   Nếu chưa sửa được ở exporter, nên ghi rõ trong vé merge các điều kiện khớp chuỗi:
   (a) tên file phải `sanitize_filename` trước khi trích Excel; (b) workbook >10 MB dùng nhánh dự phòng
   engine registry (`ConverterRegistry` + `_element_text`, ghép `\n\n`).
2. Trigger `chunks_fts_update` nên giới hạn cột (như `chunks_embeddings_content_update` đã làm) để UPDATE
   metadata không phải dựng lại FTS (vẫn phải DROP/tạo lại thủ công khi stamp hàng loạt).
3. 329 tài liệu Điều chỉnh hiện nằm trong index nhưng **chưa gắn nguồn sổ nào** — muốn hỏi đáp trên bộ này cần
   bật nguồn (việc của người dùng/Muse, ngoài phạm vi vé).
