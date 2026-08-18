# Trình tự: Gọi Router & Xử lý Lỗi An toàn (Router Call & Safe Failure)

Status: `ACTIVE`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Each router/provider upgrade or error-contract change

```mermaid
sequenceDiagram
    participant C as Caller đã phê duyệt
    participant A as WorkspaceChatRouterAdapter
    participant R as Nakazasen Router
    participant P as Provider đã cấu hình
    C->>A: câu hỏi + prompt hệ thống/người dùng
    A->>R: khởi tạo router từ biến môi trường
    A->>R: route_outcome(AIRequest)
    R->>P: Yêu cầu tới provider tùy chọn
    P-->>R: Kết quả hoặc lỗi từ provider
    R-->>A: Kết quả đã chuẩn hóa (Normalized outcome)
    alt Thành công (Success)
        A-->>C: Văn bản câu trả lời
    else Thất bại (Failure)
        A-->>C: Thông báo lỗi an toàn bằng Tiếng Việt
    end
```

Key được đọc từ biến môi trường của tiến trình tại thời điểm gọi. Adapter tuyệt đối không được in key, dữ liệu authorization thô hay payload yêu cầu provider ra log. Mọi lỗi từ provider đều được ánh xạ sang thông điệp an toàn cho người dùng.

## Các Bản ghi Liên quan (Related Records)

- [ADR-0005](../../adr/0005-router-provider-routing-boundary.md)
- [Quy trình phản ứng sự cố (Incident response)](../../operations/INCIDENT_RESPONSE.md)

