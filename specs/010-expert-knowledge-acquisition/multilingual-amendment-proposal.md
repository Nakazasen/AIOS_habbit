# Đề xuất sửa luật ngôn ngữ giao diện cho triển khai Nhật Trung (T114)

**Trạng thái**: ĐÃ DUYỆT ngày 2026-09-19. Phạm vi thí điểm luồng phỏng vấn 010, tiếng Việt giữ mặc định.

## 1. Luật hiện tại

- `CONSTITUTION.md` nguyên tắc 6: tiếng Việt dễ hiểu là ngôn ngữ duy nhất trên giao diện, thông báo, lỗi, nhật ký và báo cáo.
- `AGENT_RULES.md` mục 4: cấm câu tiếng Anh làm phương án dự phòng, khóa mã nguồn mở khi thiếu.
- `src/aios_habit/i18n.py`: `SUPPORTED_UI_LOCALES` khóa cứng `("vi",)`, bộ chọn ngôn ngữ trả về tiếng Việt.
- `scripts/check_user_facing_vietnamese.py`: quét đạt nghĩa bề mặt 100% tiếng Việt.
- Thực tế từ điển: tiếng Việt 740 khóa, tiếng Nhật và tiếng Trung mỗi bên 702 khóa, thiếu 38 khóa mỗi bên và toàn bộ khóa mới thêm gần đây chưa có bản dịch.

## 2. Vấn đề

Phỏng vấn chuyên gia sắp triển khai cho xưởng Nhật Bản và Trung Quốc. Người vận hành bên đó không đọc được giao diện tiếng Việt. Giữ luật hiện tại thì họ chỉ nhập liệu mù, sai số tăng và kiểm toán T106 không thể đạt với người không chuyên bản địa.

## 3. Đề xuất sửa

1. Cho phép thêm tiếng Nhật và tiếng Trung làm ngôn ngữ giao diện, thí điểm trước ở luồng phỏng vấn 010 (chọn thư viện, phỏng vấn, kiểm tra bản nháp, đưa vào thư viện).
2. Tiếng Việt giữ mặc định và làm phương án dự phòng khi thiếu khóa, cơ chế dự phòng này đã có sẵn trong hàm dịch.
3. Token kỹ thuật, mã thiết bị và hằng máy đọc giữ nguyên như luật hiện tại, chỉ dịch lời giải thích quanh chúng.
4. Bộ quét ngôn ngữ cập nhật theo danh sách ngôn ngữ được duyệt thay vì mặc định 100% tiếng Việt.
5. Mở rộng ra Workspace Chat và các luồng khác chỉ sau khi luồng phỏng vấn đạt kiểm toán với người bản địa.

## 4. Phạm vi không đụng tới

- Không đổi cách lưu tri thức, quyền riêng tư và kiểm toán của Goal 010.
- Không bật giọng nói Nhật Trung theo, giọng nói vẫn ẩn sau cờ riêng.
- Không dùng câu tiếng Anh làm cầu nối trong giao diện.

## 5. Rủi ro đã thấy

- Dịch thiếu hoặc sai làm người bản địa hiểu lầm thao tác xác nhận và thu hồi.
- Gánh duy trì tăng theo mỗi khóa chữ mới, cần quy tắc dịch ngay khi thêm khóa.
- Chất lượng tìm kiếm trên tài liệu Nhật Trung còn yếu, xem đợt E3 của spec 006, không nên hứa ngang tiếng Việt.
- Kiểm thử giao diện phải chạy theo từng ngôn ngữ, tốn thời gian gấp ba.

## 6. Quyết định cần chủ sở hữu

- Đồng ý hoặc từ chối mở tiếng Nhật và tiếng Trung cho luồng phỏng vấn.
- Nếu đồng ý, chốt có dịch toàn bộ 740 khóa hay chỉ các màn hình phỏng vấn trước.
- Chỉ khi có chữ duyệt mới được code theo đề xuất này.
