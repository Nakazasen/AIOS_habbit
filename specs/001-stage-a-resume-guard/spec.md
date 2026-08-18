# Đặc Tả Tính Năng: Chuẩn Bị Giai Đoạn A Có Khả Năng Tiếp Tục (Feature Specification: Resumable Stage A Preparation)

**Nhánh tính năng**: `001-stage-a-resume-guard`

**Ngày tạo**: 2026-08-14

**Trạng thái**: Hoàn thành — đã triển khai và kiểm chứng vào ngày 2026-08-13

**Đầu vào**: Mô tả của người dùng: "Khôi phục các artifact benchmark đã niêm phong nơi có bản sao gốc, sau đó đảm bảo quá trình chuẩn bị Giai đoạn A không có provider của Workspace Chat có khả năng chẩn đoán, tiếp tục và fail-closed trước khi chạy lại BQ01/BQ02."

## Kịch Bản Người Dùng & Kiểm Thử *(Bắt buộc)*

### Câu chuyện người dùng 1 - Tiếp tục một sự chuẩn bị cục bộ bị gián đoạn (Ưu tiên: P1)

Người vận hành đánh giá có thể tiếp tục quá trình chuẩn bị Giai đoạn A bị dừng giữa chừng trên ngữ liệu chỉ dùng cục bộ mà không cần xây dựng lại các nguồn đã commit thành công.

**Lý do ưu tiên**: Quá trình chẩn đoán hiện tại không thể lặp lại an toàn khi một nguồn chậm đơn lẻ buộc phải khởi động lại toàn bộ một cách mờ mịt.

**Kiểm thử độc lập**: Giả lập sự cố sau khi một nguồn được commit, chạy lại với cùng một định danh nguồn đóng băng, và xác minh nguồn đã hoàn thành không bị gửi đi để chuẩn bị lại.

**Kịch bản nghiệm thu**:

1. **Cho trước** một checkpoint chưa hoàn thành khớp với một nguồn đã commit, **Khi** người vận hành chạy lại Giai đoạn A, **Thì** quá trình chuẩn bị tiếp tục tại nguồn tiếp theo và giữ lại nguồn đã commit trước đó.
2. **Cho trước** một checkpoint có định danh ứng viên hoặc ngữ liệu khác biệt, **Khi** người vận hành chạy lại Giai đoạn A, **Thì** nó dừng lại mà không tái sử dụng checkpoint đó.

---

### Câu chuyện người dùng 2 - Xác định và giới hạn nguồn bị đình trệ (Ưu tiên: P2)

Người vận hành đánh giá có thể nhìn thấy tiến trình an toàn theo từng nguồn và nhận được lỗi tất định khi một thao tác chuẩn bị cục bộ vượt quá hạn chót đã khai báo.

**Lý do ưu tiên**: Lượt chạy trước đó đã dừng ở 917 chunks / 757 embeddings mà không có dấu hiệu bền vững nào về nguồn gây lỗi hoặc điểm khởi động lại an toàn.

**Kiểm thử độc lập**: Buộc một lệnh gọi chuẩn bị nguồn vượt quá hạn chót và xác minh checkpoint giữ lại tiến trình đã hoàn thành, ghi lại định danh nguồn mờ an toàn và để giai đoạn ở trạng thái chưa sẵn sàng.

**Kịch bản nghiệm thu**:

1. **Cho trước** một nguồn vượt quá hạn chót chuẩn bị cục bộ đã cấu hình, **Khi** Giai đoạn A xử lý nó, **Thì** nó đóng luồng worker và báo cáo timeout fail-closed mà không đánh dấu giai đoạn là sẵn sàng.
2. **Cho trước** một nguồn hoàn thành, **Khi** commit của nó thành công, **Thì** tiến trình của nó được ghi lại bền vững trước khi nguồn tiếp theo bắt đầu.

---

### Câu chuyện người dùng 3 - Bảo toàn ranh giới chẩn đoán khi không có artifact lịch sử (Ưu tiên: P3)

Người vận hành đánh giá có thể chạy chẩn đoán BQ01/BQ02 cục bộ có phạm vi hẹp khi các artifact lịch sử không khả dụng, trong khi vẫn không thể khởi tạo tuyến provider trực tiếp.

**Lý do ưu tiên**: Các artifact lịch sử không được làm tắc nghẽn việc chẩn đoán runtime cục bộ, nhưng sự vắng mặt của chúng không được làm suy yếu chính sách chỉ dùng cục bộ hoặc mở Giai đoạn B.

**Kiểm thử độc lập**: Chạy luồng chuẩn bị với đầu vào chỉ dùng cục bộ và xác minh nó không để lộ khởi tạo provider, từ chối định danh thiếu hoặc không khớp, và không tạo ra giai đoạn sẵn sàng sau khi timeout.

**Kịch bản nghiệm thu**:

1. **Cho trước** việc thiếu bằng chứng sản xuất đã niêm phong hoặc tham chiếu NotebookLM bất biến, **Khi** người vận hành chọn rõ ràng chẩn đoán mở niêm phong, **Thì** chỉ BQ01/BQ02 được phép chạy cục bộ và kết quả được gắn nhãn chỉ dùng chẩn đoán thay vì so sánh lịch sử.
2. **Cho trước** các nguồn chỉ dùng cục bộ, **Khi** Giai đoạn A được tiếp tục, **Thì** nó vẫn không có provider và Giai đoạn B không được gọi.

