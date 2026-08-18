# Tiêu chí Chấp nhận Case Cockpit (Case Cockpit Acceptance Criteria)

## Tiêu chí phiên bản v0.1
- Ứng dụng mở được thông qua trình khởi chạy `.bat`.
- Người dùng có thể tạo một hồ sơ sự vụ (case).
- Người dùng có thể thêm bằng chứng: Excel/CSV, hình ảnh/ảnh chụp màn hình, dán văn bản/log, ghi chú.
- Bản đồ sự vụ (Case Map) hiển thị biểu đồ trực quan hoặc biểu đồ Mermaid kèm bảng dự phòng (fallback table).
- Gợi ý hành động tiếp theo (Next Actions) được tạo tự động từ trạng thái sự vụ.
- Gói Prompt (Prompt Pack) bao gồm bối cảnh, tóm tắt bằng chứng, các điểm chưa rõ/giả thuyết, kết quả đầu ra yêu cầu và chỉ dẫn không bịa đặt sự thật.
- Nội dung bàn giao (Handover) được tạo tự động dưới định dạng Markdown.
- Báo cáo Audit hiển thị bảng ĐẠT/KHÔNG ĐẠT (PASS/FAIL).
- Tính năng an toàn chỉ dùng cục bộ (local-only safety) được hiển thị trực quan và thực thi nghiêm ngặt.

## Tiêu chí phiên bản v0.2
- Chỉnh sửa và sắp xếp dòng thời gian (timeline) tốt hơn.
- Hiển thị đồ thị trực quan tốt hơn với các ký hiệu đánh dấu loại bằng chứng.
- Gợi ý hàng/cột bất thường trong bảng tính Excel.
- Hook OCR tùy chọn, không bắt buộc.
- Gợi ý sự vụ tương đồng cơ bản từ các hồ sơ sự vụ cục bộ đã hoàn thành.

