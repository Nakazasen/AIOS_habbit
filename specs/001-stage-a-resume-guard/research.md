# Nghiên Cứu: Chuẩn Bị Giai Đoạn A Có Khả Năng Tiếp Tục (Research: Resumable Stage A Preparation)

## Quyết Định: Lưu checkpoint trong cache staging của benchmark, không lưu trong registry của UI

**Lý do**: Bộ nhớ registry của adapter trong RAM là tạm thời và trình chạy benchmark sở hữu định danh giai đoạn theo địa chỉ nội dung cũng như manifest của giai đoạn. Một checkpoint nằm cạnh manifest đó sẽ tồn tại qua tiến trình bị dừng mà không làm thay đổi ngữ nghĩa phiên UI.

**Các phương án thay thế đã xem xét**:
- Lưu bền vững mọi mục chuẩn bị UI trên phạm vi toàn cục: bị từ chối vì có nguy cơ làm lẫn trạng thái giữa các workspace và thiếu định danh benchmark đóng băng.
- Xây dựng lại toàn bộ tập ngữ liệu sau sự cố: bị từ chối vì lặp lại công việc và che giấu nguồn bị chậm.

## Quyết Định: Chỉ ghi nhận các ID tài liệu đã commit mờ (opaque)

**Lý do**: Adapter tạo ra các ID tài liệu `wsc-` mờ ổn định. Kết hợp với định danh giai đoạn, chúng xác định sự hoàn thành mà không cần giữ lại tiêu đề, đường dẫn hay văn bản nguồn.

**Các phương án thay thế đã xem xét**:
- Lưu trữ tên và đường dẫn để chẩn đoán: bị từ chối do các ràng buộc bảo mật chỉ dùng cục bộ (local-only).
- Chỉ lưu trữ các mã băm nội dung nguồn: bị từ chối vì adapter cần một khóa bỏ qua an toàn trực tiếp.

## Quyết Định: Hạn chót (Deadline) áp dụng cho từng lệnh gọi worker RPC trong một nguồn, trong khi CLI cung cấp một ngân sách cho mỗi nguồn

**Lý do**: Giao thức worker đã chấp nhận timeout của RPC. Việc truyền ngân sách nguồn còn lại cho mỗi thao tác stage/embed/commit sẽ giới hạn toàn bộ nguồn thay vì chỉ một nhóm đơn lẻ.

**Các phương án thay thế đã xem xét**:
- Hết thời gian trên toàn bộ tập ngữ liệu: bị từ chối vì không thể cô lập nguồn lỗi hoặc giữ lại điểm khởi động lại hữu ích.
- Thời gian vô hạn: bị từ chối vì sẽ tái diễn tình trạng tiến trình bị treo như trước.

## Quyết Định: Chỉ tiếp tục khi khớp chính xác định danh đóng băng

**Lý do**: Khóa giai đoạn hiện có ràng buộc dấu vân tay ngữ liệu, định danh sản xuất đã kích hoạt và các dấu vân tay nguồn. Việc tái sử dụng một định danh khác có thể làm trộn lẫn bằng chứng từ các ứng viên hoặc ngữ liệu khác nhau.

**Các phương án thay thế đã xem xét**:
- Ghép nối nỗ lực tối đa bằng cách khớp một vài nguồn: bị từ chối vì cổng yêu cầu một định danh thử nghiệm đóng băng.

## Quyết Định: Cho phép chẩn đoán cục bộ mở niêm phong rõ ràng

**Lý do**: Người vận hành đã ủy quyền loại bỏ chốt chặn artifact lịch sử. Việc ghi đè này vẫn bị giới hạn ở BQ01/BQ02, đầu vào chỉ dùng cục bộ và thực thi không có provider, do đó nó chẩn đoán luồng truy xuất đã triển khai mà không đưa ra tuyên bố về khả năng so sánh lịch sử.

**Các phương án thay thế đã xem xét**:
- Tạo lại bằng chứng lịch sử: bị từ chối vì sẽ biểu diễn sai một artifact mới thành bằng chứng cũ.
- Cho phép các câu hỏi tùy ý hoặc tổng hợp trực tiếp: bị từ chối vì sẽ vượt quá phạm vi chẩn đoán được ủy quyền.

