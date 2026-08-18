# Sổ Đăng Ký Rủi Ro (Risk Register)

Status: `ACTIVE`
Owner role: Project owner / risk reviewer
Last reviewed: 2026-07-25
Review cadence: Every release candidate, incident and material architecture change

| ID | Rủi ro | Khả năng | Tác động | Vai trò phụ trách | Biện pháp giảm thiểu | Điều kiện kích hoạt | Trạng thái tồn dư |
|---|---|---:|---:|---|---|---|---|
| RSK-01 | Dữ liệu/đường dẫn riêng tư bị gửi tới provider hoặc kênh công cộng | Trung bình | Cao | Người đánh giá quyền riêng tư | Gateway mặc định từ chối (default deny), kiểm thử sự đồng ý / làm sạch, chẩn đoán an toàn | Phát hiện tuyến/log/audit bất thường | Đang mở (Open) |
| RSK-02 | Prompt injection hoặc tài liệu độc hại thao túng luồng trả lời | Trung bình | Cao | Người đánh giá bảo mật | Ưu tiên cục bộ, kỷ luật bằng chứng, đánh giá mô hình mối đe dọa | Tuyến bộ phân tích / tổng hợp mới | Đang mở (Open) |
| RSK-03 | Rò rỉ thông tin xác thực hoặc sử dụng provider trái phép | Thấp-TB | Cao | Người đánh giá bảo mật / phát hành | Gitignore/audit, kiểm thử live bằng biến môi trường tạm thời, quy trình thu hồi | Quét secret, lộ dữ liệu ra công cộng | Đang mở (Open) |
| RSK-04 | Hỏng dữ liệu JSONL / chỉ mục cục bộ hoặc mất dữ liệu chủ sở hữu | Trung bình | Cao | Chủ sở hữu dữ liệu | Quy trình và đợt diễn tập sao lưu / phục hồi | Lỗi parse / lỗi chỉ mục | Đang mở (Open) |
| RSK-05 | Provider ngừng hoạt động / hết hạn ngạch / đổi mô hình làm gãy tuyến trả lời tùy chọn | Trung bình | Trung bình | Người đánh giá tích hợp | Thông báo lỗi an toàn, luồng dự phòng chỉ dùng cục bộ (local-only) | Lỗi Router / Provider | Rủi ro vận hành được chấp nhận |
| RSK-06 | Phụ thuộc bị xâm nhập / trôi lệch phiên bản | Trung bình | Cao | Người đánh giá phát hành / bảo mật | Ghim phiên bản, đánh giá, chính sách SBOM / cảnh báo lỗ hổng | Cảnh báo cập nhật hoặc cài đặt bất thường | Đang mở (Open) |
| RSK-07 | Khả năng truy xuất song ngữ yếu hoặc OCR không hỗ trợ gây hiểu lầm cho chủ sở hữu | Cao | Trung bình | Người đánh giá RAG | Ghi nhận rõ hạn chế, hành vi từ chối khi thiếu bằng chứng | Đánh giá không đạt mục tiêu | Đang mở (Kế hoạch RAG) |
| RSK-08 | Mất mát tri thức khi chỉ có một Maintain duy nhất | Trung bình | Cao | Chủ sở hữu dự án | Bàn giao (Handover), ADRs, Runbooks, quyết định sở hữu | Chủ sở hữu không sẵn sàng | Đang mở (Open) |
| RSK-09 | Tài liệu bị lệch pha so với mã nguồn | Trung bình | Trung bình | Người duy trì (Maintainer) | Kiểm tra hợp đồng tài liệu, đánh giá khi phát hành | Liên kết hỏng / tuyên bố lỗi thời | Đã kiểm soát (Controlled) |
| RSK-10 | Tuyến provider Workspace Chat thực tế bị lệch khỏi chính sách tiền kiểm / làm sạch của Gateway | Trung bình | Cao | Người đánh giá kiến trúc + quyền riêng tư | Gate hợp nhất P0 chuyên dụng, kiểm thử hồi quy theo tuyến và đánh giá mô hình đe dọa | Thay đổi tuyến provider hoặc sự đồng ý / làm sạch | Đang mở (Open) |

## Quy Tắc Đánh Giá (Review Rule)

Mỗi rủi ro đang mở (open risk) cần có ngày/quyết định đánh giá tiếp theo trong bằng chứng phát hành hoặc Gate Card. Biện pháp giảm thiểu chỉ giúp giảm rủi ro; nó không làm rủi ro tự biến mất nếu thiếu sự kiểm chứng thực tế.

