# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `UX-AGENT-UI-FIX2-VERIFY` — [NHÀ] verify lần 4 sau vá `0a0716f`. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `a44338a`
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (sẽ bổ sung mục verify lần 4)
- `ghi_chu` (OMP): 2026-10-03 19:32 +07 — App thử 8515 đã lên (health ok). `AIOS_DOC_ROOT` không đặt. `AIOS_FEATURE_CHAT_ACTION=1`. Không đụng 8501/8585. SHA index trước: `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`. Đang mở sổ E2EUxApp để verify mục 1.
- `ghi_chu` (lịch sử): Verify lần 4 phát hành ~19:30 sau vá `0a0716f`; lần 3 CHƯA ĐẠT 19:19 (thẻ ARE-* không có dòng việc) → `cho-muse`; lần 2 CHƯA ĐẠT 18:59; lần 1 CHƯA ĐẠT 18:32 (đã vá `f1dc433`); trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
