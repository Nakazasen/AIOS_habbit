# ADR-0001: Quyền Sở Hữu Hệ Thống Tệp Ưu Tiên Cục Bộ (Local-first Filesystem Ownership)

Status: `ACCEPTED`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before storage, synchronization or external-processing changes

## Bối cảnh (Context)

AIOS WorkLens lưu trữ tri thức công việc và có thể xử lý các tài liệu nhạy cảm của chủ sở hữu. Hiến pháp dự án yêu cầu hành vi ưu tiên cục bộ (local-first) và khả năng chuyển đổi dữ liệu dài hạn.

## Động lực thúc đẩy quyết định (Decision Drivers)

Tính bảo mật, quyền kiểm soát của chủ sở hữu, tính hữu dụng khi ngoại tuyến, khả năng kiểm toán và việc tránh bị khóa phụ thuộc vào nhà cung cấp AI (vendor lock-in) quan trọng hơn sự tiện lợi của việc đồng bộ hóa tập trung.

## Các phương án đã xem xét (Options Considered)

1. Không gian làm việc do đám mây quản lý ưu tiên cloud (Cloud-first managed workspace).
2. Tệp ưu tiên cục bộ (Local-first) kết hợp các lệnh gọi ra ngoài tùy chọn được ủy quyền rõ ràng.
3. Bộ lưu trữ do Router/Provider sở hữu.

## Quyết định (Decision)

Sử dụng quyền sở hữu hệ thống tệp ưu tiên cục bộ. Trạng thái của Workspace Chat được lưu trữ trong thư mục `local_cases/` (được Git bỏ qua); các tệp bằng chứng/bộ nhớ và artifact runtime khác cũng bị loại trừ khỏi Git. Việc định tuyến lên cloud, khi được sử dụng, là một ranh giới tùy chọn minh bạch.

## Hệ quả (Consequences)

- Sao lưu, khôi phục và chuyển đổi thiết bị là trách nhiệm vận hành của chủ sở hữu.
- Đồng bộ hóa chia sẻ đa thiết bị hiện chưa phải là cam kết sản phẩm.
- Tài liệu và gói xuất dữ liệu tuyệt đối tránh nhúng dữ liệu riêng tư.

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Quyết định này giảm thiểu nguy cơ tiết lộ dữ liệu ra bên ngoài theo mặc định, nhưng không thay thế mã hóa ổ đĩa, bảo mật tài khoản hệ điều hành hoặc quy trình sao lưu do người dùng tự quản lý.

## Di chuyển & Hoàn tác (Migration and Rollback)

Không cần di chuyển dữ liệu cho quyết định này. Bất kỳ phương thức lưu trữ đồng bộ nào trong tương lai đều bắt buộc phải có ADR mới, đánh giá quyền riêng tư, cập nhật mô hình mối đe dọa và kế hoạch di chuyển dữ liệu.

## Bằng chứng Liên kết (Evidence)

- [Hiến pháp (Constitution)](../../CONSTITUTION.md)
- [Chính sách dữ liệu (Data policy)](../../00_governance/DATA_POLICY.md)
- [Đánh giá tác động quyền riêng tư (Privacy impact assessment)](../security/PRIVACY_IMPACT_ASSESSMENT.md)

