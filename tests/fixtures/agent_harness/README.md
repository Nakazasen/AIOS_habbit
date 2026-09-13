# Dữ liệu giả lập cho kiểm tra trợ lý thực thi

Toàn bộ tệp trong thư mục này là dữ liệu tự tạo, không mô tả nhà máy, khách hàng hay cá nhân có thật. Chúng chỉ phục vụ G1–G6 của Goal 009.

- `factory_error/`: nhật ký và số liệu đủ để tạo báo cáo có căn cứ, cùng một nguồn thiếu số để kiểm tra không vẽ biểu đồ giả.
- `process_design/`: Guideline hiện hành, Guideline cũ, SOP nháp và biên bản ngữ cảnh để kiểm tra phân loại đạt/lệch/thiếu bằng chứng.
- `code_workspace/`: lỗi Python tối thiểu; kiểm thử ban đầu phải thất bại và có thể sửa trong vùng làm việc tách biệt.

Tệp `factory_error/duong_dan_unicode.json` mô tả đường dẫn có khoảng trắng và dấu tiếng Việt. Kiểm thử tạo đường dẫn đó trong thư mục tạm, vì console Python 3.11 hiện tại không thể in tên thư mục có dấu khi chạy `compileall`.
