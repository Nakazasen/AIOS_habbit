# Chiến Lược Kiểm Thử (Test Strategy)

Status: `ACTIVE`
Owner role: Maintainer / quality reviewer
Last reviewed: 2026-08-16
Review cadence: Each new runtime boundary, provider route or release candidate

## Mục Tiêu (Objectives)

Chứng minh hợp đồng ưu tiên cục bộ (local-first) và có bằng chứng xác thực mà không yêu cầu dữ liệu riêng tư hoặc thông tin xác thực provider trực tiếp trong quy trình phát triển / CI thông thường.

## Các Tầng Kiểm Thử (Test Layers)

| Tầng | Mục đích | Quy tắc mạng / Dữ liệu |
|---|---|---|
| Đơn vị (Unit) | Parse thuần túy, schema, quyết định quyền riêng tư, xếp hạng và ánh xạ lỗi | Dữ liệu tổng hợp (synthetic); nghiêm cấm kết nối mạng |
| Tích hợp (Integration) | Hợp đồng lưu trữ, bộ chuyển đổi, chỉ mục, Gateway và adapter | Đường dẫn tạm / fixture tổng hợp; nghiêm cấm kết nối mạng |
| Hệ thống / Import | Ranh giới khởi động Workspace Chat và CLI | Không chứa thông tin xác thực; nghiêm cấm kết nối mạng |
| Live Smoke thủ công | Kiểm tra hệ thống dây kết nối provider đã được phê duyệt rõ ràng | Chỉ dùng prompt generic; key tạm thời trong bộ nhớ; không có ngữ cảnh nguồn / không ghi log key |
| Đánh giá cục bộ riêng tư | Đánh giá tập dữ liệu của chủ sở hữu / chất lượng RAG | Chỉ chạy cục bộ, đầu ra bị gitignore, không bao giờ là artifact CI |

## Độ Bao Phủ Lưu Trữ Bền Vững Cục Bộ (Local Persistence Coverage)

- Các kho lưu trữ JSONL bắt buộc phải sử dụng cơ chế thay thế nguyên tử (atomic replacement) cho các thao tác ghi đơn tệp và hoàn tác (rollback) cho các thay đổi đa tệp liên quan.
- Một hàng dữ liệu cục bộ bị lỗi định dạng có thể được bỏ qua để duy trì tính khả dụng của ứng dụng, nhưng log hệ thống chỉ được xác định tên tệp kho lưu trữ và số dòng, tuyệt đối không ghi lại nội dung của bản ghi.
- Các bài kiểm thử hồi quy bắt buộc phải bao phủ: lưu trữ thành công, khả năng hiển thị hàng lỗi định dạng và hoàn tác sau khi thay thế thất bại.

## Chính Sách Dữ Liệu Mẫu (Fixture Policy)

- Các fixture dữ liệu phải mang tính tổng hợp (synthetic), tối giản và an toàn khi đưa vào Git.
- Tuyệt đối không commit tài liệu thô của chủ sở hữu, ảnh chụp màn hình, log cục bộ, token hoặc phản hồi provider thực tế.
- Các bài kiểm thử mẫu secret phải tự tạo giá trị giả mạo lúc runtime khi trình quét mã nguồn có thể nhầm một giá trị giả hoàn chỉnh thành một secret thật được theo dõi.

## Hành Vi AI và RAG

- Xử lý văn bản từ provider như một yếu tố bất định (nondeterministic); kiểm tra xác nhận hợp đồng / trạng thái / trích dẫn và hành vi lỗi thay vì so khớp chính xác từng từ ngữ trừ khi sử dụng bản giả lập tất định (deterministic fake).
- Đánh giá khả năng truy xuất đo lường hit@k, độ chính xác của trích dẫn, tính trung thực (faithfulness) và hành vi khi chưa đủ bằng chứng (insufficient evidence) như được định nghĩa trong thiết kế RAG v2.
- Kiểm thử Adaptive Reranking: Ma trận 60 ca truy vấn chuẩn hóa (`adaptive_routing_cases.json`) với đầy đủ các nhóm Fast, Hard, Ambiguous, Weak Evidence, Multi-Source và User Override Deep. Bắt buộc kiểm thử cơ chế Circuit Breaker (tự ngắt sau 3 lỗi), hạ cấp an toàn về Hybrid và cấm hiển thị "Đã tìm kỹ" sai sự thật.

## Tiêu Chí Hoàn Tất (Exit Criteria)

Mọi thay đổi hành vi đều phải cung cấp bằng chứng kiểm thử hồi quy trọng điểm, vượt qua tất cả các cổng chất lượng, bảo toàn các bài kiểm thử ranh giới quyền riêng tư và chỉ ghi nhận bằng chứng kiểm thử live thủ công khi một tuyến trực tiếp có sự thay đổi. Các bài kiểm thử chập chờn (flaky tests) thuộc trách nhiệm của người duy trì phát hiện/tạo ra và tuyệt đối không được tự động thử lại trong âm thầm như bằng chứng thành công.


