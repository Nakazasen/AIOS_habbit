# Các Tùy Chọn Trình Kết Xuất Đồ Thị trong AIOS Case Cockpit (Graph Renderer Options)

AIOS Case Cockpit cung cấp nhiều chế độ trực quan hóa cho Bản đồ tri thức dưới Tab 5 (Bản đồ). Các tùy chọn này có thể được chuyển đổi qua menu thả xuống **Kiểu hiển thị**.

## 1. Bản Đồ Thẻ HTML (HTML Card Map)
- **Mục tiêu**: Cung cấp một bảng phân làn theo cột rõ ràng, dễ đọc cho các nút (nodes) được nhóm theo loại thực thể (`system`, `process`, `setting`, v.v.) kèm các thẻ chip quan hệ.
- **Ràng buộc**:
  - HTML thuần túy và CSS nội dòng (inline).
  - Hoàn toàn không dùng thư viện ngoài nặng nề (không React Flow, Cytoscape, hay d3).
  - Không dùng CDN hay bất kỳ phụ thuộc từ xa nào.
  - Nghiêm cấm hoàn toàn mã JavaScript ngoài (`<script>`) hoặc kết nối mạng từ xa (`http://`, `https://`) để bảo đảm an toàn dữ liệu.
  - Escape HTML toàn bộ thuộc tính của nút và quan hệ để ngăn chặn lỗ hổng XSS.
- **Cắt giảm dữ liệu (Truncation)**: Cảnh báo sẽ hiển thị nếu số lượng nút vượt quá 50 hoặc số quan hệ vượt quá 100 nhằm bảo đảm hiệu năng hiển thị.

## 2. Bảng + Mermaid (Table + Mermaid)
- **Mục tiêu**: Cung cấp sơ đồ dựa trên văn bản chuẩn (Mermaid) và các bảng xem chi tiết cho nút cùng cạnh nối để sao chép hoặc đánh giá cấu trúc.
- **Dự phòng (Fallback)**: Hoạt động hoàn toàn cục bộ thông qua trình xem bảng tích hợp sẵn của Streamlit và Markdown mã thô.

