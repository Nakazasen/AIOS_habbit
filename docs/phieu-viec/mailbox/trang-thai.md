# Trạng thái mailbox

- Trạng thái: `cho-muse`
- Ticket hiện tại: `UX-AGENT-UI-FIX2-VERIFY` — [NHÀ] verify lại sau vá `ab70e69`. Verify lần 3 CHƯA ĐẠT. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `4006b0e`
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (mục 8, verify lần 3)
- `ghi_chu`: 2026-10-03 19:19 +07 — Verify lần 3 CHƯA ĐẠT, dừng `cho-muse`. Tạo file được. Mục 2 Hoàn tác PASS (SHA về `0e3ffa4b…bd48`). Mục 1 FAIL: nút Tải về vẫn mờ (`disabled=true`). Mục 3 FAIL: Xem toàn văn `.docx` không mờ; cả `.md` và `.docx` báo file không còn dù file còn trên đĩa. `is_safe_artifact_path` kèm `default_doc_root()` trả đúng, nhưng thẻ không có dòng `agent_work_items` nên không dùng đường dẫn đó. Index không đổi. Cổng lệnh PASS (59 test, audit PASS). Không sửa code.
- `ghi_chu` (điều phối Muse): 2026-10-03 ~19:15 +07 — Thấy cờ `cho-muse` lúc 19:03 (verify lần 2 CHƯA ĐẠT 18:59: nút Tải về bị mờ, Xem toàn văn `.md` báo sai, `.docx` không bị mờ). Muse đã vá: điểm gọi `is_safe_artifact_path` ở thẻ đính kèm chat giờ truyền `allowed_roots=(default_doc_root(),)`; vẫn chặn `..`. Kiểm chứng VM: 59 passed (gồm regression test mới), `compileall` OK, `cli audit` PASS, import app được. Mục 2 (Hoàn tác) đã PASS lần 2 → vé này verify lại mục 1 + 3, kèm mục 2/4/5 nhanh. Nếu còn FAIL: ghi đúng mục + bằng chứng, đặt lại `cho-muse`, không sửa code.
- `ghi_chu` (lịch sử): Verify lần 3 CHƯA ĐẠT 19:19 (nút thẻ vẫn mờ, không có dòng việc) → `cho-muse`; lần 2 CHƯA ĐẠT 18:59; lần 1 CHƯA ĐẠT 18:32 (đã vá `f1dc433`); trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
