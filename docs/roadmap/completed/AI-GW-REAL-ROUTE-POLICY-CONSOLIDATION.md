# Hợp Nhất Chính Sách Tuyến Provider Thực Tế Cho AI-GW (AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION)

Status: `DONE`  
Owner role: Architecture and privacy reviewer  
Last reviewed: 2026-07-25  
Review cadence: After any provider-route change  

## Mục Tiêu (Goal)

Đảm bảo tuyến provider thực tế của Workspace Chat sử dụng duy nhất một ranh giới chính sách AIOS đã được kiểm chứng cho các nhãn bảo mật, xác nhận đồng ý trên tập nguồn, ràng buộc mục đích/đích đến, làm sạch payload và xây dựng yêu cầu provider an toàn.

## Ngữ Cảnh (Context)

Cờ `real_router_enabled` hiện xây dựng một `BrainRequest` từ ảnh chụp nhanh toàn bộ nguồn được kích hoạt và gọi `BrainGateway.preflight_check()` trước khi gọi router. Gateway ràng buộc sự đồng ý với `workspace_chat_external_router` và `workspace_chat_answer`, cấp quyền cho tập con truy xuất dựa trên toàn bộ ảnh chụp nhanh nguồn, và chỉ trả về payload duy nhất được chấp nhận bởi adapter router thực tế.

## Các Phi Mục Tiêu (Non-goals)

- Không thêm nhà cung cấp hoặc hành vi mặc định dùng cloud mới.
- Không bỏ qua / nới lỏng nguyên tắc ưu tiên cục bộ hoặc các chốt chặn cứng hiện có.
- Không nằm trong phạm vi truy xuất kết hợp RAG v2, A18 hoặc P1.0.
- Không di chuyển dữ liệu lưu trữ hay thêm bảng điều khiển kỹ thuật cho người dùng thông thường.

## Điều Kiện Tiên Quyết (Preconditions)

- Đường cơ sở chuyên nghiệp hóa đã hoàn thành với đầy đủ bằng chứng hiện tại.
- Chủ sở hữu đã phê duyệt đích đến bên ngoài và cách xử lý nhãn bảo thủ.
- Bộ kiểm thử hồi quy bảo mật tuyến thực tế hiện có chạy đạt (green).

## Danh Sách Cho Phép (Allowlist)

- `src/aios_habit/brain_gateway.py`
- `src/aios_habit/workspace_chat_ai_answer.py`
- `src/aios_habit/workspace_chat_router_adapter.py`
- `src/aios_habit/workspace_chat_retrieval.py`
- `src/aios_habit/workspace_chat_ui.py`
- Các bài kiểm thử hồi quy cho Gateway, Workspace Chat answer và quy trình của chủ sở hữu.
- Các hồ sơ tài liệu được liên kết rõ ràng bên dưới.

## Phạm Vi Đã Triển Khai (Implemented Scope)

- Tuyến thực tế sử dụng Gateway chuẩn tắc trước khi tạo prompt gửi ra ngoài.
- Sự đồng ý được ràng buộc chính xác với toàn bộ snapshot nguồn, đích đến và mục đích.
- `local_only` và `confidential` luôn bị từ chối tuyệt đối (hard-denied); `unknown` và `machine_only` mặc định bị từ chối nếu không có sự đồng ý hợp lệ.
- Lựa chọn tường minh "gửi ra bên ngoài" của chủ sở hữu sẽ tạo nhãn `cloud_safe`; các nhãn cũ như `machine_only` và `cloud_allowed` mặc định không được gửi.
- Adapter thực tế chỉ chấp nhận duy nhất `SanitizedRouterPayload` và tự xây dựng các message provider nội bộ; nó không chấp nhận các prompt thô được dựng độc lập từ bên ngoài.
- Bằng chứng được truy xuất giữ lại định danh nguồn cha của nó để các đoạn trích gửi ra ngoài được ủy quyền dựa trên toàn bộ tập nguồn đã kích hoạt.

## Bằng Chứng Nghiệm Thu và Đóng Cổng (Acceptance and Closure Evidence)

Đã kiểm chứng vào ngày 2026-07-25:

- Biên dịch tập trung và bộ kiểm thử hồi quy bảo mật / tuyến provider: `155 passed`.
- Hợp đồng tài liệu: `PASS`; biên dịch toàn bộ: `PASS`; toàn bộ pytest: `903 passed in 18.16s`.
- Kiểm toán CLI audit: `PASS` không có lỗi hay cảnh báo; Import Workspace Chat: `PASS` (chỉ có các cảnh báo chế độ bare-mode của Streamlit như kỳ vọng).
- `git diff --check` và `git diff --cached --check`: `PASS`.
- Các bài test chứng minh: từ chối tuyệt đối / không gọi adapter, từ chối khi thiếu sự đồng ý, từ chối khi tập nguồn bị cũ (stale), thực thi snapshot toàn bộ cho bằng chứng truy xuất, đầu vào adapter được định kiểu và làm sạch, từ chối prompt thô, và làm sạch đường dẫn/key trước khi định tuyến.
- Bằng chứng CI chỉ sử dụng fixture giả lập; không chứa thông tin xác thực provider hay lệnh gọi live nào.

## Trạng Thái Đóng Cổng (Closure Status)

Triển khai và kiểm chứng bắt buộc đã hoàn tất. Cổng này có thể hỗ trợ bằng chứng phát hành provider bên ngoài chỉ trong phạm vi các ràng buộc chính sách phát hành và quyết định của chủ sở hữu riêng biệt.

## Hoàn Tác (Rollback)

Chỉ hoàn tác lát cắt hợp nhất này nếu xảy ra hồi quy; tuyệt đối không vô hiệu hóa các chốt chặn bảo mật cứng hoặc đưa trở lại đầu vào prompt thô cho adapter như một đường tắt hoàn tác.


