# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé 0.3 — Chuyển index sang ổ C (SSD) + resume migration GPU (cấm ghi ổ D vĩnh viễn)
- Ticket trước: Vé 0.2 — chẩn đoán disk I/O (ĐÃ DUYỆT 2026-09-27 ~18:42, báo cáo `docs/phieu-viec/ket-qua/VE0_2_chan-doan-disk-io-error.md`)
- Ticket trước nữa: Vé 0 — điều tra nhịp rơi (ĐÃ DUYỆT 2026-09-27 ~18:15, báo cáo `docs/phieu-viec/ket-qua/VE0_dieu-tra-nhip-roi.md`)
- Commit mới nhất: (chưa có — đang làm Vé 0.3)
- Báo cáo: `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` (chưa có)
- Ghi chú: OMP h410asrock 2026-09-27 18:38 +07 — SMART tươi ổ D: 05 Reallocated 769 (tăng từ 513), C4 Event 10 (tăng từ 9), C5 Pending 0, C6 0, C7 UDMA CRC 200, Health Chú ý (vàng), 38°C; SSD C còn 91% life. Theo quyết định user 19:04, bỏ chkdsk và tuyệt đối không ghi D.
- Ghi chú: Muse 2026-09-27 19:04 +07 — index chuyển sang C; copy + integrity_check đạt mới tiếp tục; mẻ ghi ngoài 10–20 (đề xuất 16), batch GPU trong giữ 2; mẫu theo dõi 3 mốc, integrity và I/O.
- Ghi chú: OMP h410asrock 2026-09-27 19:15 +07 — mốc Bước 2: chọn SSD C (ban đầu còn 5,43 GiB), sao chép `library.sqlite` sang `C:\AIOS_habit_index_ve03\library.sqlite` (1.750.740.992 byte); SHA-256 hai bản cùng `31E80A9497B3C64F8BFD7EDE0233F6EAF0526F55C78D5D694BFCCDAF69452FDA`; `PRAGMA integrity_check` trên bản C = `ok`. C còn 4.028.096.512 byte sau clone mailbox và bản sao index. Bản D không bị ghi.
- Cập nhật lần cuối: 2026-09-27 19:15 +07 (OMP — mốc Bước 2 Vé 0.3)
