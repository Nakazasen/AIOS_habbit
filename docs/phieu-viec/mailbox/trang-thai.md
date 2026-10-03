# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `UX-AGENT-UI-FIX2-VERIFY` — [NHÀ] verify lại sau vá `ab70e69` (cổng an toàn thẻ đính kèm tin gốc `~/AIOS_bao_cao`). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: (đang verify)
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (bổ sung mục verify lần 3)
- `ghi_chu`: 2026-10-03 19:09 +07 — Nhận vé `UX-AGENT-UI-FIX2-VERIFY`. Watcher tự mở OMP lần 1/4 lúc 19:07:34 (`launchStallCount=1`). Điều kiện mở ĐÃ TỚI: `ab70e69` là tổ tiên của HEAD `64022a9` (`merge-base --is-ancestor` exit 0). Không đặt `cho-muse`, không rơi nhánh 4-lần-watcher. Bắt đầu verify app 8515, không đặt `AIOS_DOC_ROOT`.
- `ghi_chu` (điều phối Muse): 2026-10-03 ~19:15 +07 — Thấy cờ `cho-muse` lúc 19:03 (verify lần 2 CHƯA ĐẠT 18:59: nút Tải về bị mờ, Xem toàn văn `.md` báo sai, `.docx` không bị mờ). Muse đã vá: điểm gọi `is_safe_artifact_path` ở thẻ đính kèm chat giờ truyền `allowed_roots=(default_doc_root(),)`; vẫn chặn `..`. Kiểm chứng VM: 59 passed (gồm regression test mới), `compileall` OK, `cli audit` PASS, import app được. Mục 2 (Hoàn tác) đã PASS lần 2 → vé này verify lại mục 1 + 3, kèm mục 2/4/5 nhanh. Nếu còn FAIL: ghi đúng mục + bằng chứng, đặt lại `cho-muse`, không sửa code.
- `ghi_chu` (lịch sử): Verify lần 2 CHƯA ĐẠT 18:59 (nút thẻ) → `cho-muse`; lần 1 CHƯA ĐẠT 18:32 (đã vá `f1dc433`); trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
