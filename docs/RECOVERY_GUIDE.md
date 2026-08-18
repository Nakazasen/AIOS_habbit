# Hướng Dẫn Phục Hồi (Recovery Guide)

Status: `ACTIVE`
Owner role: Operator / local data owner
Last reviewed: 2026-07-25
Review cadence: Before release and after persistent-store changes

Sử dụng tài liệu [Sao lưu và Phục hồi (Backup and Restore)](operations/BACKUP_RESTORE.md) làm quy trình phục hồi canonical và [Ứng phó sự cố (Incident Response)](operations/INCIDENT_RESPONSE.md) đối với các sự cố nghi ngờ về quyền riêng tư, lộ thông tin xác thực, mất dữ liệu hoặc lộ dữ liệu ra công cộng.

Nếu dữ liệu riêng tư bị staged vào Git, hãy gỡ bỏ nó khỏi theo dõi Git mà không xóa bản sao cục bộ của chủ sở hữu trừ khi có yêu cầu rõ ràng. Tuyệt đối không tuyên bố bản sao lưu có thể phục hồi được cho đến khi một đợt diễn tập phục hồi tổng hợp được hoàn thành thành công.
