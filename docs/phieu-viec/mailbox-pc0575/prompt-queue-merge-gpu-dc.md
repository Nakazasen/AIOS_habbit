# Ticket XẾP HÀNG (mailbox-pc0575): merge-gpu-dc — nhập 329 tài liệu Điều chỉnh từ delta GPU-DC vào production

> **CHƯA PHÁT HÀNH** — vé này chỉ được Muse phát hành (copy vào `prompt.md`,
> `trang-thai.md` → `moi`) khi TẤT CẢ điều kiện dưới đây đã đủ. OMP/watcher
> PC0575 không tự nhặt vé này.

## Điều kiện phát hành
1. Vé `merge-gpu262b` trên PC0575 đã `xong-cho-duyet` + có verdict của Muse
   (KHÔNG merge 2 gói cùng lúc — tránh 2 lần ghi production chồng nhau).
2. File delta đã có trên Drive (vé `upload-delta-drive` trên máy nhà đã đẩy + verify ẩn danh; link trong báo cáo `docs/phieu-viec/ket-qua/upload-delta-drive.md`, thư mục AIOS_Data):
   `gpu-dc-delta-20261001.zip` (**74.065.213 byte**,
   SHA-256 `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3`).
   - Link Drive: `https://drive.google.com/file/d/1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ/view?usp=sharing`
   - Tải trực tiếp (không cần đăng nhập): `https://drive.usercontent.google.com/download?id=1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ&export=download&confirm=t`
   Tải file từ Drive về máy (thư mục scratch), verify SHA-256 khớp ghim trên mới làm tiếp. Nếu đến giờ chạy mà
   file chưa có trên Drive → mailbox `cho-muse`, ghi rõ "chưa nhận được delta".

## Bối cảnh
Máy nhà đã nhúng GPU 344 tài liệu Điều chỉnh (10.238/10.238 chunk, fingerprint `016c5255…`,
verdict ĐẠT 2026-10-01, commit `805392f`) và đóng gói delta:
- `gpu-dc-delta-20261001.sqlite` — 228.937.728 byte,
  SHA-256 `a0ca1345b62a5d95867bb62f5790a40b3bd5f46704002323731c68822ad1cec3`
- `gpu-dc-manifest-20261001.json` — kê khai 329 tài liệu / 12.720 mảnh / 10.238 retrievable:
  nhập **toàn bộ 329 ID** (`skip_existing_document_ids = []` — đối chiếu với production, không ID nào trùng).

Thành phần 12.720 chunk: 10.238 chunk retrievable **có vector** (đã nhúng GPU) + 2.482 parent chunk
**chỉ giữ ngữ cảnh, không vector** (`retrievable=0` — đúng ngữ nghĩa app và production thật; chèn kèm để giữ ngữ cảnh).

Production đích:
`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`

## Việc cần làm
1. Tải zip từ Drive về scratch, verify SHA-256 khớp ghim trên → bung ra thư mục tạm (trên C hoặc
   scratch, KHÔNG bung đè lên production). Verify SHA sqlite trong zip khớp ghim trên.
2. Dry-run merge (chỉ đọc): đọc manifest, liệt kê 329 ID sẽ nhập; kiểm tra fingerprint delta =
   `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` trên cả 2 bảng vector;
   kiểm tra **không ID nào trùng** production (document_id + chunk_id). Lệch bất kỳ điểm nào → DỪNG,
   mailbox `cho-muse`, ghi rõ.
3. Backup production: copy `library.sqlite` production sang bản backup mới có
   timestamp; SHA-256 + `PRAGMA integrity_check` → phải `ok` trước khi merge.
4. Apply: import 329 ID từ delta vào production, kèm 2.482 parent chunk giữ ngữ cảnh.
   Luật cứng: nếu phát hiện trùng `document_id`/`chunk_id` với production thì DỪNG
   (không skip lặng lẽ, không ghi đè), mailbox `cho-muse`.
5. Stamp `source_fingerprint` cho các dòng vừa merge (bài học từ merge-gpu262b 13:14
   2026-10-01: delta xuất thiếu trường này → app chặn truy vấn ở cổng phủ
   `document_identity_mismatch`). Cách làm an toàn đã kiểm chứng: UPDATE chỉ các
   dòng `source_fingerprint IS NULL` thuộc đúng 329 ID mới (không đụng dòng cũ);
   trước UPDATE tạm DROP trigger `chunks_fts_update` (trigger này AFTER UPDATE mọi
   cột nên buộc dựng lại FTS từng dòng — rất chậm), UPDATE xong tạo lại trigger
   **đúng nguyên văn DDL gốc** và kiểm khớp. Verify: `NULL=0`.
6. Verify sau merge (chỉ đọc): 329/329 ID mới `retrievable=1` đủ dense+sparse,
   2.482 parent `retrievable=0`; fingerprint `016c5255…`; `integrity_check=ok`;
   cổng phủ `valid=True`; ghi SHA production mới. Restart app + smoke 1 câu hỏi trên UI LAN.
7. Mailbox → `xong-cho-duyet` + báo cáo `docs/phieu-viec/ket-qua/merge-gpu-dc.md`
   (ghi rõ: SHA zip/sqlite đã verify, SHA backup, 329 ID đã nhập, kết quả smoke).

## Cấm
- Không ghi đè bất kỳ dòng nào đã tồn tại trong production. Không merge khi backup chưa ok.
- Không merge khi `merge-gpu262b` chưa xong. Không merge `main`. Không force-push.
- Không nhúng lại CPU 10.238 chunk đã có vector (delta mang vector sẵn, chỉ import).
