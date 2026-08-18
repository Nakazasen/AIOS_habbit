# Luồng Dữ Liệu (Data Flow)

## Luồng Chính (Main Flow)

```text
1. Khám phá nguồn dữ liệu (Source discovery)
2. Kiểm kê nguồn dữ liệu (Source inventory)
3. Tạo bản ghi bằng chứng (Evidence record creation)
4. Trích xuất ứng viên (Candidate extraction)
5. Đánh giá con người / AI (Human/AI review)
6. Thăng cấp bộ nhớ đã xác thực (Validated memory promotion)
7. Cập nhật hồ sơ tổng thể (Master profile update)
8. Tạo gói xuất cho AI (AI export pack generation)
9. Đánh giá / cho dừng định kỳ (Periodic review/deprecation)
```

## Luồng Không Lưu Chat Thô (No-Raw-Chat Flow)

```text
Bản ghi chép Chat (Chat transcript)
  -> Nhận diện mẫu hữu ích
  -> Tạo bản tóm tắt bằng chứng
  -> Trích xuất bộ nhớ ứng viên
  -> Hủy bỏ hoặc chỉ giữ bản ghi thô ở chế độ cục bộ (local-only)
```

## Luồng Xử Lý Xung Đột (Conflict Flow)

```text
Bằng chứng mới mâu thuẫn với bộ nhớ hiện có
  -> Đánh dấu bộ nhớ bị xung đột (conflicted)
  -> Tạo mục ghi nhận xung đột
  -> Đánh giá độ mạnh của bằng chứng
  -> Cập nhật / cho dừng / phân tách bộ nhớ
```

