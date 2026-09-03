# Danh sách kiểm đặc tả

## Chất lượng nội dung

- [x] Mọi user story có thể kiểm thử độc lập.
- [x] Có ranh giới rõ với Gate A/B/C và các hạng mục cấm.
- [x] Tách phần có thể lập trình khỏi tiền đề dữ liệu/quyền phải do chủ hệ thống cung cấp.
- [x] Không dùng tuyên bố dự đoán, chẩn đoán hay production khi chưa có evidence.
- [x] Các yêu cầu có mã duy nhất và tiêu chí thành công đo được.
- [x] US1–US11 vẫn được giữ đầy đủ; việc tinh gọn chỉ thay đổi thứ tự thực thi.
- [x] Mỗi đợt có điều kiện vào, kết quả dùng được và điều kiện hoàn tất.
- [x] `tasks.md` chỉ chứa lát cắt đang đủ điều kiện; backlog tương lai không giả làm việc đang triển khai.
- [x] Thiết kế phù hợp máy i5, RAM 16 GB, không GPU và không bắt buộc model nặng.

## Trước khi code

- [x] Chủ repo duyệt thứ tự cổng và định nghĩa quyền chuyên gia/phát hành SOP.
- [ ] Có bằng chứng Gói 1 và Gói 2 ngoài phạm vi code.
- [x] Có sample log đã được phép và owner cho pilot line.
- [x] Có dataset/nhãn/quality owner cho readiness LSU.
- [x] Chủ sở hữu duyệt phương án giao theo đợt nhỏ ngày 04/09/2026.

Ghi chú: thư mục nguồn, mẫu log, SOP, mã lỗi, mapping và các trường dữ liệu LSU đã được chủ sở hữu xác nhận có sẵn cục bộ. Việc ingest thật, kiểm tra NAS nhiều máy và backup/restore vẫn chưa chạy nên Gói 1/Gói 2 chưa được đánh dấu hoàn tất.
