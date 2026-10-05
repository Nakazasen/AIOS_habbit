# Vé RESTORE-INDEX-SPLIT-PC0575 — Tải 5 khối index từ Drive về, hợp lại thành kho chính

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `SPEED-COLDSTART-PC0575`, trước `WIRE-QA-CAGENT-PC0575`.
**Role gợi ý:** DEFAULT (tải file lớn + kiểm SHA).

## Bối cảnh

- Máy công ty đang chạy index TẠM `062ec090` (2,55GB) — bản này lệch nguồn LSU hiện tại
  (0/494 nguồn `NB-E35A7BEE` khớp), chỉ là giải pháp tình thế sau vụ mất dữ liệu 05/10.
- Máy nhà đã upload đủ 5 file khối tách của index production (`45eb0e07…`,
  889 document / 149.800 chunk) lên Drive, SHA tải lại khớp 100%
  (vé `UPLOAD-SPLIT-DRIVE-HOME`, verdict Muse ĐẠT 2026-10-05 ~23:39).
- Vé này: tải về + hợp lại + thay cho index TẠM để máy công ty "dùng mượt mà".

## Nguồn trên Drive

- Thư mục: `index-split-r5-backup` — ID `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`
- 5 file: `lsu` (1.155.637.248 B) + `dieu_tra_loi` (1.643.761.664 B) +
  `mom` (21.598.208 B) + `tong_hop` (36.081.664 B) + `domain_manifest.json` (491.253 B)
- Lưu ý: 2 link chia sẻ riêng (lsu, dieu_tra_loi) Drive đang chặn (thử lại 06/10 vẫn chặn)
  → tải qua link thư mục chung. Tuyệt đối không bịa link/ID.
- Bảng SHA-256 đầy đủ trong `docs/phieu-viec/ket-qua/upload-split-drive-home.md`.

## Việc cần làm (đúng thứ tự)

1. Tải đủ 5 file về máy công ty. Nếu `drive.google.com` timeout thì dùng endpoint
   `drive.usercontent.google.com/download` (vé RESTORE-DRIVE đã chứng minh được).
2. Đối chiếu SHA-256 từng file với báo cáo upload — lệch 1 byte cũng tải lại, không làm tiếp.
3. Hợp 4 khối thành `library.sqlite` hoàn chỉnh theo manifest
   (xem cách tách trong báo cáo upload hoặc script split trong repo).
4. `PRAGMA integrity_check` phải = ok; đếm document/chunk (kỳ vọng ~889 / ~149.800).
5. DỪNG APP trước khi thay. Backup index TẠM ra thư mục khác (KHÔNG xóa).
6. Đặt index đã hợp vào đúng path app mong đợi — kiểm lại bằng deployment module
   (`python -B -m aios_habit.workspace_chat_rag_v2_deployment`), không hardcode path.
7. Audit deployment → `Status: PASS` + smoke 1 câu hỏi thật qua UI.

## Rào cứng

- Thiếu 1 file hoặc SHA lệch → DỪNG, báo rõ, không ráp bừa.
- Không ghi đè khi chưa backup bản TẠM. Không merge `main`.
- Code tương thích Python 3.11. Heartbeat mốc 15 phút/lần.

## Báo cáo

`docs/phieu-viec/ket-qua/restore-index-split-pc0575.md` — đủ: bảng SHA 5 file,
kết quả integrity_check, số document/chunk, kết quả audit + smoke.
