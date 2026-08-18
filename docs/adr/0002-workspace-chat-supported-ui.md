# ADR-0002: Workspace Chat Là Giao Diện Người Dùng Được Hỗ Trợ Duy Nhất

Status: `ACCEPTED`
Owner role: Project owner / product and architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before adding or retiring a public user route

## Bối cảnh (Context)

Các tuyến công khai cũ của Studio và Case Cockpit đã tạo ra nhiều điểm vào gây mâu thuẫn cho người dùng thông thường. Định hướng sản phẩm hiện tại yêu cầu một luồng duy nhất, đơn giản: chọn nguồn → đặt câu hỏi → kiểm tra trích dẫn (citation).

## Các phương án đã xem xét (Options Considered)

1. Duy trì nhiều giao diện người dùng công khai cùng lúc.
2. Đặt Workspace Chat là giao diện người dùng duy nhất được hỗ trợ, đồng thời giữ lại các dịch vụ dùng chung cũ cho đến khi được kiểm toán tách biệt.
3. Xóa bỏ ngay lập tức toàn bộ các dịch vụ cũ.

## Quyết định (Decision)

Workspace Chat là tuyến người dùng thông thường duy nhất được hỗ trợ. Các trình khởi chạy và tuyến công khai cũ được cho dừng (retired); các dịch vụ dùng chung cũ nằm ngoài quyết định này cho đến khi quá trình kiểm toán phụ thuộc/năng lực cho phép gỡ bỏ an toàn.

## Hệ quả (Consequences)

- Tài liệu hướng dẫn người dùng và các kiểm tra phát hành chỉ nhắm vào Workspace Chat.
- Các module cũ không được phép đưa trở lại vào phần import của giao diện được hỗ trợ.
- Việc xóa các dịch vụ cũ vẫn là một hạng mục backlog được kiểm soát độc lập.

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Một điểm vào duy nhất được hỗ trợ giúp việc kiểm toán thông điệp bảo mật, xử lý lỗi an toàn và cẩm nang vận hành trở nên dễ dàng và chặt chẽ hơn. Quyết định này không tự động cấp quyền định tuyến lên đám mây.

## Di chuyển & Hoàn tác (Migration and Rollback)

Hoàn tác (Rollback) sẽ khôi phục một trình khởi chạy/module cụ thể đã dừng từ lịch sử Git sau khi đánh giá tuyến; không khôi phục tài liệu lỗi thời thành sự thật hiện tại.

## Bằng chứng Liên kết (Evidence)

- [Roadmap canonical](../../ROADMAP.md)
- [Bản kê dừng hoạt động (Retirement manifest)](../legacy/RETIREMENT_MANIFEST.md)
- [Hợp đồng giao diện runtime (Runtime interfaces)](../contracts/RUNTIME_INTERFACES.md)

