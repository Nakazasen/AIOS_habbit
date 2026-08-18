# Hướng Dẫn Hội Nhập Cho Maintainer (Maintainer Onboarding)

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-08-16
Review cadence: Before handover and each release candidate

## 30 Phút Đầu Tiên (First 30 Minutes)

1. Đọc `README.md`, `CONSTITUTION.md`, `ROADMAP.md` và `PROJECT_HANDOVER.md`.
2. Đọc [chỉ mục chuẩn hóa chuyên nghiệp (Professionalization index)](../PROFESSIONALIZATION_INDEX.md) và ghi chú lại tất cả các mục `OWNER_DECISION_REQUIRED`.
3. Cài đặt chuỗi công cụ cục bộ đã khóa phiên bản bằng lệnh `uv sync --group dev`.
4. Chạy toàn bộ các [cổng chất lượng (Quality gates)](../quality/QUALITY_GATES.md) bắt buộc.
5. Xác nhận trạng thái Git không chứa bất kỳ tài liệu riêng tư / dữ liệu runtime nào bị đưa vào stage.

## Tác Vụ Làm Việc Đầu Tiên (First Working Task)

1. Tìm hoặc mở một Gate Card; không tự suy đoán rằng một hạng mục đang ở trạng thái lên kế hoạch (planned) là đang hoạt động.
2. Đọc các bản ghi ADR, yêu cầu nghiệp vụ, hợp đồng giao diện, mô hình mối đe dọa / quyền riêng tư và các bài test liên quan.
3. Luôn giữ dữ liệu nguồn / dữ liệu runtime ở cục bộ; sử dụng các fixture dữ liệu tổng hợp (synthetic).
4. Thực hiện thay đổi có phạm vi nhỏ nhất kèm theo độ bao phủ kiểm thử hồi quy trọng điểm.
5. Chỉ cập nhật roadmap / handover / changelog kèm theo bằng chứng kiểm chứng hiện tại.

## Trước Khi Phát Hành Hoặc Bàn Giao (Before Release or Handover)

- Tuân thủ [danh mục kiểm tra phát hành (Release checklist)](../release/RELEASE_CHECKLIST.md).
- Xem xét [sổ đăng ký rủi ro (Risk register)](../governance/RISK_REGISTER.md).
- Xem xét quy trình sao lưu / khôi phục và xử lý sự cố; tuyệt đối không tuyên bố đã diễn tập nếu không có bản ghi diễn tập tổng hợp thực tế.
- Nhận quyết định của chủ sở hữu đối với: kênh báo cáo bảo mật, phương thức phân phối, ma trận hỗ trợ, thời gian lưu trữ và thực thi cảnh báo phụ thuộc.

## Báo Cáo Leo Thang Thay Vì Đoán Mò (Escalate Instead of Guessing)

Bắt buộc hỏi ý kiến chủ sở hữu dự án trước khi: bật provider cho người dùng thông thường, thay đổi ngữ nghĩa nhãn bảo mật / sự đồng ý, di chuyển dữ liệu cục bộ, xuất bản artifact, sửa đổi quy tắc Git-ignore cho dữ liệu riêng tư hoặc xóa các dịch vụ dùng chung cũ.
