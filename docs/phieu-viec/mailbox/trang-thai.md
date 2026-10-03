# Trạng thái mailbox

- Trạng thái: `xong`
- Ticket hiện tại: `DON-O-C` — [NHÀ] dọn ổ C (rác tmp → venv trùng → worktree → backup cũ sau kiểm toàn vẹn). Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy nguyên văn `prompt-queue-don-o-c.md`).
- `commit`: `3302ec4`
- `bao_cao`: `docs/phieu-viec/ket-qua/don-o-c-may-nha.md`
- `verdict`: ĐẠT (Muse review 2026-10-03 ~20:52 +07). 5/5 bước làm đúng vé: liệt kê → xác minh; không xóa file nào vì không mục nào đủ điều kiện chắc chắn (rác tmp: 0 file quá 7 ngày; venv: không có bản trùng nào trên ổ C — các bản tạm đã xóa 29/09; worktree vé 0.3 đã xóa 29/09; backup: chỉ còn 1 bản rollback duy nhất của kho trước merge → GIỮ theo luật "không xóa nếu chỉ còn 1 bản backup"). Production SHA `45eb0e07…b7c0` khớp ghim, `integrity_check=ok` đo lại chỉ đọc; không đụng ổ D, cây ONNX, index production. Mục tiêu ~8 GB của vé đã đạt từ lần dọn 29/09 (thu hồi 9,1 GiB) — lần phát hành lại này xác nhận không còn mục an toàn nào để dọn thêm.
- `ghi_chu`: 2026-10-03 ~20:52 +07 — hàng chờ máy nhà đã cạn; CHƯA merge `main` (điều kiện duyệt merge ngày 29/09: E-series verify ĐẠT — chưa đủ). Đề xuất của OMP: `C:\tmp` còn ~7,9 GB ứng viên dọn nhưng nằm ngoài 4 đường vé cho phép → cần vé riêng nêu rõ đường được xóa, do user phê duyệt danh sách.
- `hang-cho` (còn lại sau khi phát hành `DON-O-C`): hết — hàng chờ máy nhà đã cạn.
