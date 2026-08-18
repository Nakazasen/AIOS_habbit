# Đường Cơ Sở Yêu Cầu Sản Phẩm (Product Requirements Baseline)

Status: `ACTIVE`
Owner role: Project owner / product reviewer
Last reviewed: 2026-07-25
Review cadence: Before a product-scope or supported-flow change

## Phạm Vi (Scope)

Đường cơ sở này ghi nhận các hành vi sản phẩm hiện đang được hỗ trợ. Nó không tự ý mở các công việc theo kế hoạch của RAG, A18 hoặc P1.0.

| ID | Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|---|
| PR-01 | Chủ sở hữu có thể khởi chạy một giao diện Workspace Chat được hỗ trợ duy nhất tại cục bộ. | `IMPLEMENTED` | README, cổng import Workspace Chat |
| PR-02 | Chủ sở hữu có thể tạo/chọn sổ ghi chép cục bộ và ngữ cảnh nguồn dữ liệu. | `IMPLEMENTED` | Kiểm thử Workspace Chat store/app |
| PR-03 | Chủ sở hữu có thể gắn nhãn bảo mật nguồn cục bộ trước khi định tuyến AI tùy chọn. | `IMPLEMENTED` | Hành vi UI/Gateway và các bài kiểm thử quyền riêng tư |
| PR-04 | Nội dung chỉ dùng cục bộ / bảo mật không đủ điều kiện định tuyến tới provider bên ngoài. | `IMPLEMENTED` | Kiểm thử `brain_gateway` |
| PR-05 | Câu trả lời hiển thị ngữ cảnh nguồn / bằng chứng hoặc thông báo chưa đủ bằng chứng thay vì tạo ra sự chắc chắn bịa đặt. | `PARTIAL` | Bản xem trước hiện tại / thiết kế RAG; tổng hợp nâng cao vẫn nằm trong kế hoạch |
| PR-06 | Lỗi từ provider tùy chọn phải an toàn và hiển thị bằng Tiếng Việt. | `IMPLEMENTED` | Kiểm thử adapter Workspace router |
| PR-07 | Người dùng mặc định có thể vận hành mà không cần dịch vụ đám mây. | `IMPLEMENTED` | Hiến pháp, tài liệu cài đặt và kiến trúc |
| PR-08 | Giao diện Studio / Case Cockpit cũ không còn là tuyến được hỗ trợ cho người dùng thông thường. | `IMPLEMENTED` | Roadmap và bằng chứng dừng hoạt động (retirement) |

## Ngoài Phạm Vi (Out of scope)

Truy xuất ngữ nghĩa / vector, OCR hình ảnh PNG, đồng bộ hóa đa người dùng, sao lưu đám mây tự động và đảm bảo tính khả dụng của provider bên ngoài hiện không phải là các yêu cầu của sản phẩm hôm nay.

## Các Bản Ghi Liên Quan (Related Records)

- [Đường cơ sở yêu cầu phi chức năng (NFR baseline)](NON_FUNCTIONAL_REQUIREMENTS.md)
- [Ma trận truy xuất nguồn gốc (Traceability matrix)](TRACEABILITY_MATRIX.md)
- [Hướng dẫn người dùng (User guide)](../user/WORKSPACE_CHAT_USER_GUIDE.md)

