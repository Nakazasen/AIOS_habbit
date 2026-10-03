# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `INDEX-NGUON-KIEM-KE` — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `ghi_chu` (verdict Muse): 2026-10-03 ~19:55 +07 — **ĐẠT** vé UX-AGENT-UI-FIX2-VERIFY (commit `16d4100`): cả 5 mục verify lần 4 PASS trên app 8515 thật — Tải về bấm được (file SHA khớp byte, Word mở 8 đoạn đúng câu), Hoàn tác trả SHA về đúng, .docx Xem toàn văn mờ / .md xem-thu đúng, SHA index production không đổi (`062ec090…`, 2.552.659.968 byte), cổng 63 passed + cli audit PASS + import OK trên Python 3.11.14. Thẻ phỏng vấn cũ không vỡ. Ghi chú cosmetic: nhãn nút vẫn "Tải về .md" dù file tải là `.docx` — không chặn, có thể gọt sau. Phát hành vé xếp hàng tiếp theo #6 `INDEX-NGUON-KIEM-KE` theo thứ tự hàng chờ.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
