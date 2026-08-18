# Mô Hình Sở Hữu và Đánh Giá (Ownership and Review Model)

Status: `PROPOSED`
Owner role: Project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and when team membership changes

## Mô Hình Vai Trò (Role Model)

Repository này không nêu tên cá nhân hoặc tài khoản GitHub cụ thể khi chưa có sự phê duyệt của chủ sở hữu. Các vai trò dưới đây mô tả trách nhiệm giải trình bắt buộc.

| Vai trò | Trách nhiệm |
|---|---|
| Chủ sở hữu dự án (Project owner) | Phạm vi sản phẩm, quyết định của chủ sở hữu dữ liệu, phê duyệt phát hành |
| Người duy trì (Maintainer) | Thay đổi mã nguồn/tài liệu, bằng chứng kiểm thử/audit, sửa tài liệu lỗi thời |
| Người đánh giá kiến trúc (Architecture reviewer) | Đánh giá ADR, hợp đồng giao diện, di chuyển dữ liệu và ranh giới cũ |
| Người đánh giá bảo mật/quyền riêng tư | Đánh giá mô hình mối đe dọa, tuyến dữ liệu/đồng ý, phụ thuộc và sự cố |
| Người đánh giá phát hành (Release reviewer) | Đánh giá phiên bản, checklist, môi trường, hoàn tác và SBOM |
| Người vận hành / chủ sở hữu dữ liệu | Sao lưu cục bộ, diễn tập khôi phục, xử lý dữ liệu riêng tư |

## Các Yếu Tố Kích Hoạt Đánh Giá (Review Triggers)

| Thay đổi | Đánh giá bắt buộc |
|---|---|
| Thêm provider mới / gửi dữ liệu ra ngoài | Chủ sở hữu dự án + Người đánh giá bảo mật/quyền riêng tư |
| Dữ liệu lưu trữ bền vững / schema | Người đánh giá kiến trúc + Người vận hành / chủ sở hữu dữ liệu |
| Phụ thuộc hoặc phát hành | Người đánh giá phát hành + Người đánh giá bảo mật |
| Tuyến giao diện người dùng công khai | Chủ sở hữu dự án + Người đánh giá kiến trúc |
| Sự cố / Lộ thông tin bí mật | Chủ sở hữu dự án + Người đánh giá bảo mật |

## Tệp CODEOWNERS

`.github/CODEOWNERS` vẫn là một tệp giữ chỗ (placeholder) cho đến khi chủ sở hữu cung cấp tên tài khoản GitHub hoặc nhóm hợp lệ. Một tài liệu phân quyền vai trò không thể thay thế cho hệ thống kiểm soát truy cập (access control) của nền tảng lưu trữ Git.

