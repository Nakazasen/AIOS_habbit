# Các Thành phần Kiến trúc (Architecture Components)

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before a component contract, data class or supported UI changes

## Sơ đồ các thành phần được hỗ trợ (Supported Component Map)

| Thành phần | Vai trò | Bằng chứng trọng yếu |
|---|---|---|
| `workspace_chat_app` | Khởi tạo giao diện người dùng Streamlit được hỗ trợ và luồng chủ sở hữu | Gate kiểm tra import Workspace Chat |
| `workspace_chat_store` | Lưu trữ bền vững sổ ghi chép/tin nhắn/nguồn bằng JSONL (được gitignore) | Các bài test store và runbook sao lưu |
| `workspace_chat_source_ingest` | Ranh giới trích xuất tệp tải lên cục bộ | Các bài test ingest / lỗi an toàn phía người dùng |
| `workspace_chat_ai_answer` | Điều phối câu trả lời cục bộ / ngữ cảnh nguồn | Các bài test AI của Workspace Chat |
| `brain_gateway` | Nhãn bảo mật, sự đồng ý (consent), làm sạch dữ liệu và tính hợp lệ gửi ra ngoài | Các bài test quyền riêng tư Router mock |
| `workspace_chat_router_adapter` | Kết quả từ Router → Thông điệp an toàn trên UI | Bằng chứng smoke test trọng điểm router/live |
| `rag_v2` | Nền tảng generic element / chunk / chỉ mục cục bộ (local-index) | Thiết kế & các bài test RAG v2 |
| `rag_v2.adaptive_retrieval` | Cổng phân luồng thích ứng Pre/Post-Gate, Circuit Breaker và bảo vệ hạ cấp trong suốt | Test adaptive retrieval, benchmark report & schema v3 |
| `audit` / `cli` | Xác thực an toàn / bằng chứng của repository | Gate CLI audit |


## Ranh giới Quyền sở hữu (Ownership Boundary)

Ứng dụng sở hữu quyết định chọn nguồn dữ liệu, nhãn bảo mật/sự đồng ý của người dùng và hành vi an toàn phía giao diện. Router nhà cung cấp chỉ sở hữu hành vi lựa chọn/gọi provider; nhà cung cấp (provider) chịu trách nhiệm về dịch vụ bên ngoài và điều khoản của họ.

## Ranh giới Hệ thống Cũ đã biết (Known Legacy Boundary)

`case_cockpit` và các dịch vụ dùng chung cũ vẫn còn hiện diện để phục vụ kế hoạch dừng phụ thuộc tách biệt. Mã nguồn Workspace Chat được hỗ trợ tuyệt đối không được đưa trở lại các tuyến legacy công khai.

## Các Bản ghi Liên quan (Related Records)

- [Hợp đồng giao diện runtime (Runtime interfaces)](../contracts/RUNTIME_INTERFACES.md)
- [Khả năng tương thích dữ liệu lưu trữ (Persisted-data compatibility)](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Cổng chất lượng (Quality gates)](../quality/QUALITY_GATES.md)

