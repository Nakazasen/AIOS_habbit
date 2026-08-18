# Khả Năng Quan Sát và Chẩn Đoán (Observability and Diagnostics)

Status: `PROPOSED`
Owner role: Project owner / operations reviewer
Last reviewed: 2026-08-16
Review cadence: Before logging, telemetry or support-bundle changes

## Nguyên tắc (Principle)

AIOS WorkLens sử dụng cơ chế chẩn đoán cục bộ an toàn về quyền riêng tư. Hiện tại sản phẩm không tuyên bố có backend đo từ xa tập trung (central telemetry), backend số liệu (metrics) hay dịch vụ giám sát lưu trữ bên ngoài.

## Các Danh mục Chẩn đoán (Diagnostic Categories)

| Danh mục | Ví dụ được phép | Ví dụ bị cấm |
|---|---|---|
| Môi trường | Phiên bản Python/gói, dòng hệ điều hành, mã thoát lệnh | API key, giá trị biến môi trường, đường dẫn home/user |
| Trạng thái ứng dụng | Tính năng được chọn, reason code an toàn, số lượng/trạng thái | Văn bản nguồn thô, nội dung sổ ghi chép/tin nhắn |
| Router | Trạng thái chuẩn hóa / phân loại lỗi, provider/mô hình (chỉ khi được chủ sở hữu duyệt) | Header Authorization, API key, prompt/payload đầy đủ |
| Lưu trữ | Loại kho lưu trữ, sự tồn tại của tệp, số lượng chỉ mục | Các hàng JSONL, dữ liệu thô SQLite, tên tài liệu chủ sở hữu |
| Git / Chất lượng | Kết quả audit/kiểm thử, trạng thái được theo dõi / bỏ qua | Tên tệp/nội dung riêng tư từ các đường dẫn bị gitignore |

## Quy tắc Ghi Log (Logging Rules)

- Sử dụng các thông điệp người dùng an toàn bằng Tiếng Việt cho các lỗi trên giao diện được hỗ trợ.
- Giữ văn bản ngoại lệ nội bộ nằm ngoài giao diện người dùng trừ khi đã được làm sạch.
- Tuyệt đối không thêm telemetry, tải lên crash report hay analytics nếu không có ADR mới, đánh giá quyền riêng tư và sự phê duyệt của chủ sở hữu.
- Thời gian lưu trữ dữ liệu chẩn đoán ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu); các tệp chẩn đoán luôn ở cục bộ theo mặc định và tuyệt đối không được commit vào Git.

## Cơ chế Chẩn đoán Lưu trữ Cục bộ Hiện tại

Quá trình đọc JSONL hiện ghi log cảnh báo (warning) cho một bản ghi bị từ chối chỉ bằng tên tệp kho lưu trữ, số dòng và ngoại lệ đã chuẩn hóa. Quá trình ghi JSONL sử dụng cơ chế thay thế nguyên tử cục bộ (local atomic replacement); các thay đổi đa tệp liên quan sẽ cố gắng hoàn tác nếu việc thay thế thất bại. Đây là hành vi chẩn đoán cục bộ, không phải là dịch vụ telemetry và không phải là sự cho phép thu thập hoặc xuất các bản ghi runtime.

## Gói Chẩn đoán An toàn (Safe Diagnostic Bundle)

Một gói hỗ trợ kỹ thuật (support bundle), nếu được chủ sở hữu yêu cầu rõ ràng, chỉ chứa metadata phiên bản, trạng thái lệnh, mã lý do đã chuẩn hóa và các đoạn trích đã được làm sạch. Hãy tạo gói này bên ngoài repository, kiểm tra thủ công và xóa bỏ mọi đường dẫn/secret trước khi chia sẻ. Tuyệt đối không được bao gồm `local_cases/`, `local_runs/`, `.env`, tệp API key, nội dung prompt thô hay kho lưu trữ runtime SQLite/JSONL.

## Các Chỉ số Sức Khỏe (Health Indicators)

Các chỉ số sẵn sàng cục bộ hiện tại là: hợp đồng tài liệu PASS, biên dịch PASS, kiểm thử PASS, CLI audit PASS và import Workspace Chat PASS. Tính khả dụng của provider không phải là một yêu cầu sẵn sàng vì việc sử dụng provider là hoàn toàn tùy chọn.

