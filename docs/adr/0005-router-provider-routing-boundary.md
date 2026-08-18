# ADR-0005: Router Là Phụ Thuộc Định Tuyến Provider, Không Phải Thẩm Quyền Chính Sách

Status: `ACCEPTED`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Each router upgrade or new provider integration

## Bối cảnh (Context)

AIOS sử dụng Nakazasen AI Router để lựa chọn/gọi các provider đã cấu hình. Quyền riêng tư, sự đồng ý trong sản phẩm và quyền sở hữu nguồn dữ liệu là trách nhiệm của AIOS.

## Quyết định (Decision)

Ghim phiên bản và tích hợp router như một phụ thuộc định tuyến provider. AIOS tiếp tục sở hữu các quyết định chính sách, tối thiểu hóa prompt/nguồn, sự đồng ý của người dùng và xử lý lỗi an toàn phía giao diện. Adapter Workspace Chat trực tiếp tiếp nhận kết quả từ router và trả về thông điệp Tiếng Việt an toàn; tuyệt đối không tải tệp chứa key làm cấu hình ứng dụng bền vững.

## Hệ quả (Consequences)

- Nâng cấp Router đòi hỏi kiểm tra tính tương thích, chạy các bài test trọng điểm và kiểm chứng toàn diện.
- Năng lực của Router không đồng nghĩa với việc tự động cấp quyền truyền dữ liệu ra ngoài.
- Các bài kiểm thử trực tiếp luôn chạy tường minh, theo kịch bản generic và sử dụng biến môi trường tạm thời.

## Tác động Bảo mật & Quyền riêng tư (Security and Privacy Impact)

Router nằm ngoài thẩm quyền quyết định chính sách. Điều khoản của nhà cung cấp, tính khả dụng và thời gian lưu trữ dữ liệu vẫn là nghĩa vụ đánh giá của chủ sở hữu bên ngoài.

## Di chuyển & Hoàn tác (Migration and Rollback)

Hoàn tác (Revert) về tag router đã được kiểm chứng gần nhất, cài đặt lại trong môi trường sạch và chạy lại toàn bộ quality gates. Tuyệt đối không tự động cập nhật (self-update) thay cho chủ sở hữu.

## Bằng chứng Liên kết (Evidence)

- [Bộ chuyển đổi Router (Router adapter)](../../src/aios_habit/workspace_chat_router_adapter.py)
- [Chính sách phụ thuộc (Dependency policy)](../security/DEPENDENCY_POLICY.md)
- [Chính sách phát hành (Release policy)](../release/RELEASE_POLICY.md)

