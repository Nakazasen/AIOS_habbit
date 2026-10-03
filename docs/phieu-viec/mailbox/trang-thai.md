# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `INDEX-NGUON-KIEM-KE` — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `ghi_chu`: 2026-10-03 19:58:02 +07 — OMP nhận vé. Đường vé ghi `C:\AIOS_habit_index_ve03\library.sqlite` không còn (đã xóa ở don-canary, không phải cổng chờ). Kho app đang resolve: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (2.942.201.856 byte, 2026-10-01 08:27). Sẽ mở file này `mode=ro`, không ghi.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
