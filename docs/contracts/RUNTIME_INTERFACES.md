# Hợp Đồng Giao Diện Runtime (Runtime Interface Contracts)

Status: `ACTIVE`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing a public module boundary or provider contract

## Ranh giới Lưu trữ Bền vững Workspace Chat (Persistence Boundary)

`workspace_chat_store` sở hữu việc lưu trữ bền vững sổ ghi chép, cuộc trò chuyện, tin nhắn, nguồn và lựa chọn nguồn dưới thư mục `local_cases/workspace_chat/` (được gitignore). Caller sử dụng các đối tượng model và hàm store; các tệp vật lý là chi tiết triển khai nội bộ, không phải là API đồng bộ công khai.

## Ranh giới Cổng Quyền riêng tư (Privacy Gateway Boundary)

`BrainRequest` mang câu hỏi, ảnh chụp nhanh toàn bộ tập nguồn đang kích hoạt, sự đồng ý tùy chọn (consent), trạng thái router, mục đích, đích đến và tập con bằng chứng gửi ra ngoài tùy chọn. `BrainGateway.preflight_check()` là hợp đồng chính sách duy nhất cho cả tuyến thực tế và tuyến mock. Nó trả về `BrainDecision` gồm:

- `allowed` (cho phép hay không), mã lý do (reason code) và hành động tiếp theo;
- payload đã được làm sạch (sanitized payload) chỉ khi tuyến gửi ra ngoài được cho phép.

Đích đến của Workspace Chat ra bên ngoài là định danh ổn định `workspace_chat_external_router`; mục đích là `workspace_chat_answer`. Sự đồng ý phải khớp với cả hai giá trị này và khớp chính xác với mã băm (hash) toàn bộ tập nguồn đang kích hoạt. Bất kỳ đoạn trích xuất gửi ra ngoài nào cũng bắt buộc phải được ủy quyền bởi ảnh chụp nhanh toàn bộ nguồn đó.

## Ranh giới Provider Workspace Chat Thực tế

`generate_workspace_ai_answer()` chuyển đổi toàn bộ lựa chọn trong Workspace Chat thành một `BrainRequest` trước khi gọi router thực tế. Nó sử dụng phê duyệt từ Gateway để tạo ra payload duy nhất gửi ra ngoài. Các nhãn `local_only` và `confidential` bị từ chối cứng; `unknown` và `machine_only` yêu cầu sự đồng ý tương ứng. Lựa chọn chia sẻ hiện tại tường minh của chủ sở hữu được ánh xạ thành `cloud_safe`. Các bản ghi mang nhãn `machine_only` và `cloud_allowed` cũ mặc định vẫn không thể gửi cho đến khi được phân loại lại một cách chủ động.

## Ranh giới Router (Router Boundary)

Hàm `WorkspaceChatRouterAdapter.generate_answer()` chỉ chấp nhận `SanitizedRouterPayload` và trả về `(ok, text_or_safe_error)`. Nó xây dựng các thông điệp gửi tới provider trong nội bộ từ payload đã được phê duyệt này và ánh xạ các kết quả thất bại/ngoại lệ thành các thông điệp Tiếng Việt an toàn. Key tuyệt đối không bao giờ là đối số truyền vào hoặc giá trị trả về của hợp đồng này.

### Tự phục hồi mô hình của Provider (Provider Model Recovery)

Đối với các mô hình đám mây mặc định được quản lý theo danh mục (catalog-managed), `ai_router.route_answer()` có thể xử lý phản hồi `model_not_found` rõ ràng bằng cách thực hiện một lần thăm dò metadata mô hình (không chứa nội dung) và thử lại một lần với mô hình thay thế cùng dòng họ đã được phê duyệt trong danh mục. Lần thử lại sử dụng lại chính xác payload đã được phê duyệt; nó không thể thay đổi lựa chọn nguồn, đích đến, mục đích, phạm vi đồng ý hay phân loại bảo mật.

Việc ghi đè biến môi trường `AIOS_<PROVIDER>_MODEL` tường minh hoàn toàn do chủ sở hữu kiểm soát và tuyệt đối không bao giờ bị thay thế tự động. Việc khám phá mô hình không bao giờ đi theo URL do phản hồi của provider cung cấp và không bao giờ chọn tùy tiện mô hình đầu tiên từ phản hồi. Nếu không có mô hình thay thế nào đã phê duyệt hoạt động, tuyến kiểm tra sức khỏe/dự phòng thông thường của provider sẽ được áp dụng.

`aios-habit provider-check` là một lệnh chỉ dùng để chẩn đoán. Nó chỉ thăm dò metadata mô hình cho các provider đã cấu hình, in ra trạng thái/kết quả mô hình đã được làm sạch, không gửi bất kỳ tài liệu nguồn nào, không ghi bất kỳ cấu hình nào và tuyệt đối không bao giờ in API key.

## Ranh giới Chỉ mục RAG v2 (RAG v2 Index Boundary)

`LocalChunkIndex(db_path)` tạo/mở SQLite tại đường dẫn tường minh do caller chỉ định. `upsert_chunks`, `search`, `count`, `clear` và `close` là hợp đồng hiện tại. Tìm kiếm là thuật toán chấm điểm từ vựng (lexical) tất định, không phải là cam kết truy xuất ngữ nghĩa/FTS đầy đủ.

## Hợp đồng Xử lý Lỗi (Error Contract)

Các lỗi hiển thị cho người dùng trên giao diện được hỗ trợ bắt buộc phải là Tiếng Việt an toàn và tuyệt đối không làm lộ traceback thô, bí mật hay đường dẫn tệp cục bộ. Các ngoại lệ nội bộ là tín hiệu vận hành và phải được làm sạch trước khi chia sẻ hỗ trợ.

## Tính Tương thích (Compatibility)

Lựa chọn chia sẻ phía chủ sở hữu sẽ ghi nhận nhãn `cloud_safe`. Các nhãn `machine_only` và `cloud_allowed` đã lưu trữ trong quá khứ được giữ nguyên có chủ đích, không bị tự động phân loại lại hoặc tự động gửi ra ngoài; chủ sở hữu bắt buộc phải đưa ra lựa chọn chia sẻ mới tường minh. Bất kỳ thay đổi nào về chữ ký hàm / lược đồ dữ liệu đều yêu cầu các bài test hồi quy trọng điểm, một bản ghi ADR mới khi thay đổi ranh giới trọng yếu và cập nhật [PERSISTED_DATA_COMPATIBILITY.md](PERSISTED_DATA_COMPATIBILITY.md).

