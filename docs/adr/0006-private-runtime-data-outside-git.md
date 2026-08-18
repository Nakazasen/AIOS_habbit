# ADR-0006: Dữ Liệu Runtime Riêng Tư Luôn Nằm Ngoài Git

Status: `ACCEPTED`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before adding a storage path, export or CI artifact

## Bối cảnh (Context)

Mã nguồn và lịch sử Git được theo dõi không phải là nơi thích hợp để lưu trữ tài liệu của chủ sở hữu, trạng thái chat, thông tin xác thực, ảnh chụp màn hình hoặc kết quả đánh giá riêng tư được sinh ra.

## Quyết định (Decision)

Luôn giữ các đường dẫn runtime/riêng tư trong danh sách bỏ qua của Git (.gitignore). Repository chỉ theo dõi mã nguồn, lược đồ (schemas), mẫu (templates), ví dụ tổng hợp (synthetic) và tài liệu đã được làm sạch. Hệ thống CI tuyệt đối không được tải lên nội dung runtime riêng tư hoặc gọi các provider với dữ liệu của chủ sở hữu.

## Hệ quả (Consequences)

- Người vận hành phải tự thực hiện sao lưu/khôi phục dữ liệu cục bộ.
- Các bài kiểm thử bắt buộc sử dụng fixture dữ liệu tổng hợp.
- Một tệp riêng tư vô tình bị đưa vào stage (git add) là một lỗi chặn phát hành nghiêm trọng (release blocker), không phải là cảnh báo vô hại.

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Điều này thiết lập mức cơ sở chống lại nguy cơ vô tình tiết lộ dữ liệu ra ngoài, nhưng không thể bảo vệ tệp nếu chủ sở hữu chủ động chia sẻ ra ngoài repository.

## Di chuyển & Hoàn tác (Migration and Rollback)

Nếu một tệp riêng tư bị đưa vào stage, hãy gỡ bỏ nó khỏi chỉ mục Git và cập nhật quy tắc ignore mà không xóa dữ liệu của chủ sở hữu trừ khi được ủy quyền rõ ràng. Nếu đã vô tình commit, hãy cách ly quyền truy cập và tuân thủ quy trình xử lý sự cố; việc viết lại lịch sử Git bắt buộc cần sự đánh giá của chủ sở hữu.

## Bằng chứng Liên kết (Evidence)

- [Quy tắc Git-ignore](../../.gitignore)
- [Sao lưu và phục hồi (Backup and restore)](../operations/BACKUP_RESTORE.md)
- [Quy trình phản ứng sự cố (Incident response)](../operations/INCIDENT_RESPONSE.md)

