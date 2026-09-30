# Ticket XẾP HÀNG (mailbox-pc0575): merge-gpu262b — nhập 14 tài liệu mới từ delta GPU-262b vào production

> **CHƯA PHÁT HÀNH** — vé này chỉ được Muse phát hành (copy vào `prompt.md`,
> `trang-thai.md` → `moi`) khi TẤT CẢ điều kiện dưới đây đã đủ. OMP/watcher
> PC0575 không tự nhặt vé này.

## Điều kiện phát hành
1. Vé `hodap-lsu-loi` trên PC0575 đã `xong-cho-duyet` + có verdict của Muse
   (KHÔNG merge giữa lúc PC0575 đang test hỏi đáp — tránh đổi corpus giữa chừng).
2. File delta đã có trên Drive (vé `upload-delta-drive` trên máy nhà đã đẩy + verify ẩn danh; link trong báo cáo `docs/phieu-viec/ket-qua/upload-delta-drive.md`, thư mục AIOS_Data):
   `D:\Sandbox\AIOS_habbit\scratch\gpu-262b-delta-20261001.zip`
   (20.867.536 byte,
   SHA-256 `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85`).
   Tải file từ Drive về máy (thư mục scratch), verify SHA-256 khớp ghim trên mới làm tiếp. Nếu đến giờ chạy mà
   file chưa có trên Drive → mailbox `cho-muse`, ghi rõ "chưa nhận được delta".

## Bối cảnh
Máy nhà đã nhúng GPU 19 tài liệu phi-CSV (2.883 chunk, fingerprint `016c5255…`,
verdict ĐẠT 2026-10-01) và đóng gói delta:
- `gpu-262b-delta-20261001.sqlite` — 57.020.416 byte,
  SHA-256 `b4b6f0bf059f544b606cfb7c33b315d72a5dc9c3a9b9a3591dc4cbfc47cf944a`
- `gpu-262b-manifest-20261001.json` — kê khai 19 tài liệu / 2.883 mảnh:
  nhập **14 ID mới**, **SKIP 5 ID đã có** trong production PC0575, tuyệt đối không ghi đè.

5 ID SKIP (đã có vector trong production, cấm ghi đè):
- `wsc-154101d384acc2d01009025d` (`Tài_liệu_đào_tạo_LSU_2019.01.18_K.pptx`)
- `wsc-9e3e7cbc01ed57332c1384eb` (biên bản lỗi kỳ 2 .msg)
- `wsc-a1a89391eee709a956a46130` (`tổng_hợp_dữ_liệu_dán_tape.xlsx`)
- `wsc-58589483c646877fdb341f46` (`Dữ_liệu_tổng_hợp.xlsx`)
- `wsc-cc7d383bb6f7b9127bcaef00` (`dữ_liệu_tổng_hợp_CaV2__1240_.xlsx`)

Production đích:
`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`

## Việc cần làm
1. Verify SHA-256 file zip khớp ghim trên → bung ra thư mục tạm (trên C hoặc
   scratch, KHÔNG bung đè lên production). Verify SHA sqlite trong zip khớp
   ghim trên.
2. Dry-run merge (chỉ đọc): đọc manifest, liệt kê 14 ID sẽ nhập + 5 ID sẽ skip;
   kiểm tra fingerprint delta = `016c5255…` trên cả 2 bảng vector; kiểm tra 5 ID
   skip ĐÚNG là đã tồn tại trong production (document_id khớp, đủ dense+sparse).
   Lệch bất kỳ điểm nào → DỪNG, mailbox `cho-muse`, ghi rõ.
3. Backup production: copy `library.sqlite` production sang bản backup mới có
   timestamp; SHA-256 + `PRAGMA integrity_check` → phải `ok` trước khi merge.
4. Apply: import 14 ID mới từ delta vào production. Luật cứng: KHÔNG ghi đè
   bất kỳ dòng nào của 5 ID cũ — nếu phát hiện trùng `chunk_id` thì DỪNG
   (không skip lặng lẽ), mailbox `cho-muse`.
5. Verify sau merge (chỉ đọc): 14/14 ID mới `retrievable=1`, đủ dense+sparse,
   fingerprint `016c5255…`; `integrity_check=ok`; ghi SHA production mới.
   Restart app + smoke 1 câu hỏi trên UI LAN.
6. Mailbox → `xong-cho-duyet` + báo cáo `docs/phieu-viec/ket-qua/merge-gpu262b.md`
   (ghi rõ: SHA zip/sqlite đã verify, SHA backup, 14 ID đã nhập, 5 ID đã skip,
   kết quả smoke).

## Cấm
- Không ghi đè 5 ID đã tồn tại. Không merge khi backup chưa ok.
- Không merge `main`. Không force-push.