### Các Trường Hợp Biên (Edge Cases)

- Checkpoint cũ tuyệt đối không bao giờ được tái sử dụng khi định danh ứng viên, ngữ liệu hoặc manifest nguồn đóng băng của nó thay đổi.
- Một nguồn thất bại không được báo cáo là sẵn sàng chỉ vì các nguồn trước đó đã hoàn thành.
- Các nguồn trống hoặc không chứa văn bản không được tạo ra các bản ghi hoàn thành gây hiểu lầm.
- Quá trình ghi bị gián đoạn phải giữ lại checkpoint hợp lệ trước đó hoặc một bản ghi thay thế hoàn chỉnh, tuyệt đối không để lại bản ghi phân mảnh.

## Yêu Cầu *(Bắt buộc)*

### Yêu cầu chức năng

- **FR-001**: Giai đoạn A BẮT BUỘC lưu tiến trình hoàn thành theo từng nguồn an toàn sau mỗi lần commit cục bộ thành công.
- **FR-002**: Giai đoạn A BẮT BUỘC chỉ tiếp tục từ checkpoint khớp chính xác với định danh ứng viên và nguồn/ngữ liệu đóng băng.
- **FR-003**: Giai đoạn A BẮT BUỘC bỏ qua công việc chuẩn bị đã được ghi nhận là đã commit bởi checkpoint khớp.
- **FR-004**: Giai đoạn A BẮT BUỘC thực thi hạn chót chuẩn bị theo từng nguồn đã khai báo và áp dụng fail-closed khi hết hạn.
- **FR-005**: Một nguồn bị lỗi hoặc timeout BẮT BUỘC để giai đoạn ở trạng thái chưa sẵn sàng và bảo tồn điểm khởi động lại cho các nguồn đã hoàn thành.
- **FR-006**: Bằng chứng tiến trình và lỗi BẮT BUỘC sử dụng các định danh nguồn mờ và TUYỆT ĐỐI KHÔNG lưu trữ văn bản nguồn, tên tệp, credential hoặc phản hồi của provider.
- **FR-007**: Giai đoạn A BẮT BUỘC không có provider cho các nguồn chỉ dùng cục bộ và TUYỆT ĐỐI KHÔNG khởi tạo tổng hợp Giai đoạn B.
- **FR-008**: Việc thiếu bằng chứng sản xuất hoặc các artifact tham chiếu NotebookLM bất biến TUYỆT ĐỐI KHÔNG làm chặn chẩn đoán BQ01/BQ02 chỉ dùng cục bộ được chọn rõ ràng; không có dữ liệu thay thế tự sinh nào được coi là bằng chứng đã niêm phong hoặc so sánh lịch sử.
- **FR-009**: Chẩn đoán mở niêm phong BẮT BUỘC từ chối tổng hợp trực tiếp, nhãn bảo mật không phải cục bộ và bất kỳ lựa chọn câu hỏi nào khác ngoài chính xác BQ01 và BQ02.

### Các Thực Thể Then Chốt

- **Checkpoint chuẩn bị**: Bản ghi bền vững, ràng buộc định danh của một lượt chạy Giai đoạn A, tiến trình an toàn và trạng thái kết thúc của nó.
- **Mục tiến trình nguồn**: Định danh nguồn mờ, vị trí hoàn thành và thời gian hoàn thành cho một nguồn đã commit thành công.
- **Hạn chót chuẩn bị**: Thời lượng tối đa do người vận hành khai báo để xử lý một nguồn trước khi có kết quả fail-closed.

## Tiêu Chí Thành Công *(Bắt buộc)*

### Kết quả có thể đo lường

- **SC-001**: Sự cố gián đoạn giả lập sau 1 trong 3 nguồn sẽ tiếp tục với 0 lệnh gọi chuẩn bị lặp lại cho nguồn đã hoàn thành.
- **SC-002**: Một timeout giả lập tạo ra một giai đoạn chưa sẵn sàng và một checkpoint chứa nguồn hoàn thành cuối cùng trong vòng 1 lượt thử thực thi.
- **SC-003**: Tất cả các bài kiểm thử staging và adapter tập trung đều đạt trong khi chứng minh không có lệnh gọi provider nào được yêu cầu cho Giai đoạn A.
- **SC-004**: Một artifact niêm phong bị thiếu chỉ cho phép một chẩn đoán BQ01/BQ02 cục bộ được gắn nhãn rõ ràng và không bao giờ bị thay thế bởi dữ liệu cục bộ mới được tạo ra.

## Giả Định (Assumptions)

- Lần commit theo từng nguồn của worker có tính lũy thừa (idempotent) đối với định danh nguồn không thay đổi.
- Hạn chót theo từng nguồn có giới hạn do người vận hành cấu hình an toàn hơn việc cho phép thao tác worker cục bộ không giới hạn.
- Các artifact niêm phong ban đầu có thể được khôi phục sau để so sánh lịch sử, nhưng không bắt buộc đối với chẩn đoán BQ01/BQ02 cục bộ rõ ràng.
- Giai đoạn B vẫn nằm ngoài phạm vi một cách rõ ràng và bị khóa.

