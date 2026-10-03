# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: `INDEX-NGUON-KIEM-KE` — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `18a0ab4`
- `bao_cao`: `docs/phieu-viec/ket-qua/index-nguon-kiem-ke.md`
- `ghi_chu`: 2026-10-03 20:04:29 +07 — xong kiểm kê chỉ đọc. Đường vé `C:\AIOS_habit_index_ve03` đã bị xóa (don-canary), không chờ 4 lần. Kho app đang chạy: 889 document / 149.800 chunk, SHA trước=sau `45eb0e07…5b65b7c0`. Bốn nhóm đường dẫn nằm chung một collection `tri_thuc`; khối 496 không còn thư mục gốc MOM/LSU/Điều-tra trong `source_path`.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
