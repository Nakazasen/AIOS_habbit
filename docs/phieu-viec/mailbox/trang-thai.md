# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Vé P1 — Đóng dấu kho thử thành kho thật trên Windows máy nhà (chỉ kiểm toàn vẹn + backup production + copy + đọc thử B1–B5; cấm ghi đè kho production khi chưa đủ dấu toàn vẹn)
- `commit`: `4ec8567`
- `bao_cao`: `docs/phieu-viec/ket-qua/VE_P1_dong-dau-kho-that.md`
- `ghi_chu`: 2026-09-28 05:06 +07 (OMP) — Bước 1 đạt; dừng an toàn ở Bước 2 vì chưa xác định được kho production trên ổ C. Báo cáo đã ghi rõ đường dẫn đã dò và yêu cầu Muse xác nhận.
- Ticket trước: Vé V1.4 — ĐẠT 2026-09-28 ~04:53: tải zip đường mới lần 1 (858.190.286 byte), 4/4 file khớp sha256, manifest 6/6 + error_cases 26/26 (F4 11/11) trên Windows, chỉ thao tác ổ C, không ghi index; báo cáo `docs/phieu-viec/ket-qua/VE_V1_4_F4-windows.md` (commit `c9148e5`); quyền anyone-with-link trên file zip đã thu hồi.
- Vé mẫu P1/P2 + tiêu chí G2 (đã push cùng nhịp này): `docs/phieu-viec/VE_P1_ve-mau-dong-dau-kho-that.md`, `docs/phieu-viec/VE_P2_ve-mau-may-cong-ty.md`, `docs/phieu-viec/G2_tieu-chi-nghiem-thu.md`
- Ticket trước nữa: Vé V1 — verify F1–F4 trên Windows (xong qua V1.4)
