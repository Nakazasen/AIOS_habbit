# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé 0 — Điều tra nhịp rơi (đã báo cáo; Vé B đang dừng, chờ vé xử lý lỗi I/O)
- Ticket trước: Vé B — đường GPU (đã ghi 6.128/99.003 khối rồi dừng do `sqlite3.OperationalError: disk I/O error`; Vé 0 không restart/resume)
- Ticket trước nữa: Vé A — chốt điểm dừng G1 (xong, báo cáo `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`)
- Commit: `fa41d8e` (báo cáo Vé 0; Vé B chưa hoàn tất)
- Báo cáo: `docs/phieu-viec/ket-qua/VE0_dieu-tra-nhip-roi.md`
- Ghi chú: 2026-09-27 17:32 +0700 (máy h410asrock) — Vé 0 báo cáo: `integrity_check` chỉ-đọc = `ok`; tiến trình dừng sau 6.128/99.003 khối; nhịp cuối 0,723 khối/giây, ETA có điều kiện 35,7 giờ. Chưa resume; không sửa mã/chỉ mục/bản sao lưu.
- Cập nhật lần cuối: 2026-09-27 17:32 +0700 (OMP — hoàn tất báo cáo điều tra Vé 0)
