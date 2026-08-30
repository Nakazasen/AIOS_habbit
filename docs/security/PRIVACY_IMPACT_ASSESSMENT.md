# Đánh Giá Tác Động Quyền Riêng Tư (Privacy Impact Assessment)

Status: `PARTIAL`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before any new external recipient, data class or cloud route

## Mục Đích và Giới Hạn (Purpose and Limits)

Đây là bản đánh giá kỹ thuật về quyền riêng tư (engineering privacy assessment), không phải lời khuyên pháp lý hay chứng nhận tuân thủ. Nó ghi nhận hành vi hiện tại của hệ thống và các quyết định còn thiếu của chủ sở hữu.

## Kiểm Kê Xử Lý Dữ Liệu (Processing Inventory)

| Phân loại dữ liệu | Xử lý cục bộ | Bên nhận bên ngoài | Điều kiện | Thực tế lưu trữ |
|---|---|---|---|---|
| Sổ ghi chép, tin nhắn và nguồn Workspace Chat | JSONL dưới `local_cases/workspace_chat/` (được gitignore) | Mặc định không có | Dùng cục bộ | Dữ liệu hệ thống tệp do chủ sở hữu tự quản lý; chưa có bộ máy xóa/lưu tự động được kiểm chứng |
| Chunk / Chỉ mục RAG v2 | Đường dẫn SQLite cục bộ do caller chọn | Mặc định không có | Truy xuất cục bộ | Có thể tái tạo từ đầu vào nguồn/chunk có sẵn nơi caller lưu giữ |
| Hồ sơ vụ việc, review và bài học | SQLite dưới `local_cases/` | Mặc định không có | Chỉ metadata, role/scope, digest và locator đã làm sạch | Không lưu chat/excerpt/raw log; retention tự động chưa được kiểm chứng |
| Dữ liệu/model dự đoán và shadow outcome | SQLite/artifact cục bộ do chủ sở hữu quản lý | Mặc định không có | Chỉ mở sau Data Gate và phê duyệt shadow | Không có connector điều khiển nhà máy; dataset/model thật không vào Git |
| Artifact Agent | Proposal, version, approval và output cục bộ | Mặc định không có | AI chỉ tạo nháp; con người có role/scope duyệt | Không ghi đè nguồn; output root phải allowlist |
| Văn bản nguồn `local_only` / `confidential` | Chỉ dùng cục bộ | Bị chặn | Gateway từ chối cứng (hard deny) | Do chủ sở hữu tự quản lý |
| Văn bản nguồn `unknown` / `machine_only` | Mặc định cục bộ | Provider tùy chọn | Gateway yêu cầu sự đồng ý ràng buộc với toàn bộ tập nguồn, đích đến và mục đích; văn bản nhạy cảm gửi ra ngoài vẫn bị làm sạch | Do chủ sở hữu tự quản lý; sự đồng ý là ủy quyền yêu cầu, không phải chính sách lưu trữ |
| Văn bản nguồn `cloud_safe` / `public` | Cục bộ hoặc provider tùy chọn | Provider đã cấu hình | Phê duyệt từ Gateway + luồng yêu cầu tường minh thông thường | Điều khoản / lưu trữ của provider là bên ngoài và bắt buộc phải được chủ sở hữu xem xét |
| API key | Biến môi trường tiến trình cho tích hợp router | Chỉ dùng xác thực provider | Tuyến live tường minh | Không lưu trữ theo hợp đồng ứng dụng; tuyệt đối không commit |
| Log / Chẩn đoán | Cục bộ / do người vận hành kiểm soát | Mặc định không có | Chỉ thu thập bản đã làm sạch | Chưa có chính sách lưu trữ tự động chính thức |

## Độ Bao Phủ Chính Sách Theo Tuyến (Route-specific Policy Coverage)

Hàm `BrainGateway.preflight_check()` triển khai chính sách đã được kiểm chứng cho cả luồng mock router và luồng provider Workspace Chat thực tế:

1. router bị tắt hoặc không có nguồn → từ chối;
2. `local_only` / `confidential` → từ chối cứng tuyến gửi ra bên ngoài;
3. `unknown` / `machine_only` → từ chối cho đến khi có `OwnerConsent` hợp lệ khớp với mã băm toàn bộ tập nguồn, đích đến và mục đích;
4. bằng chứng gửi ra ngoài được truy xuất phải khớp với một nguồn trong ảnh chụp nhanh toàn bộ nguồn đang kích hoạt;
5. payload được phê duyệt phải được làm sạch; tiêu đề/văn bản nguồn nhạy cảm bị ẩn đi và metadata nằm trong allowlist/dạng mờ đục.

Tuyến thực tế sử dụng đích đến `workspace_chat_external_router` và chỉ truyền `SanitizedRouterPayload` cho router adapter. Adapter tự xây dựng các thông điệp gửi tới provider, tuyệt đối không dùng prompt thô do caller cung cấp. Lựa chọn chia sẻ bên ngoài phía người dùng sẽ ghi nhãn `cloud_safe`; các bản ghi `machine_only` và `cloud_allowed` cũ vẫn ở trạng thái không thể gửi cho đến khi chủ sở hữu phân loại lại tường minh. Nakazasen Router vẫn là phụ thuộc định tuyến provider và không bao giờ là thẩm quyền quyết định sự đồng ý.

## Quyết Định Bắt Buộc Của Chủ Sở Hữu (Owner Decisions Required)

| Quyết định | Trạng thái |
|---|---|
| Cơ sở pháp lý và nghĩa vụ quyền riêng tư theo khu vực tài phán cụ thể | `OWNER_DECISION_REQUIRED` |
| Danh sách provider bên ngoài và các điều khoản / bên xử lý phụ của họ | `OWNER_DECISION_REQUIRED` |
| Thời hạn lưu trữ / lịch trình xóa dữ liệu | `OWNER_DECISION_REQUIRED` |
| Đầu mối liên hệ công bố bảo mật và truyền thông sự cố | `OWNER_DECISION_REQUIRED` |
| Quyết định có kích hoạt định tuyến ra bên ngoài cho người dùng thông thường hay không | `OWNER_DECISION_REQUIRED` |

## Kỳ Vọng Kiểm Thử Quyền Riêng Tư (Privacy Test Expectations)

- Các bài kiểm thử bao phủ: từ chối cứng (hard deny), từ chối mặc định (default deny), sự đồng ý ràng buộc tập nguồn và làm sạch dữ liệu.
- CI chỉ sử dụng fixture dữ liệu tổng hợp và không có thông tin xác thực provider.
- Live smoke với provider là tùy chọn opt-in và sử dụng prompt generic không chứa ngữ cảnh dự án / nguồn. Bằng chứng chỉ ghi trạng thái / model, tuyệt đối không ghi API key hoặc yêu cầu thô.

## Các Chốt Chặn Liên Quan (Related Controls)

- [Chính sách dữ liệu (Data policy)](../../00_governance/DATA_POLICY.md)
- [Mô hình mối đe dọa (Threat model)](THREAT_MODEL.md)
- [Vận hành và sự cố (Operations and incidents)](../operations/INCIDENT_RESPONSE.md)
