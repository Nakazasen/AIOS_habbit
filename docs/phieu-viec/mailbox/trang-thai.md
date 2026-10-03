# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `UX-AGENT-UI-FIX2-VERIFY` — [NHÀ] verify lại sau vá `0a0716f` (verify lần 4). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: `0a0716f`
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (mục 8, verify lần 3)
- `ghi_chu` (điều phối Muse): 2026-10-03 ~19:30 +07 — Thấy cờ `cho-muse` 19:19 (verify lần 3 CHƯA ĐẠT). Muse đã vá (commit `0a0716f`): thẻ đính kèm giờ fallback sang kiểm đúng `result_path` trong comment metadata khi không có dòng `agent_work_items` (helper mới `verify_card_result_path` trong `agent_report_artifact.py`); vẫn chặn `..` và file ngoài gốc. Kiểm chứng VM: 63 passed (4 regression test mới), `compileall` OK, `cli audit` PASS, import app được, code tương thích Python 3.11. Vé verify lần 4 phát hành; mục 2 đã PASS lần 3 → verify lại mục 1 + 3, kèm 2/4/5 nhanh. Nếu còn FAIL: ghi đúng mục + bằng chứng, đặt lại `cho-muse`, không sửa code.
- `ghi_chu` (lịch sử): Verify lần 4 phát hành ~19:30 sau vá `0a0716f`; lần 3 CHƯA ĐẠT 19:19 (thẻ ARE-* không có dòng việc) → `cho-muse`; lần 2 CHƯA ĐẠT 18:59; lần 1 CHƯA ĐẠT 18:32 (đã vá `f1dc433`); trước đó UX-INTERVIEW-UI-FIX1-VERIFY ĐẠT ~18:25.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đang verify lại):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
