# Sổ Tay Vận Hành (Operator Runbook)

Status: `ACTIVE`
Owner role: Operator / local data owner
Last reviewed: 2026-07-25
Review cadence: Before release and after an operational workflow change

## Luồng Sử Dụng Hằng Ngày (Daily Usage Flow)

1. Mở tệp `RUN_AIOS_WORKSPACE_CHAT.bat`.
2. Tạo hoặc chọn workspace phù hợp.
3. Tạo hoặc chọn sổ ghi chép tri thức (knowledge notebook); thêm nguồn dữ liệu cục bộ khi cần.
4. Kiểm tra nhãn quyền riêng tư (privacy label) trước khi đặt câu hỏi về nguồn dữ liệu.
5. Đặt câu hỏi tự nhiên trong Workspace Chat; sử dụng ngữ cảnh nguồn / trích dẫn (source context/citations) để kiểm chứng câu trả lời.
6. Khi thông tin chưa đủ, bổ sung thêm nguồn hoặc giữ kết quả ở trạng thái cần đánh giá; tuyệt đối không biến các tuyên bố chưa có bằng chứng (evidence) thành kết luận chắc chắn.

## An Toàn Vận Hành (Operational Safety)

- Tuyệt đối không đưa tài liệu thô cục bộ, thông tin bí mật (secrets), runtime JSONL/SQLite, ảnh chụp màn hình hoặc gói chẩn đoán (diagnostic bundle) vào Git / cloud / issue công khai.
- Provider AI bên ngoài là tùy chọn (optional); khi gặp sự cố provider, ưu tiên quay về luồng chỉ dùng cục bộ (local-only).
- Tuyệt đối không tự ý xóa hoặc ghi đè thư mục `local_cases/` để "sửa nhanh" khi chưa sao lưu (backup).

## Sổ Tay Vận Hành Liên Quan (Related Runbooks)

- [Xử lý sự cố (Troubleshooting)](operations/TROUBLESHOOTING.md)
- [Sao lưu và phục hồi (Backup and restore)](operations/BACKUP_RESTORE.md)
- [Ứng phó sự cố (Incident response)](operations/INCIDENT_RESPONSE.md)
- [Khả năng quan sát và chẩn đoán (Observability and diagnostics)](operations/OBSERVABILITY.md)
- [Hướng dẫn người dùng Workspace Chat (Workspace Chat user guide)](user/WORKSPACE_CHAT_USER_GUIDE.md)

Lập trình viên xem thêm [Sổ tay nhà phát triển](runbooks/developer.md) để chạy kiểm thử / audit / phát hành.
