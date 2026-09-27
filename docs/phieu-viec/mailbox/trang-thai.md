# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Vé P1.1 — Hoàn tất đóng dấu kho thật (sửa đường dẫn production; bước 1 của P1 đã đạt, không làm lại)
- `commit`: `bdda73c`
- `bao_cao`: `docs/phieu-viec/ket-qua/VE_P1_1_dong-dau-kho-that.md`
- `ghi_chu`: 2026-09-28 05:18 +07 (OMP) — Dừng fail-closed: storage_root rỗng, chưa xác định production; không sao lưu/chép kho hoặc chạy B1–B5. Báo cáo commit `bdda73c`; chờ xác nhận runtime/profile production.
- Ticket trước: Vé P1 — CHƯA ĐẠT đóng dấu 2026-09-28 ~05:10: bước 1 đạt (integrity ok, 107331/107331 ONNX, fingerprint khớp, pending=0); bước 2–5 chưa chạy vì không xác định được kho production trên ổ C; báo cáo `docs/phieu-viec/ket-qua/VE_P1_dong-dau-kho-that.md` (commit `4ec8567`).
- Ticket trước nữa: Vé V1.4 — ĐẠT 2026-09-28 ~04:53: tải zip đường mới lần 1 (858.190.286 byte), 4/4 file khớp sha256, manifest 6/6 + error_cases 26/26 (F4 11/11) trên Windows, chỉ thao tác ổ C, không ghi index; báo cáo `docs/phieu-viec/ket-qua/VE_V1_4_F4-windows.md` (commit `c9148e5`); quyền anyone-with-link trên file zip đã thu hồi.
