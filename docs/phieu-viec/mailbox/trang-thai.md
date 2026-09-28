# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ). Quyết định tuyến do user ủy quyền Muse chốt 2026-09-28 20:55 +07.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu`: 2026-09-28 ~21:00 +07 (Muse VM) — Review P1.3: sao lưu + chép kho ĐẠT (SHA khớp, quick_check ok); B1–B5 chưa chạy nên P1.3 CHƯA ĐẠT nghiệm thu. Chốt tuyến NỘI BỘ cho B1–B5 (cấm AI ngoài vì DATA_POLICY.md dòng 39: local_only "tuyệt đối không được gửi tới provider"). ĐẠT P1.4 = P1.3 đóng. Lưu ý: branch head vẫn `9b0ac6a` — fix PYTHONPATH (bge_subprocess_client.py) chưa được commit; nếu B1–B5 gặp lỗi worker subprocess, OMP tự xử lý theo vé.
- Ticket trước: Vé KHẨN — OMP đã dừng theo vé, cây sạch, mọi thứ đã trên nhánh (head `9b0ac6a`).
