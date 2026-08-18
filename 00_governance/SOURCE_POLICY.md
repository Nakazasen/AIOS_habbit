# Chính Sách Nguồn Dữ Liệu (Source Policy)

## Mục Đích (Purpose)

Quy định những loại nguồn dữ liệu nào được phép dùng để trích xuất bộ nhớ (memory) và quy trình xử lý tương ứng.

## Các Loại Nguồn Được Phép (Allowed Source Types)

- Ghi chú Markdown.
- Lộ trình phát triển (Roadmaps).
- Tài liệu kiến trúc (Architecture docs).
- Báo cáo kiểm toán (Audit reports).
- Lịch sử commit.
- Đặc tả dự án (Project specifications).
- Thư viện prompt.
- Bản ghi chat được người dùng phê duyệt.
- Phỏng vấn người dùng.

## Quy Tắc Xử Lý Nguồn (Source Processing Rule)

```text
Nguồn (Source) -> Kiểm kê nguồn -> Bản ghi bằng chứng -> Bộ nhớ ứng viên -> Xác thực -> Kho bộ nhớ (Memory Vault)
```

Tuyệt đối không được đi tắt trực tiếp:

```text
Nguồn (Source) -> Kho bộ nhớ (Memory Vault)
```

## Quy Tắc Chat Thô (Raw Chat Rule)

Bản ghi chép chat (chat transcript) tuyệt đối không được lưu trữ trực tiếp dưới dạng bộ nhớ. Chúng chỉ được dùng để trích xuất:

- Mẫu hành vi (Behavior pattern).
- Mẫu quy trình (Workflow pattern).
- Mẫu quyết định (Decision pattern).
- Tri thức dự án (Project knowledge).
- Bài học kinh nghiệm (Lessons learned).

## Tiêu Chí Loại Trừ (Exclusion Criteria)

Bắt buộc loại trừ hoặc chỉ giữ ở chế độ cục bộ (local-only) nếu nguồn chứa:

- Thông tin bí mật (Secrets).
- Thông tin xác thực (Credentials).
- Dữ liệu cá nhân riêng tư không liên quan.
- Nội dung không được phép xử lý.
- Dữ liệu thô quá dài chưa được phân loại.

## Yêu Cầu Đối Với Bản Ghi Bằng Chứng (Evidence Requirements)

Mỗi bản ghi bằng chứng (evidence record) bắt buộc phải có:

- Loại nguồn (Source type).
- Vị trí nguồn hoặc tham chiếu.
- Mã băm (Hash) nếu có thể.
- Tóm tắt nội dung (Summary).
- Ranh giới áp dụng (Boundary).
- Trạng thái cấp phép (Permission status).
- Trạng thái thời gian lưu trữ (Retention status).

## Quy Tắc Khám Phá (Discovery Rule)

Không được tự giả định danh sách dự án / nguồn là đã đầy đủ. Giai đoạn 1 bắt buộc phải có báo cáo kiểm kê và báo cáo loại trừ.

