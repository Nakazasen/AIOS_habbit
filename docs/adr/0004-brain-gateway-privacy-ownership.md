# ADR-0004: Brain Gateway Sở Hữu Các Quyết Định Quyền Riêng Tư & Sự Đồng Ý

Status: `ACCEPTED`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before a data label, consent or external-route change

## Bối cảnh (Context)

Hệ thống định tuyến của nhà cung cấp (provider routing) tuyệt đối không được tự quyết định xem dữ liệu của chủ sở hữu có được phép rời khỏi tiến trình cục bộ hay không. Sản phẩm cần hành vi từ chối theo mặc định (default-deny), yêu cầu sự đồng ý tường minh đối với các phân loại dữ liệu nhạy cảm và làm sạch payload.

## Quyết định (Decision)

Hàm `BrainGateway.preflight_check()` sở hữu phân loại bảo mật canonical, băm tập nguồn (source-set hashing), xác thực sự đồng ý (consent), cấp phép bằng chứng gửi ra ngoài và hợp đồng làm sạch dữ liệu (sanitization contract). Cả luồng mock router lẫn luồng provider Workspace Chat thực tế hiện tại đều phải tạo một `BrainRequest` và gọi hợp đồng này trước khi adapter đủ điều kiện được chạy.

Tuyến Workspace Chat thực tế sử dụng đích đến ổn định `workspace_chat_external_router` và mục đích `workspace_chat_answer`. Nó kiểm tra chính sách đối chiếu với toàn bộ ảnh chụp nhanh tập nguồn đang kích hoạt, ngay cả khi truy xuất cục bộ chỉ chọn ra một tập con. Adapter thực tế chỉ chấp nhận `SanitizedRouterPayload`, do đó các thông điệp gửi tới provider không thể được cung cấp dưới dạng prompt thô tự xây dựng độc lập.

## Hệ quả (Consequences)

- Các adapter của nhà cung cấp chỉ nhận hợp đồng payload đã được phép/làm sạch.
- Các nhãn `local_only`/`confidential` bị từ chối cứng (hard-denied); `unknown`/`machine_only` yêu cầu sự đồng ý ràng buộc. Lựa chọn chia sẻ tường minh của chủ sở hữu sẽ tạo ra nhãn `cloud_safe`.
- Các nhãn `machine_only`/`cloud_allowed` cũ đã lưu trữ vẫn giữ trạng thái không thể gửi cho đến khi chủ sở hữu đưa ra lựa chọn chia sẻ mới tường minh; tuyệt đối không tự động di chuyển ngầm.
- Việc lựa chọn nhãn bảo mật vẫn là trách nhiệm của chủ sở hữu và là rủi ro tồn dư.

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Đây là chốt chặn kiểm soát cốt lõi nhằm tối thiểu hóa dữ liệu (data minimization) tại ranh giới kết nối với provider bên ngoài. Nó bắt buộc phải được kiểm thử trong mọi đợt thay đổi tuyến trọng yếu.

## Di chuyển & Hoàn tác (Migration and Rollback)

Bất kỳ thay đổi ngữ nghĩa nào về nhãn/sự đồng ý đều bắt buộc phải có ADR mới, cập nhật đánh giá quyền riêng tư, bổ sung bài kiểm thử hồi quy và tuyên bố tương thích cho các nhãn nguồn đã lưu trữ.

## Bằng chứng Liên kết (Evidence)

- [Mã nguồn Gateway](../../src/aios_habit/brain_gateway.py)
- [Mô hình mối đe dọa (Threat model)](../security/THREAT_MODEL.md)
- [Đánh giá tác động quyền riêng tư (Privacy impact assessment)](../security/PRIVACY_IMPACT_ASSESSMENT.md)

