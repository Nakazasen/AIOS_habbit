# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `SCAN-O-D` — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `ghi_chu`: 2026-10-03 20:20:13 +07 — cây ổ D đã có số (chỉ đọc). Đang tính SHA-256 mọi file sqlite, gom theo inode để không đọc hai lần file trùng. Chưa xóa/sửa/di chuyển.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; còn lại sau khi phát hành `SCAN-O-D`):
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
