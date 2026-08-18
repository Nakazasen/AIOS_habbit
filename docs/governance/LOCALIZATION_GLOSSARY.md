# Bảng Thuật Ngữ Địa Phương Hóa (Localization Glossary)

Status: `ACTIVE`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before new supported UI terminology or provider-facing copy

## Chính Sách (Policy)

Giao diện người dùng thông thường được hỗ trợ mặc định ưu tiên Tiếng Việt (Vietnamese-first). Các hằng số kỹ thuật thiết yếu có thể giữ nguyên Tiếng Anh khi chúng được giải thích ngay lập tức bằng Tiếng Việt. Traceback thô và chi tiết lỗi nội bộ tuyệt đối không được hiển thị cho chủ sở hữu.

| Thuật ngữ | Tiếng Việt chuẩn hóa | Ghi chú sử dụng |
|---|---|---|
| Workspace Chat | Workspace Chat | Tên sản phẩm; giải thích là "Không gian hỏi đáp" trong văn bản hỗ trợ khi cần |
| source | nguồn | Dùng "nguồn dữ liệu" ở những nơi cần làm rõ ngữ nghĩa |
| evidence | bằng chứng | Phân biệt rõ ràng với nguồn thô (raw source) |
| privacy label | nhãn bảo mật | Hiển thị ý nghĩa trước khi đưa ra quyết định gửi lên đám mây |
| local_only | chỉ dùng cục bộ | Tuyệt đối không gửi ra bên ngoài |
| confidential | bảo mật | Tuyệt đối không gửi ra bên ngoài |
| machine_only | cần xác nhận chủ sở hữu | Bắt buộc phải có xác nhận đồng ý cho tuyến gửi ra ngoài |
| cloud_safe | cho phép gửi AI cloud | Chỉ áp dụng sau khi tuyến đáp ứng đủ điều kiện chính sách |
| consent | xác nhận đồng ý | Ràng buộc với tập nguồn / đích đến / mục đích |
| insufficient evidence | chưa đủ bằng chứng | Ưu tiên dùng thay vì tạo ra sự chắc chắn bịa đặt |
| fallback | phương án dự phòng | Giải thích hiệu ứng đối với người dùng, không nêu cơ chế nội bộ |

## Quy Tắc Đánh Giá (Review Rule)

Văn bản giao diện người dùng mới bắt buộc phải sử dụng nhất quán các thuật ngữ này, đồng thời bao gồm các trạng thái lỗi, trạng thái trống/đang tải và trạng thái ngoại tuyến dễ tiếp cận theo bản ghi nghiệm thu UX.

