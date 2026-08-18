# Chính sách Di chuyển (Migration Policy)

- Không sao chép mã nguồn một cách mù quáng.
- Chỉ thu hoạch/kế thừa mã nguồn sau khi đã thực hiện kiểm tra đánh giá ở chế độ chỉ đọc (read-only audit).
- Mọi tính năng được di chuyển bắt buộc phải ghi rõ repository nguồn gốc, lý do, bài kiểm thử, module sở hữu và quy trình hoàn tác (rollback path).
- Mọi tính năng được di chuyển bắt buộc phải phục vụ vòng lặp: Sự việc (Case) → Bằng chứng (Evidence) → Bản đồ (Map) → Hành động (Action) → Bài học (Learning).
- Các tính năng không phục vụ vòng lặp công việc hàng ngày phải TẠM DỪNG (PAUSED).
- Kho mã nguồn công khai (public repo) chỉ chứa mã nguồn, tài liệu, lược đồ dữ liệu và các ví dụ dữ liệu tổng hợp (synthetic).
- Các tệp dữ liệu runtime, hồ sơ sự vụ cục bộ, tài liệu văn phòng thô, ảnh chụp màn hình, log, token và gói trích xuất tuyệt đối nằm ngoài Git.

