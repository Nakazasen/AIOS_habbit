# Đặc Tả: Khắc Phục Lỗi Kiểm Toán 3 Truy Vấn Có Cấu Trúc Excel (Spec: Excel Structured Query Audit 3 Remediation)

## Mục Tiêu (Objective)

Khắc phục các phát hiện về độ chính xác và phạm vi bao phủ còn lại từ Đợt kiểm toán 3 mà không mở rộng bề mặt truy vấn có cấu trúc.

## Yêu Cầu (Requirements)

### 1. Ý định tất cả các trang tính có giới hạn (Bounded all-sheets intent)
- `plan_excel_query()` BẮT BUỘC chỉ nhận diện ý định chọn tất cả các sheet khi `all` là một token chuẩn tắc độc lập hoặc cụm từ chuẩn tắc `tat ca` xuất hiện.
- TUYỆT ĐỐI KHÔNG coi các chuỗi con trong các từ không liên quan (ví dụ `smallest`) là ý định chọn tất cả các sheet.
- Các workbook có cùng lược đồ gây mơ hồ mà không có ý định chọn tất cả sheet hợp lệ hoặc tham chiếu sheet rõ ràng BẮT BUỘC tiếp tục fail-soft với lỗi `ambiguous_sheet_table`.

### 2. Nguồn gốc xuyên sheet không mất mát (Lossless cross-sheet provenance)
- Việc mã hóa nguồn gốc tổng hợp nội bộ TUYỆT ĐỐI KHÔNG sử dụng ký tự phân cách hợp lệ trong tên sheet của Excel.
- Một sheet có tên `East,West` BẮT BUỘC phải chuyển đổi hai chiều (round-trip) thành một bản ghi nguồn gốc duy nhất, không được tách thành hai sheet tự bịa.
- Một phép tổng hợp đa sheet BẮT BUỘC vẫn trả về một `StructuredProvenance` cho mỗi sheet hoặc vùng đóng góp.

### 3. Bao phủ tích hợp Workspace Chat (Workspace Chat integration coverage)
- Bài kiểm thử tích hợp phải thực thi luồng workbook được quản lý thông qua `retrieve_workspace_chat_evidence()` với hai sheet.
- BẮT BUỘC xác nhận header bằng chứng và `location_info` của trích dẫn liệt kê đúng các sheet đóng góp thực tế.

### 4. Chất lượng và vệ sinh mã nguồn (Quality and hygiene)
- Loại bỏ các dòng trống mới thêm vào ở cuối tệp (EOF) trong các tệp kiểm thử bị ảnh hưởng.
- Bảo toàn danh sách cho phép SQL, các giới hạn thực thi có chặn và hành vi fail-soft.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

- `smallest Revenue` không bao giờ chọn tất cả các sheet chỉ vì nó chứa `all`.
- Tên sheet `East,West` được giữ nguyên vẹn trong nguồn gốc tổng hợp.
- Bằng chứng Workspace Chat đa sheet trích dẫn `Sheets: East, West` cho các tên hai sheet bình thường.
- Bộ kiểm thử bị ảnh hưởng mục tiêu đạt, `py_compile` đạt, `git diff --check` sạch sẽ cho các tệp kiểm thử đã chạm và graphify được cập nhật sau khi thay đổi mã.

## Đóng Cổng Khắc Phục (Remediation Closure)

- **Trạng thái:** Đã đóng vào ngày 2026-08-13.
- **Xác thực:** Toàn bộ bộ kiểm thử đạt: `1182 passed in 41.49s`.
- **Phạm vi truy vấn có cấu trúc:** Bộ lập kế hoạch, bộ thực thi SQLite có giới hạn và adapter Workspace Chat đã được kiểm toán với một workbook thực tế đa sheet chứa Unicode, dấu câu, ngày tháng, bộ lọc kết hợp, phép tổng hợp và nguồn gốc xuyên sheet.
- **Bảo mật và giới hạn:** SQL vẫn nằm trong danh sách cho phép và được tham số hóa; giới hạn truy vấn workbook giữ ở mức `max_cells=100000` và `max_rows=50`; các yêu cầu không hỗ trợ / mơ hồ áp dụng fail-soft.
- **Biểu đồ Graphify:** `graphify update .` hoàn thành sau các thay đổi mã. Quá trình quét chỉ bỏ qua các thư mục tự sinh không thể truy cập `pytest_goal_032` và `pytest_goal_033`.

