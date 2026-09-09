# Danh sách kiểm tra chất lượng đặc tả: Phỏng vấn chuyên gia

**Mục đích**: xác nhận đặc tả sửa ngày 2026-09-09 đủ rõ để lập task sửa
**Tính năng**: [spec.md](../spec.md)

## Chất lượng nội dung

- [x] Tập trung vào nhu cầu và kết quả của người dùng.
- [x] Viết bằng tiếng Việt dễ hiểu cho người không chuyên.
- [x] Không phụ thuộc vào ngôn ngữ lập trình, framework hoặc tên kho dữ liệu cụ thể.
- [x] Không còn phần bắt buộc nào bỏ trống.

## Tính đầy đủ của yêu cầu

- [x] Không còn dấu cần làm rõ.
- [x] Mỗi yêu cầu có thể kiểm thử và không mâu thuẫn với mô hình nhóm tin cậy.
- [x] Tiêu chí thành công đo được và hướng tới hành vi người dùng.
- [x] Có kịch bản cá nhân, dùng chung, âm thanh, trách nhiệm và khôi phục.
- [x] Có trường hợp biên cho ghi đồng thời, tên trùng, thư mục lỗi và nội dung đổi phiên bản.
- [x] Phạm vi và phần không làm được nêu rõ.
- [x] Không hứa xác thực danh tính hoặc phân quyền khi sản phẩm chưa có hệ tài khoản chung.

## Không thiết kế thừa

- [x] Không yêu cầu đăng nhập, vai trò, quản trị viên, SSO hoặc quyền theo công đoạn.
- [x] Không yêu cầu một máy ghi cố định hoặc cấu hình quyền Windows/NAS.
- [x] Không thêm máy chủ trung tâm, DB phân tán, ứng dụng mới hoặc hệ thiết kế giao diện mới.
- [x] Gap chỉ là gợi ý; không chặn phỏng vấn trực tiếp.
- [x] Giới hạn phiên, mã kiểm tra, khóa ghi và kiểm tra toàn vẹn nằm bên trong hoặc phần kỹ thuật thu gọn.
- [x] Fine-tune không còn là cổng sản phẩm của Goal 010.

## UX/UI

- [x] Luồng chính có bốn chặng và một hành động chính mỗi chặng.
- [x] Form quyết định chỉ yêu cầu thông tin người dùng hiểu và hệ thống không thể tự suy ra.
- [x] Fixture, mã băm, mã gói, trạng thái nội bộ và đường dẫn hệ thống bị loại khỏi bề mặt chính.
- [x] Lỗi phải nói điều gì xảy ra và bước tiếp theo.
- [x] Có lượt đi bộ với người không chuyên trước khi đóng Goal.

## Sẵn sàng lập kế hoạch

- [x] ADR, đặc tả, kế hoạch, mô hình dữ liệu và hai hợp đồng đã thống nhất.
- [x] Task sửa T083–T109 có thứ tự phụ thuộc và đường dẫn cụ thể.
- [ ] Việc triển khai và kiểm chứng T083–T109 chưa thực hiện; Goal phải giữ `REOPENED_FOR_SIMPLIFICATION`.

## Ghi chú

Checklist xác nhận tài liệu sẵn sàng cho pha thực thi, không xác nhận mã hiện tại đáp ứng đặc tả mới.
