# Trạng thái mailbox

- Trạng thái: `cho-muse`
- Ticket hiện tại: `UX-AGENT-UI-FIX1-VERIFY` — [NHÀ] verify lại sau vá `f1dc433`. Verify lần 2 CHƯA ĐẠT. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `3ce1d66`
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (mục 7, verify lần 2)
- `ghi_chu`: 2026-10-03 18:59 +07 — Verify lần 2 CHƯA ĐẠT, dừng `cho-muse`. Tạo file được (hết lỗi đường dẫn). Mục 2 Hoàn tác PASS (SHA về `0e3ffa4b…bd48`). Mục 1 FAIL: nút Tải về bị mờ vì `is_safe_artifact_path` không cho `~/AIOS_bao_cao`. Mục 3 FAIL: Xem toàn văn của `.docx` không mờ; cả `.md` và `.docx` báo file không còn dù file còn trên đĩa. Index không đổi. Cổng lệnh PASS (51 test, audit PASS). Không sửa code.
- `ghi_chu` (lịch sử): UX-AGENT-UI verify lần 1 CHƯA ĐẠT 18:32 (đã vá `f1dc433`); lần 2 CHƯA ĐẠT 18:59 (nút thẻ). Trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
