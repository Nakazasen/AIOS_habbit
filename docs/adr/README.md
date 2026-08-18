# Bản ghi Quyết định Kiến trúc (Architecture Decision Records)

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before a material architecture or boundary change

## Mục đích (Purpose)

Các bản ghi quyết định kiến trúc (ADR) lưu giữ bối cảnh, các giải pháp thay thế và hệ quả của các quyết định kỹ thuật trọng yếu. Chúng tách biệt với mẫu quyết định người dùng trong `11_templates/decision_record.md`.

## Vòng đời (Lifecycle)

- `ACCEPTED`: quyết định hiện hành đang áp dụng.
- `SUPERSEDED`: đã được thay thế bởi một ADR mới hơn được dẫn link.
- `DEPRECATED`: được giữ lại làm lịch sử nhưng không còn là quyết định khuyến nghị.
- `PROPOSED`: cần sự phê duyệt của chủ sở hữu trước khi triển khai.

Các ADR mới nhận số thứ tự tăng dần (có đệm số 0) và bắt buộc bao gồm: bối cảnh, động lực thúc đẩy quyết định, các phương án lựa chọn, quyết định, hệ quả, tác động bảo mật/quyền riêng tư, phương án khôi phục (rollback) và các liên kết bằng chứng. Các ADR lịch sử chỉ ghi nhận sự thật đã biết; không tuyên bố rằng các chốt chặn chưa triển khai đã tồn tại.

## Chỉ mục ADR (Index)

1. [ADR-0001: Quyền sở hữu hệ thống tệp ưu tiên cục bộ (Local-first filesystem ownership)](0001-local-first-filesystem-ownership.md)
2. [ADR-0002: Workspace Chat là giao diện được hỗ trợ duy nhất (Workspace Chat as supported UI)](0002-workspace-chat-supported-ui.md)
3. [ADR-0003: Chỉ mục từ vựng SQLite cục bộ (Local SQLite lexical index)](0003-local-sqlite-lexical-index.md)
4. [ADR-0004: Brain Gateway sở hữu các quyết định quyền riêng tư (Brain Gateway owns privacy decisions)](0004-brain-gateway-privacy-ownership.md)
5. [ADR-0005: Router là phụ thuộc định tuyến nhà cung cấp (Router is a provider-routing dependency)](0005-router-provider-routing-boundary.md)
6. [ADR-0006: Dữ liệu runtime riêng tư luôn nằm ngoài Git (Private runtime data stays outside Git)](0006-private-runtime-data-outside-git.md)

