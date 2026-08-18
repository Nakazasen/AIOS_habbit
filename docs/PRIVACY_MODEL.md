# Mô Hình Quyền Riêng Tư (Privacy Model)

Status: `ACTIVE`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before a new data class, external recipient or cloud route

AIOS WorkLens hoạt động theo nguyên tắc ưu tiên cục bộ (local-first). Nội dung repository công khai chỉ giới hạn ở mã nguồn, tài liệu, schema, mẫu (template) và các mẫu dữ liệu tổng hợp (synthetic samples). Dữ liệu runtime riêng tư luôn được giữ lại ở cục bộ và được Git bỏ qua (Git-ignored), bao gồm trạng thái Workspace Chat, JSONL bằng chứng / bộ nhớ, kết quả ứng viên, các gói xuất đã tạo và các báo cáo audit/handover cục bộ cuối cùng.

Khám phá luôn ưu tiên metadata trước (metadata-first). Quá trình trích xuất chỉ tạo ra các ứng viên, không phải chân lý đã được xác minh. Bộ nhớ đã xác thực (verified memory) bắt buộc phải có bằng chứng; các gói xuất bắt buộc phải được kiểm toán trước khi sử dụng.

Các chốt chặn kiểm soát quyền riêng tư kỹ thuật mang tính canonical bao gồm:

- [Chính sách dữ liệu (Data policy)](../00_governance/DATA_POLICY.md)
- [Đánh giá tác động quyền riêng tư (Privacy impact assessment)](security/PRIVACY_IMPACT_ASSESSMENT.md)
- [Mô hình mối đe dọa (Threat model)](security/THREAT_MODEL.md)
- [Ứng phó sự cố (Incident response)](operations/INCIDENT_RESPONSE.md)

Chưa có cam kết nào về lịch trình xóa/lưu trữ tự động, tuyên bố tuân thủ pháp lý hay phê duyệt bên xử lý phụ (subprocessor) của provider cho đến khi các quyết định chính thức của chủ sở hữu được ghi nhận.
