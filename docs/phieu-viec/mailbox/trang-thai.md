# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `UX-AGENT-UI-FIX1-VERIFY` — [NHÀ] verify lại 4 mục UX-AGENT-UI trên app thật sau khi Muse vá lỗi gốc doc root (commit `f1dc433`). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: (đang verify)
- `ghi_chu`: 2026-10-03 18:52 +07 — Mốc 2: câu tạo `tuan.docx` đã chạy trên app 8515 (hội thoại `CONV-1DFEBF40`, sổ `E2EUxApp`). File có trên đĩa, nội dung đúng. Đang kiểm 3 nút thẻ: nút Tải về đang bị mờ. Tiếp tục mục Hoàn tác và `.md`.
- `ghi_chu`: 2026-10-03 18:41 +07 — Nhận vé `UX-AGENT-UI-FIX1-VERIFY`. Watcher tự mở OMP lần 1/4 lúc 18:39:24 (`launchStallCount=1`). Điều kiện mở ĐÃ TỚI: `f1dc433` là tổ tiên của HEAD `2e9393d` (`merge-base --is-ancestor` exit 0). Không đặt `cho-muse`, không rơi nhánh 4-lần-watcher. Bắt đầu verify app 8515, không đặt `AIOS_DOC_ROOT`.
- `ghi_chu` (điều phối Muse): 2026-10-03 ~18:45 +07 — Nhận cờ `cho-muse` 18:32+07 (verify lần 1 CHƯA ĐẠT: mục 1 FAIL — app 8515 từ chối "Đường dẫn nằm ngoài thư mục làm việc" vì `chat_action_agent_report._default_doc_root()` → `~/AIOS_bao_cao` nhưng `agent_doc_edit._safe_path()` → `cwd` khi thiếu `AIOS_DOC_ROOT`). Muse đã vá độc lập trên VM: hàm dùng chung `default_doc_root()` → cả hai lớp cùng gốc `~/AIOS_bao_cao`, cổng `_safe_path` giữ nguyên (commit `f1dc433`); kiểm chứng VM 51 test pass + `cli audit` PASS + import app OK + Python 3.11-compatible. Phát hành vé verify lại, giữ nguyên `hang-cho` 6–8.
- `ghi_chu` (lịch sử): UX-AGENT-UI verify lần 1 CHƯA ĐẠT 18:32 (mục 1 FAIL, đã vá `f1dc433`); trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25, UX-INTERVIEW-UI ĐẠT ~16:55, UX-E2E-APP-R2 ĐẠT ~16:33.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
