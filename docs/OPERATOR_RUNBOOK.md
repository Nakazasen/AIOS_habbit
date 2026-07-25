# Operator Runbook

Status: `ACTIVE`
Owner role: Operator / local data owner
Last reviewed: 2026-07-25
Review cadence: Before release and after an operational workflow change

## Luồng dùng hằng ngày

1. Mở `RUN_AIOS_WORKSPACE_CHAT.bat`.
2. Tạo hoặc chọn workspace phù hợp.
3. Tạo hoặc chọn knowledge notebook; thêm nguồn cục bộ khi cần.
4. Kiểm tra nhãn privacy trước khi hỏi về nguồn.
5. Đặt câu hỏi tự nhiên trong Workspace Chat; dùng source context/citations để
   kiểm tra câu trả lời.
6. Khi thông tin chưa đủ, bổ sung nguồn hoặc giữ kết quả ở trạng thái cần review;
   không biến claim chưa có evidence thành kết luận chắc chắn.

## An toàn vận hành

- Không đưa raw local documents, secrets, runtime JSONL/SQLite, screenshots hoặc
  diagnostic bundle vào Git/cloud/public issue.
- External AI provider là optional; khi có lỗi provider, ưu tiên local-only flow.
- Không tự xóa hoặc ghi đè `local_cases/` để "sửa nhanh" khi chưa có backup.

## Runbook liên quan

- [Troubleshooting](operations/TROUBLESHOOTING.md)
- [Backup and restore](operations/BACKUP_RESTORE.md)
- [Incident response](operations/INCIDENT_RESPONSE.md)
- [Observability and diagnostics](operations/OBSERVABILITY.md)
- [Workspace Chat user guide](user/WORKSPACE_CHAT_USER_GUIDE.md)

Developer xem [developer.md](runbooks/developer.md) để chạy test/audit/release.
