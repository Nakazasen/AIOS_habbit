# ADR-0007: Ranh giới vòng hồ sơ có bằng chứng

Status: `ACCEPTED`
Vai trò chủ sở hữu: Chủ sở hữu dự án / người duyệt kiến trúc
Xem xét lần cuối: 2026-08-30
Chu kỳ xem xét: Trước khi thêm kho, loại hồ sơ hoặc quyền Agent mới

## Bối cảnh

Workspace Chat đã lưu được siêu dữ liệu hồ sơ và tham chiếu bằng chứng, nhưng chưa có chuyển đổi lược đồ theo phiên bản, màn hình mở lại hồ sơ, quyền theo công đoạn hoặc vòng thẩm định. Dữ liệu tài liệu, nhật ký dây chuyền và dự đoán có vòng đời khác nhau; gộp chúng vào một SQLite sẽ làm tăng rủi ro quyền riêng tư, chuyển đổi lược đồ và truy vết.

## Các phương án đã xem xét

1. Gộp tài liệu, log, case và dự đoán vào một kho SQLite.
2. Giữ bốn kho riêng, liên kết bằng ID, phiên bản và digest; Workspace Chat là UI được hỗ trợ duy nhất.
3. Khôi phục Case Cockpit làm UI thứ hai.

## Quyết định

Chọn phương án 2. `library.sqlite`, `line_events.sqlite`, `workspace_cases.sqlite` và `production_prediction.sqlite` tách biệt. Hồ sơ chỉ giữ siêu dữ liệu, vị trí đã làm sạch và mã kiểm tra. Ba loại hồ sơ là `investigation`, `prediction`, `agent_work`. Agent tạo đầu ra theo hồ sơ và Agent kỹ thuật phần mềm là hai miền quyền riêng; cả hai chỉ tạo đề xuất hoặc bản nháp cho đến khi con người có vai trò/phạm vi hợp lệ duyệt.

Người được giao việc mặc định có cả quyền điều tra và chuyên gia trong đúng phạm vi công đoạn. Chỉ cấu hình một chuyên gia theo dõi riêng trong trường hợp đặc biệt. Vai trò `admin` không có quyền bao trùm ngầm; mọi khả năng vẫn được liệt kê và kiểm tra phạm vi.

Người thao tác của Workspace Chat lấy từ ngữ cảnh do ứng dụng kiểm soát, không lấy mã tự khai từ biểu mẫu hoặc nội dung do AI tạo. Bản cục bộ một người dùng dùng `local_admin` với quyền tường minh cho phạm vi `general`; mọi thao tác đổi trạng thái hoặc giao việc đều phải bắt đầu từ nút do con người bấm. Khi mở nhiều người dùng phải thay bằng ánh xạ tài khoản hoặc hệ điều hành đã được chủ sở hữu duyệt; chưa có ánh xạ này thì phải từ chối chạy nhiều người dùng.

## Hệ quả

- Lược đồ hồ sơ phải chuyển đổi theo phiên bản và sao lưu/khôi phục trước khi thêm bảng.
- Mọi chuyển trạng thái, gắn bằng chứng, giao việc và thẩm định đi qua lớp dịch vụ, dùng phiên bản chống ghi đè và lịch sử chỉ ghi nối có chuỗi mã kiểm tra.
- Liên kết dự đoán sang hồ sơ dùng hộp thư đi, chống ghi lặp và đối soát; không dùng giao dịch phân tán giữa hai SQLite.
- Workspace Chat không import `studio` hoặc `case_cockpit`.

## Tác động bảo mật và quyền riêng tư

Kho hồ sơ nằm dưới `local_cases/`, bị Git bỏ qua và không lưu câu hỏi thô, câu trả lời thô, đoạn trích thô, ảnh hoặc nhật ký thô. Vị trí tuyệt đối của hệ thống phải được thay bằng định danh đã làm sạch. AI chỉ tạo nháp, không có vai trò phê duyệt và không được mượn danh `local_admin`.

## Di chuyển và hoàn tác

Trong cùng khóa ghi trước mỗi lần chuyển đổi lược đồ, hệ thống tạo bản sao lưu trực tuyến SQLite và chạy `quick_check`. Nếu chuyển đổi hoặc kiểm tra sau chuyển đổi lỗi, hệ thống đóng kết nối, phục hồi bản chụp và trả mã lỗi an toàn. Cổng sau không được mở khi chuỗi chuyển đổi, mã kiểm tra hoặc phiên bản không nhất quán.

## Bằng chứng liên kết

- [Đặc tả vòng hồ sơ](../../specs/008-evidence-case-loop/spec.md)
- [Hợp đồng vòng hồ sơ](../../specs/008-evidence-case-loop/contracts/workspace-evidence-loop.md)
- [ADR-0002](0002-workspace-chat-supported-ui.md)
- [ADR-0006](0006-private-runtime-data-outside-git.md)
