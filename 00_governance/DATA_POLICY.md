# Chính Sách Dữ Liệu (Data Policy)

Status: `ACTIVE`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before a new data class, persistent store or external recipient

## Ưu Tiên Cục Bộ (Local First)

Mọi dữ liệu mặc định được lưu trữ cục bộ (local). Tuyệt đối không đồng bộ lên đám mây hoặc gửi tới provider nếu chưa có tuyến chính sách và xác nhận đồng ý phù hợp từ chủ sở hữu. Repository Git chỉ chứa mã nguồn, schema, tài liệu, mẫu (template) và fixture dữ liệu tổng hợp (synthetic).

## Các Phân Loại Dữ Liệu (Data Classes)

| Phân loại | Mô tả | Xử lý mặc định |
|---|---|---|
| Nguồn thô (Raw source) | Bản ghi chat, email, log, tệp gốc | Không commit; chỉ lưu cục bộ / do chủ sở hữu kiểm soát |
| Trạng thái Workspace Chat | Sổ ghi chép, cuộc trò chuyện, tin nhắn, nguồn đã chọn | JSONL cục bộ dưới `local_cases/workspace_chat/`, được Git bỏ qua |
| Bản ghi bằng chứng (Evidence record) | Metadata / tham chiếu nguồn / tóm tắt / mã băm | Có thể commit nếu không chứa nội dung nhạy cảm |
| Bộ nhớ ứng viên (Candidate memory) | Bộ nhớ chưa qua đánh giá | Chỉ nằm trong workspace trích xuất / cục bộ theo chính sách |
| Bộ nhớ đã xác thực (Validated memory) | Bộ nhớ đã qua đánh giá | Lưu trong kho bộ nhớ (memory vault) theo ranh giới bằng chứng |
| Chunk / Chỉ mục RAG | Metadata chunk/bằng chứng và chỉ mục SQLite cục bộ | Cục bộ, đường dẫn do caller quản lý; không mặc định cloud |
| Gói xuất (Export pack) | Hồ sơ chuyển giao cho các AI khác | Chỉ tạo từ hồ sơ tổng thể (master profile) và kiểm toán trước khi dùng |
| Thông tin bí mật (Secrets) | Token, API key, thông tin xác thực | Tuyệt đối không commit / không đưa vào chẩn đoán hoặc tài liệu |

## Thực Tế Lưu Trữ và Xóa Bỏ (Retention and Deletion Reality)

- Nguồn thô chỉ giữ lại khi cần kiểm toán và bắt buộc phải nằm ngoài Git hoặc trong vùng chỉ dùng cục bộ (local-only).
- Bản ghi bằng chứng được giữ lâu dài nếu không vi phạm quyền riêng tư; bộ nhớ dừng hoạt động (deprecated) phải được ghi rõ lý do trước khi xem xét xóa.
- Dữ liệu runtime / sao lưu của Workspace Chat có thời gian lưu trữ **do chủ sở hữu tự quản lý**. Hiện chưa có bộ lập lịch xóa / lưu trữ tự động; không được tuyên bố các cam kết thời hạn pháp lý khi chưa có cơ chế.
- Chỉ mục RAG chỉ có thể tái tạo (rebuild) khi dữ liệu đầu vào nguồn/chunk tương ứng vẫn còn và chủ sở hữu cho phép sử dụng.

## Ranh Giới Tuyến Gửi Ra Bên Ngoài (External Route Boundary)

Các nhãn `local_only` và `confidential` tuyệt đối không được gửi tới provider. Các tuyến gửi ra bên ngoài khác bắt buộc phải sử dụng các chốt chặn kiểm soát quyền riêng tư / sự đồng ý đã được kiểm chứng; độ bao phủ hiện tại và lỗ hổng P0 được mô tả trong [Đánh giá tác động quyền riêng tư (Privacy Impact Assessment)](../docs/security/PRIVACY_IMPACT_ASSESSMENT.md). Không sử dụng router/provider làm thẩm quyền quyết định sự đồng ý.

## Bằng Chứng Không Lưu Trữ Dữ Liệu Thô (Evidence Without Raw Storage)

Ưu tiên lưu trữ mã băm (hash), tham chiếu cục bộ, tóm tắt ngắn, tham chiếu dòng và ID artifact. Tránh lưu toàn văn hội thoại / email hoặc các dữ liệu định danh không cần thiết.

## Các Chốt Chặn Liên Quan (Related Controls)

- [Chính sách nguồn (Source policy)](SOURCE_POLICY.md)
- [Mô hình quyền riêng tư (Privacy model)](../docs/PRIVACY_MODEL.md)
- [Sao lưu và phục hồi (Backup and restore)](../docs/operations/BACKUP_RESTORE.md)
- [Khả năng tương thích di chuyển dữ liệu (Data migration compatibility)](../docs/operations/DATA_MIGRATION_COMPATIBILITY.md)
