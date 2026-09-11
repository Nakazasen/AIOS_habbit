# Checklist chất lượng đặc tả: Trợ lý thực thi công việc cho kỹ sư

**Ngày cập nhật**: 2026-09-11
**Đặc tả**: [spec.md](../spec.md)

## Chất lượng nội dung

- [x] Tập trung vào giá trị người dùng và ranh giới sản phẩm.
- [x] Các chi tiết kỹ thuật nằm ở kế hoạch, không lẫn vào tiêu chí thành công.
- [x] Không còn placeholder hoặc câu cần làm rõ.
- [x] Tài liệu dùng tiếng Việt dễ hiểu.

## Tính đầy đủ

- [x] Yêu cầu có thể kiểm thử và không mơ hồ.
- [x] Tiêu chí thành công đo được và hướng đến kết quả.
- [x] Hành trình chính, trường hợp biên, giả định và phụ thuộc đã nêu.
- [x] Phạm vi bản đầu và phi mục tiêu được khóa.
- [x] Permission, privacy, rollback và bằng chứng có tiêu chí bắt buộc.
- [x] Báo cáo lỗi, biểu đồ và rà soát thiết kế công đoạn có quy tắc nguồn rõ ràng.
- [x] Người dùng không chuyên không bị buộc duyệt `diff`, terminal hoặc từng tool call.

## Sẵn sàng lập kế hoạch

- [x] Mỗi hành trình có kiểm thử độc lập.
- [x] G1 kiểm chứng đủ đọc–sửa–test–hoàn tác và có điều kiện dừng sớm rõ ràng.
- [x] Không tuyên bố parity hoặc production trước benchmark và clean-machine E2E.
- [x] MVP dùng lại module hiện có, không dựng extension, scheduler hoặc nền tảng đa Agent mới.
