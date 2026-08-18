# Chính sách Bảo mật (Security Policy)

Status: `PROPOSED`
Owner role: Project owner / designated security contact
Last reviewed: 2026-07-25
Review cadence: Each release candidate and after a security-relevant change

## Phạm vi (Scope)

AIOS WorkLens là một ứng dụng ưu tiên cục bộ (local-first). Phạm vi bảo mật bao gồm mã nguồn được theo dõi, các artifact phát hành, cấu hình phụ thuộc, ranh giới dữ liệu cục bộ và tích hợp nhà cung cấp AI bên ngoài tùy chọn. Các tài liệu riêng tư cục bộ, tệp JSONL/SQLite runtime và thông tin xác thực (credentials) tuyệt đối không được đính kèm vào các báo cáo công khai.

## Các phiên bản được hỗ trợ (Supported versions)

| Dòng phiên bản | Trạng thái |
|---|---|
| Nhánh `main` hiện tại / ứng viên phát hành (RC) tiếp theo | Được hỗ trợ các bản sửa lỗi bảo mật |
| Các bản phát hành lịch sử | `OWNER_DECISION_REQUIRED` |

Khung phiên bản được hỗ trợ chính thức sẽ được định nghĩa chi tiết tại
[docs/release/SUPPORTED_VERSIONS.md](docs/release/SUPPORTED_VERSIONS.md).

## Báo cáo lỗ hổng bảo mật (Reporting a vulnerability)

**OWNER_DECISION_REQUIRED:** Cần cấu hình một kênh báo cáo riêng tư trước bất kỳ đợt phát hành công khai nào. Cho đến khi có quyết định đó, không mở issue công khai chứa các bước khai thác, API key, đường dẫn tệp cục bộ, tài liệu riêng tư hoặc log nhạy cảm.

Một báo cáo an toàn bao gồm: phiên bản/commit bị ảnh hưởng, trường hợp tái lập tối thiểu bằng dữ liệu tổng hợp (synthetic), mức độ tác động, điều kiện tiên quyết tấn công và giải pháp khắc phục đề xuất. Báo cáo không được chứa thông tin xác thực thực tế hoặc dữ liệu của khách hàng/chủ sở hữu.

## Phân loại & Công bố (Triage and disclosure)

Vòng đời xử lý đề xuất: Tiếp nhận (acknowledge) → Tái lập bằng dữ liệu tổng hợp → Khoanh vùng cách ly (contain) → Khắc phục và kiểm thử → Công bố khuyến cáo/ghi chú phát hành đã làm sạch (sanitized). Mục tiêu thời gian phản hồi và khung thời gian cấm tiết lộ/công bố vẫn ở trạng thái `OWNER_DECISION_REQUIRED`; tài liệu này không cam kết SLA cố định.

## Tài liệu tham khảo thiết kế bảo mật (Security design references)

- [Mô hình mối đe dọa (Threat model)](docs/security/THREAT_MODEL.md)
- [Đánh giá tác động quyền riêng tư (Privacy impact assessment)](docs/security/PRIVACY_IMPACT_ASSESSMENT.md)
- [Chính sách phụ thuộc (Dependency policy)](docs/security/DEPENDENCY_POLICY.md)
- [Quy trình phản ứng sự cố (Incident response)](docs/operations/INCIDENT_RESPONSE.md)

