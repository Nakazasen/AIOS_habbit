# Chỉ Mục Chuyên Nghiệp Hóa (Professionalization Index)

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-08-29
Review cadence: Each Gate Card closure and release candidate

## Mục Đích (Purpose)

Chỉ mục này là bản đồ điều hướng cho các bản ghi kỹ thuật chuyên nghiệp. Trạng thái chuyển giao hiện tại của dự án vẫn là nguồn chân lý canonical trong `ROADMAP.md`; tệp này không thay thế tệp đó.

Agent và người kế thừa **không đọc chỉ mục này trước** `AGENTS.md`. Lớp đọc: L0 `AGENTS.md` → L1 `CONSTITUTION.md` + `AGENT_RULES.md` → L2 kiến trúc/roadmap/ADR → L3 đúng một spec. Cây `00_`–`12_` và `docs/archive/` không phải lối vào.

| Lĩnh vực | Bản ghi Canonical | Trọng tâm trạng thái |
|---|---|---|
| Kiểm soát tài liệu | [Quản trị tài liệu](DOCUMENTATION_GOVERNANCE.md) | Nguồn canonical và quy tắc đánh giá |
| Bảo mật | [Chính sách bảo mật](../SECURITY.md), [mô hình mối đe dọa](security/THREAT_MODEL.md) | Kênh báo cáo và rủi ro tồn dư cần chủ sở hữu xem xét |
| Quyền riêng tư/Dữ liệu | [Đánh giá tác động quyền riêng tư](security/PRIVACY_IMPACT_ASSESSMENT.md), [chính sách dữ liệu](../00_governance/DATA_POLICY.md) | Quyết định cơ sở pháp lý/lưu trữ/provider đang chờ |
| Phụ thuộc | [Chính sách phụ thuộc](security/DEPENDENCY_POLICY.md), [chính sách SBOM](release/SBOM_POLICY.md) | Thực thi cảnh báo đang chờ |
| Kiến trúc | [Ngữ cảnh](architecture/CONTEXT.md), [container](architecture/CONTAINERS.md), [thành phần](architecture/COMPONENTS.md), [triển khai](architecture/DEPLOYMENT.md) | Các khung nhìn runtime/container hiện hành |
| Quyết định | [Chỉ mục ADR](adr/README.md) | Các quyết định trọng yếu mới bắt buộc phải có ADR |
| Yêu cầu | [Sản phẩm](requirements/PRODUCT_REQUIREMENTS.md), [NFR](requirements/NON_FUNCTIONAL_REQUIREMENTS.md), [truy xuất nguồn gốc](requirements/TRACEABILITY_MATRIX.md) | Các mục tiêu đánh dấu TBD vẫn chưa được phê duyệt |
| Giao diện/Dữ liệu | [Giao diện runtime](contracts/RUNTIME_INTERFACES.md), [tương thích dữ liệu lưu trữ](contracts/PERSISTED_DATA_COMPATIBILITY.md) | Khung di chuyển chính thức chưa được triển khai |
| Chất lượng | [Chiến lược kiểm thử](quality/TEST_STRATEGY.md), [cổng chất lượng](quality/QUALITY_GATES.md), [UX/tiếp cận](quality/UX_ACCESSIBILITY_ACCEPTANCE.md) | Đánh giá thủ công khả năng tiếp cận đang chờ |
| Vận hành | [Sao lưu/phục hồi](operations/BACKUP_RESTORE.md), [ứng phó sự cố](operations/INCIDENT_RESPONSE.md), [xử lý sự cố](operations/TROUBLESHOOTING.md), [quan sát](operations/OBSERVABILITY.md) | Diễn tập phục hồi tổng hợp đã đạt; RTO/RPO vẫn là quyết định của chủ sở hữu |
| Phát hành | [Chính sách phát hành](release/RELEASE_POLICY.md), [checklist](release/RELEASE_CHECKLIST.md), [phiên bản hỗ trợ](release/SUPPORTED_VERSIONS.md) | Kênh phân phối / cửa sổ hỗ trợ đang chờ |
| Quản trị | [Sổ rủi ro](governance/RISK_REGISTER.md), [sở hữu](governance/OWNERSHIP_AND_REVIEW.md), [DoR/DoD](governance/DEFINITION_OF_READY_DONE.md) | Chỉ định sở hữu bằng tên đang chờ |
| Sản phẩm hóa | [Hướng dẫn người dùng](user/WORKSPACE_CHAT_USER_GUIDE.md), [onboarding](onboarding/MAINTAINER_ONBOARDING.md), [di chuyển](operations/DATA_MIGRATION_COMPATIBILITY.md) | Đánh giá thủ công và quyết định chính sách đang chờ |
| Tầm nhìn sản phẩm | [Định vị sản phẩm](AIOS_PRODUCT_POSITIONING.md), [tầm nhìn trí tuệ sản xuất](design/PRODUCTION_INTELLIGENCE_VISION.md) | Định vị = canonical sứ mệnh/giai đoạn; trí tuệ sản xuất = thiết kế dài hạn, chưa mở gate |
| Stub (đừng đọc nội dung cũ) | `PRODUCT_NORTH_STAR.md`, `WORKLENS_ARCHITECTURE.md`, `WORKLENS_MASTER_ROADMAP.md` | Chỉ chuyển hướng |

## Các Quyết Định Bắt Buộc Của Chủ Sở Hữu (Required Owner Decisions)

1. Kênh báo cáo bảo mật riêng tư và quy trình công bố lỗ hổng.
2. Kênh phân phối phát hành và cửa sổ phiên bản được hỗ trợ.
3. Chính sách lưu trữ/xóa dữ liệu và các mục tiêu khôi phục (RTO/RPO).
4. Danh tính người đánh giá / chủ sở hữu dự phòng và tên tài khoản trong CODEOWNERS của repository.
5. Công cụ quét cảnh báo SBOM/lỗ hổng, ngưỡng mức độ và trạng thái thực thi.

Cho đến khi các quyết định trên được ghi nhận, các chính sách tương ứng vẫn ở trạng thái `PROPOSED` hoặc `OWNER_DECISION_REQUIRED`, không phải là các bảo đảm phát hành.

