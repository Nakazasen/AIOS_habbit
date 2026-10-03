# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: `SCAN-O-D` — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `379435d`
- `bao_cao`: `docs/phieu-viec/ket-qua/scan-o-d.md`
- `ghi_chu`: 2026-10-03 20:30:06 +07 — xong kiểm kê chỉ đọc. 366 sqlite đủ SHA, size/mtime trước=sau. Kho C `45eb0e07…b7c0` khớp; bản đông D `062ec090…` khớp. Staging GPU-262 không có trên D, vẫn giữ trên C. Không xóa/sửa/di chuyển.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; còn lại sau khi phát hành `SCAN-O-D`):
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
