# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `SCAN-O-D` — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `ghi_chu`: 2026-10-03 20:11:36 +07 — đang quét cây ổ D chỉ đọc (metadata + SHA sqlite). Chưa xóa/sửa/di chuyển file nào. Gate vẫn 1/4, không cho-muse.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; còn lại sau khi phát hành `SCAN-O-D`):
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
