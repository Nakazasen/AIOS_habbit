# Chính Sách Dữ Liệu (Data Policy)

Status: `ACTIVE`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-09-29
Review cadence: Before a new data class, persistent store or external recipient

> **Ghi chú 2026-09-29 (quyết định của chủ sở hữu):** bỏ mọi hạn chế gửi dữ liệu
> tới AI provider. Các điều khoản "tuyệt đối không được gửi tới provider" trước
> đây đã được gỡ. Chủ sở hữu tự chịu trách nhiệm về dữ liệu gửi ra ngoài.

## Ưu Tiên Cục Bộ (Local First)

Mọi dữ liệu mặc định được lưu trữ cục bộ (local). Chủ sở hữu đã cho phép đồng bộ
lên đám mây và gửi tới AI provider khi cần phục vụ công việc (quyết định 2026-09-29,
gỡ bỏ hạn chế cũ). Repository Git chỉ chứa mã nguồn, schema, tài liệu, mẫu (template)
và fixture dữ liệu tổng hợp (synthetic).

## Các Phân Loại Dữ Liệu (Data Classes)

| Phân loại | Mô tả | Xử lý mặc định |
|---|---|---|
| Nguồn thô (Raw source) | Bản ghi chat, email, log, tệp gốc | Không commit; chỉ lưu cục bộ / do chủ sở hữu kiểm soát |
| Trạng thái Workspace Chat | Sổ ghi chép, cuộc trò chuyện, tin nhắn, nguồn đã chọn | JSONL cục bộ dưới `local_cases/workspace_chat/`, được Git bỏ qua |
| Bản ghi bằng chứng (Evidence record) | Metadata / tham chiếu nguồn / tóm tắt / mã băm | Có thể commit nếu không chứa nội dung nhạy cảm |
| Bộ nhớ ứng viên (Candidate memory) | Bộ nhớ chưa qua đánh giá | Chỉ nằm trong workspace trích xuất / cục bộ theo chính sách |
| Bộ nhớ đã xác thực (Validated memory) | Bộ nhớ đã qua đánh giá | Lưu trong kho bộ nhớ (memory vault) theo ranh giới bằng chứng |
| Chunk / Chỉ mục RAG | Metadata chunk/bằng chứng và chỉ mục SQLite cục bộ | Cục bộ, đường dẫn do caller quản lý; không mặc định cloud |
| Hồ sơ vụ việc và thẩm định | Metadata case, role/scope, activity, checklist, review và tham chiếu evidence | `local_cases/workspace_cases.sqlite`; không lưu chat, excerpt, ảnh hoặc log thô; không commit |
| Bài học từ case | Candidate và bản đã promotion có provenance | Kho case cục bộ riêng; candidate không được dùng như sự thật và không tự ghi vào thư viện RAG |
| Dữ liệu dự đoán | Dataset manifest, feature/model version, risk assessment và shadow outcome | Kho dự đoán cục bộ riêng; không commit dataset/model thật; không điều khiển máy |
| Artifact Agent | Proposal, version, approval và đường dẫn output đã làm sạch | Cục bộ, versioned, không ghi đè nguồn; AI không có quyền phê duyệt |
| Gói xuất (Export pack) | Hồ sơ chuyển giao cho các AI khác | Chỉ tạo từ hồ sơ tổng thể (master profile) và kiểm toán trước khi dùng |
| Thông tin bí mật (Secrets) | Token, API key, thông tin xác thực | Tuyệt đối không commit / không đưa vào chẩn đoán hoặc tài liệu |

## Thực Tế Lưu Trữ và Xóa Bỏ (Retention and Deletion Reality)

- Nguồn thô chỉ giữ lại khi cần kiểm toán và bắt buộc phải nằm ngoài Git hoặc trong vùng chỉ dùng cục bộ (local-only).
- Case/review/activity không hard-delete qua UI thông thường; thời hạn lưu và thao tác xóa dữ liệu thật vẫn cần chủ sở hữu phê duyệt riêng.
- Bản ghi bằng chứng được giữ lâu dài nếu không vi phạm quyền riêng tư; bộ nhớ dừng hoạt động (deprecated) phải được ghi rõ lý do trước khi xem xét xóa.
- Dữ liệu runtime / sao lưu của Workspace Chat có thời gian lưu trữ **do chủ sở hữu tự quản lý**. Hiện chưa có bộ lập lịch xóa / lưu trữ tự động; không được tuyên bố các cam kết thời hạn pháp lý khi chưa có cơ chế.
- Chỉ mục RAG chỉ có thể tái tạo (rebuild) khi dữ liệu đầu vào nguồn/chunk tương ứng vẫn còn và chủ sở hữu cho phép sử dụng.

## Ranh Giới Tuyến Gửi Ra Bên Ngoài (External Route Boundary)

Các nhãn `local_only` và `confidential` không còn chặn gửi tới provider
(quyết định của chủ sở hữu ngày 2026-09-29 — gỡ bỏ hạn chế "tuyệt đối không được
gửi tới provider"). Các nhãn này giờ chỉ còn ý nghĩa phân loại nội bộ, không phải
cổng chặn kỹ thuật.

## Bằng Chứng Không Lưu Trữ Dữ Liệu Thô (Evidence Without Raw Storage)

Ưu tiên lưu trữ mã băm (hash), tham chiếu cục bộ, tóm tắt ngắn, tham chiếu dòng và ID artifact. Tránh lưu toàn văn hội thoại / email hoặc các dữ liệu định danh không cần thiết.

## Các Chốt Chặn Liên Quan (Related Controls)

- [Chính sách nguồn (Source policy)](SOURCE_POLICY.md)
- [Mô hình quyền riêng tư (Privacy model)](../docs/PRIVACY_MODEL.md)
- [Sao lưu và phục hồi (Backup and restore)](../docs/operations/BACKUP_RESTORE.md)
- [Khả năng tương thích di chuyển dữ liệu (Data migration compatibility)](../docs/operations/DATA_MIGRATION_COMPATIBILITY.md)
