# Trình tự: Kiểm tra Trước khi Gửi Ra Ngoài Workspace Chat (External Preflight)

Status: `ACTIVE`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing labels, consent or external destinations

```mermaid
sequenceDiagram
    participant UI as Workspace Chat
    participant G as BrainGateway
    participant O as Sự đồng ý chủ sở hữu (Consent)
    participant A as Bộ chuyển đổi Router
    participant P as Provider tùy chọn
    UI->>G: BrainRequest(toàn bộ nguồn, bằng chứng truy xuất, đích đến, mục đích)
    G->>G: Xác minh tập nguồn đầy đủ & nhãn bảo mật nghiêm ngặt nhất
    alt local_only hoặc confidential
        G-->>UI: Từ chối: bắt buộc dùng tuyến chỉ cục bộ (local-only)
    else unknown hoặc machine_only
        G->>O: Xác thực sự đồng ý theo tập nguồn/đích đến/mục đích
        alt Sự đồng ý không hợp lệ hoặc bị thiếu
            G-->>UI: Từ chối: yêu cầu phân loại hoặc xác nhận đồng ý
        else Hợp lệ
            G->>G: Ủy quyền bằng chứng đối chiếu với toàn bộ tập nguồn
            G->>G: Làm sạch dữ liệu (Sanitize payload)
            G-->>A: SanitizedRouterPayload
        end
    else cloud_safe hoặc public
        G->>G: Ủy quyền bằng chứng & làm sạch payload
        G-->>A: SanitizedRouterPayload
    end
    A->>A: Xây dựng thông điệp provider CHỈ từ payload đã làm sạch
    A->>P: Gửi yêu cầu tới provider tùy chọn
    P-->>A: Kết quả hoặc thông báo lỗi an toàn
    A-->>UI: Phản hồi an toàn bằng Tiếng Việt
```

Trình tự này tài liệu hóa tuyến tùy chọn đã được triển khai; nó không kích hoạt bất kỳ provider nào theo mặc định. Tuyến này luôn bị chặn khi cấu hình router không khả dụng, chính sách từ chối, hoặc truy xuất không mang lại bằng chứng đủ điều kiện.

## Các Bản ghi Liên quan (Related Records)

- [ADR-0004](../../adr/0004-brain-gateway-privacy-ownership.md)
- [Đánh giá tác động quyền riêng tư (Privacy impact assessment)](../../security/PRIVACY_IMPACT_ASSESSMENT.md)

