# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `UX-AGENT-UI` — [NHÀ] verify nút Tải về / Hoàn tác thẻ đính kèm trên app thật (theo báo cáo `docs/phieu-viec/ket-qua/ux-agent-ui-a.md`). Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `commit`: (chưa chạy)
- `bao_cao`: `docs/phieu-viec/ket-qua/ux-agent-ui-a.md` (bổ sung mục verify [NHÀ])
- `ghi_chu` (verdict Muse): 2026-10-03 ~18:25 +07 — **ĐẠT** vé `UX-INTERVIEW-UI-FIX1-VERIFY` (báo cáo `docs/phieu-viec/ket-qua/ux-interview-ui-fix1.md`, mailbox commit `6c34b2d`, HEAD lúc duyệt `13b233b`). Bằng chứng độc lập (Commits API): `6c34b2d` chỉ thêm 1 file báo cáo và là tổ tiên của HEAD; fix `f521566` là tổ tiên của HEAD (compare `f521566...44b069c` behind_by=0). (1) mục 3 PASS: chữ "✅ Đã lưu nháp chờ duyệt (phiên IS-744426A0, 3 đáp án)." giữ ổn định trên app 8515 sau rerun (8 lần poll, không rơi "hết hạn"); sqlite 3 đáp án mới `reviewer_status=cho_chuyen_gia_phan_hoi`; (2) regression 1, 2, 4, 5, 6 PASS; (3) index production không đổi (`062ec090…ef8ca`); (4) `compileall` OK, pytest liên quan 75 passed, `cli audit` PASS, Python 3.11. Giới hạn đã ghi (không chặn): reload sau hoàn thành vẫn báo "hết hạn trong bộ nhớ" — chữ lưu nháp chỉ sống trong cùng phiên trình duyệt; app 8501/cầu nối 8585 không đụng. Phát hành vé xếp hàng #5 `UX-AGENT-UI` theo thứ tự hang-cho.
- `ghi_chu` (lịch sử): UX-E2E-APP-R2 ĐẠT ~16:33; UX-INTERVIEW-UI ĐẠT ~16:55→vé sửa FIX1 [VM] commit `f521566`, phát hành vé verify `UX-INTERVIEW-UI-FIX1-VERIFY`; ĐẠT ~18:25 → phát hành #5.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07; #5 `UX-AGENT-UI` đã phát hành 2026-10-03 ~18:25; #4 `UX-INTERVIEW-UI` ĐẠT; chèn #4 #5 do user gật 2 phương án UI 2026-10-03 ~16:10):
  6. `INDEX-NGUON-KIEM-KE` (`prompt-queue-index-nguon-kiem-ke.md`) — [NHÀ] kiểm kê document trong index production theo thư mục nguồn, CHỈ ĐỌC (mode=ro), làm căn cứ tách index thành 3 khối LSU / Điều-tra-lỗi / MOM theo yêu cầu user 2026-10-03.
  7. `SCAN-O-D` (`prompt-queue-scan-o-d.md`) — [NHÀ] kiểm kê + quét thao tác ổ D (chỉ đọc metadata/SHA, không xóa/sửa); user duyệt viết vé 2026-10-03.
  8. `DON-O-C` (`prompt-queue-don-o-c.md`) — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn); XÓA BACKUP phải có danh sách GB từng mục để user gật trước khi xóa.
