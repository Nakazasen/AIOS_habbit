# Chính Sách Phát Hành (Release Policy)

Status: `PROPOSED`
Owner role: Release owner / project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and hotfix

## Trạng thái Phân phối (Distribution Status)

Quy trình làm việc đã được kiểm chứng hiện tại là cài đặt editable cục bộ từ bản checkout của repository. Bản phát hành GitHub Releases, xuất bản lên package registry, các artifact có chữ ký số và trình cài đặt tự động ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu); chính sách này không tuyên bố chúng đã tồn tại.

## Đánh số Phiên bản (Versioning)

Sử dụng phiên bản package trong `pyproject.toml` làm định danh phát hành. Đề xuất áp dụng quy tắc Semantic Versioning (SemVer):

- MAJOR: thay đổi giao diện được hỗ trợ / dữ liệu lưu trữ không tương thích ngược;
- MINOR: thêm tính năng mới tương thích ngược hoặc năng lực được hỗ trợ;
- PATCH: sửa lỗi / tài liệu / điều chỉnh phát hành tương thích ngược.

Các nhãn tiền phát hành (pre-release) và chính sách nhánh phát hành cần có sự phê duyệt của chủ sở hữu.

## Luồng Phát Hành (Release Flow)

1. Mở/xác nhận phạm vi đã phê duyệt và cập nhật các bản ghi yêu cầu / ADR / rủi ro.
2. Cập nhật phiên bản và ghi chú phát hành (release notes) khi có ý định phát hành bản phân phối.
3. Chạy [danh mục kiểm tra phát hành (Release checklist)](RELEASE_CHECKLIST.md) theo kế hoạch trên môi trường sạch.
4. Xem xét phụ thuộc/SBOM và độ an toàn của dữ liệu riêng tư.
5. Nhận phê duyệt chính thức từ chủ sở hữu/reviewer theo vai trò quản trị.
6. Chỉ xuất bản qua kênh đã được chủ sở hữu phê duyệt.
7. Lưu giữ tham chiếu hoàn tác (rollback) và bằng chứng hỗ trợ kỹ thuật.

## Ranh giới Phát hành Provider Bên ngoài (External-provider Release Boundary)

Một bản phát hành kích hoạt hoặc hiển thị một tuyến provider bên ngoài thực tế tuyệt đối không được tuyên bố việc thực thi quyền riêng tư đã sẵn sàng cho production trừ khi thẻ
[AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](../roadmap/completed/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
ở trạng thái `DONE` kèm theo các bài kiểm thử cụ thể cho tuyến và đánh giá đe dọa/quyền riêng tư hiện tại. Điều này không gỡ bỏ các chốt chặn cứng hiện có; nó ngăn chặn việc đưa ra tuyên bố phát hành quá mức mà chưa được hỗ trợ.

## Bản Vá Nóng (Hotfix)

Một bản vá nóng (hotfix) phải tuân thủ cùng các cổng chất lượng/bảo mật/quyền riêng tư, chỉ được giảm bớt bằng một quyết định rủi ro bằng văn bản. Nó bắt buộc phải nêu rõ lỗi thoái lui, bản sửa lỗi đã kiểm thử, mục tiêu hoàn tác và kế hoạch xem xét lại sau đó.

## Hoàn Tác (Rollback)

Quay trở lại phiên bản/commit đã kiểm chứng trước đó, khôi phục trạng thái cục bộ tương thích nếu cần, chạy lại các cổng chất lượng và ghi chép lại lý do. Tuyệt đối không hạ cấp/xóa dữ liệu bền vững của chủ sở hữu nếu thiếu kế hoạch tương thích.

