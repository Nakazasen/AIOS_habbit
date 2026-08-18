# Nghiệm Thu Trải Nghiệm Người Dùng và Khả Năng Tiếp Cận (UX and Accessibility Acceptance)

Status: `PROPOSED`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before supported UI release or material interaction change

## Phạm Vi (Scope)

Danh mục kiểm tra này áp dụng cho luồng làm việc Workspace Chat ưu tiên Tiếng Việt (Vietnamese-first) được hỗ trợ. Đây là mức cơ sở nghiệm thu, không phải là tuyên bố đã đạt chứng nhận khả năng tiếp cận (accessibility certification) hoàn chỉnh.

## Các Hạng Mục Kiểm Tra Nghiệm Thu Bắt Buộc

| Khu vực | Kiểm tra | Bằng chứng / Trạng thái hiện tại |
|---|---|---|
| Ngôn ngữ | Luồng chính hướng tới người dùng ưu tiên Tiếng Việt; các hằng số kỹ thuật được giải thích gần kề. | `PARTIAL` — chính sách và nhãn UI đã tồn tại; cần đánh giá thủ công |
| Bàn phím | Chủ sở hữu có thể thực hiện các hành động chính, hộp thoại và xác nhận xóa mà không bắt buộc dùng chuột. | `PLANNED` kiểm tra thủ công |
| Tiêu điểm (Focus) | Tiêu điểm di chuyển có thể dự đoán sau khi tạo/chọn/lưu trữ/xóa và khi ở trạng thái lỗi. | `PLANNED` kiểm tra thủ công |
| Nhãn phần tử | Các ô nhập liệu/nút bấm có nhãn ngữ nghĩa rõ ràng thay vì chỉ mang ý nghĩa qua biểu tượng đơn thuần. | `PLANNED` kiểm tra thủ công |
| Độ tương phản | Độ tương phản của văn bản, lỗi, cảnh báo và trạng thái được chọn được kiểm tra trong giao diện hỗ trợ. | `PLANNED` kiểm tra thủ công |
| Trạng thái lỗi | Lỗi bằng Tiếng Việt an toàn; tuyệt đối không làm lộ traceback thô/secret/đường dẫn lên giao diện người dùng. | `PARTIAL` — kiến trúc/test đã bao phủ lỗi an toàn; cần kiểm tra UI thủ công |
| Trống/Đang tải/Ngoại tuyến | Chủ sở hữu hiểu rõ các trạng thái: không có nguồn, chưa đủ bằng chứng, trích xuất lỗi và provider AI tùy chọn lỗi. | `PARTIAL` — văn bản đã có; cần đánh giá quy trình |
| Nội dung dài | Danh sách nguồn và câu trả lời dài vẫn dễ hiểu mà không che khuất ngữ cảnh trích dẫn. | `PLANNED` kiểm tra thủ công |
| Minh bạch sự đồng ý | Hiệu lực của nhãn bảo mật / sự đồng ý được giải thích rõ trước khi gọi tuyến gửi ra ngoài. | `PARTIAL` — ranh giới chính sách đã được ghi nhận; cần đánh giá UI |

## Giao Thức Đánh Giá Thủ Công (Manual Review Protocol)

Chỉ sử dụng nội dung tổng hợp an toàn. Ghi lại phiên bản trình duyệt / Streamlit, kịch bản, pass/fail, ID issue và ảnh chụp màn hình đã làm sạch chỉ khi chủ sở hữu cho phép rõ ràng bên ngoài Git. Tuyệt đối không sử dụng sổ ghi chép riêng tư, API key hay lệnh gọi provider thật.

## Quy Tắc Hoàn Tất (Exit Rule)

Một bản phát hành hướng tới người dùng không thể tuyên bố đáp ứng khả năng tiếp cận cho đến khi các kiểm tra liên quan được thực hiện, các issue được phân loại và quyết định đánh giá của chủ sở hữu được ghi nhận.

