# Operator Runbook

## Luồng dùng hằng ngày

1. Mở `RUN_AIOS_WORKSPACE_CHAT.bat`.
2. Tạo hoặc chọn workspace phù hợp.
3. Tạo hoặc chọn knowledge notebook; thêm nguồn cục bộ khi cần.
4. Kiểm tra nhãn privacy trước khi hỏi về nguồn.
5. Đặt câu hỏi tự nhiên trong Workspace Chat; dùng source context/citations để
   kiểm tra câu trả lời.
6. Khi thông tin chưa đủ, bổ sung nguồn hoặc giữ kết quả ở trạng thái cần review;
   không biến claim chưa có evidence thành kết luận chắc chắn.

## Xử lý sự cố

- Nếu launcher báo thiếu dependency: chạy `py -3 -m pip install -e .` tại root
  repository rồi mở launcher lại.
- Nếu nguồn không được dùng: kiểm tra notebook/source đang chọn và privacy
  setting trước khi thay đổi code.
- Không đưa raw local documents, secrets hoặc runtime data vào Git/cloud.

Developer xem [developer.md](runbooks/developer.md) thay vì dùng tài liệu này để
chạy test/audit/release.
