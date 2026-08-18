# Chính Sách Bảo Trì và Dừng Hoạt Động (Maintenance and Deprecation Policy)

Status: `PROPOSED`
Owner role: Project owner / maintainer
Last reviewed: 2026-08-16
Review cadence: Each release candidate and retirement decision

## Bảo Trì (Maintenance)

Ưu tiên bảo trì Workspace Chat được hỗ trợ, ranh giới quyền riêng tư, an toàn dữ liệu cục bộ và các cổng chất lượng trước tiên. Các tính năng đang lên kế hoạch không đương nhiên trở thành cam kết hỗ trợ chỉ vì tài liệu thiết kế tồn tại.

## Vòng Đời Dừng Hoạt Động (Deprecation Lifecycle)

1. Ghi lại lý do căn bản, các module/dữ liệu bị ảnh hưởng và giải pháp thay thế trong một ADR / Gate Card.
2. Đánh dấu tài liệu / tuyến là đã deprecated (dừng hoạt động) trong khi vẫn bảo tồn bằng chứng lịch sử.
3. Chỉ loại bỏ kỳ vọng về trình khởi chạy / import được hỗ trợ sau khi đã xem xét tính tương thích.
4. Giữ lại các dịch vụ dùng chung cho đến khi kiểm toán năng lực / phụ thuộc phê duyệt việc gỡ bỏ.
5. Ghi nhận kiểm chứng, hoàn tác và rủi ro tồn dư trong roadmap / changelog / handover.

## Các Ví Dụ Hiện Tại (Current Examples)

Các tuyến công khai của Studio và Case Cockpit đã được dừng (retired) khỏi bề mặt giao diện người dùng được hỗ trợ. Việc loại bỏ tệp Case Cockpit hiện đang chờ kiểm chứng toàn bộ bộ test và commit cuối cùng; các dịch vụ dùng chung của Case Cockpit không được tự động xóa bỏ.

## Cửa Sổ Hỗ Trợ (Support Window)

Thời hạn hỗ trợ bản phát hành và ngày kết thúc vòng đời (EOL) ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu).

