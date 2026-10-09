# VÉ: NOTEBOOK-OPEN-DIAG-PC0575 (chẩn đoán việc mở sổ vụ việc Điều tra lỗi bị trắng kéo dài)

- Mã vé: `NOTEBOOK-OPEN-DIAG-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/notebook-open-diag-pc0575.md`
- Bối cảnh: lúc 21:24 ngày 09/10, người dùng mở trực tiếp sổ vụ việc Điều tra lỗi LSU (mã sổ `NB-E35A7BEE`) tại máy công ty — trang hiện khung và tiêu đề sổ nhưng vùng nội dung trắng kéo dài nhiều phút không dựng xong. Các số đo mở sổ hiện có (mở lạnh khoảng 3 giây sau vé `APP-OPEN-DIAG-PC0575`) chỉ đo trên đường sổ tri thức trong chỉ mục; đường mở sổ vụ việc (dữ liệu vụ việc lưu tại máy, sổ này có 9 cuộc trò chuyện) chưa từng được đo phân rã riêng. Vé này khép khoảng trống đó.

## Việc phải làm

1. Đo phân rã đường mở sổ vụ việc trên chính sổ Điều tra lỗi LSU thật: từ lúc chọn sổ tới khi gõ được câu hỏi trong sổ, tách rõ từng khâu (nạp dữ liệu sổ, nạp lịch sử các cuộc trò chuyện, khâu liên quan tới trạng thái chỉ mục nếu có, khâu dựng giao diện). Đo cả lượt lạnh (khởi động lại ứng dụng trước) và lượt ấm, ghi số giây từng khâu vào báo cáo kèm tệp dữ kiện đo.
2. Xác định khâu ngốn thời gian nhất và sửa gốc nếu nguyên nhân nằm trong mã nguồn. Mọi thay đổi phải có kiểm thử bảo vệ và khả năng hoàn lui; không thay đổi định dạng dữ liệu sổ.
3. Nghiệm thu dùng thật sau sửa: mở sổ Điều tra lỗi LSU lạnh và ấm bằng thao tác thật, nộp số đo và ảnh trong đó nội dung sổ đã dựng xong và ô nhập câu hỏi sẵn sàng. Ghi rõ mã commit đang chạy.

## Rào cứng

- Dữ liệu sổ vụ việc là dữ liệu thật của người dùng tại máy: chỉ đọc trong lúc đo; nếu bắt buộc phải đụng tới thì sao lưu nguyên vẹn trước và ghi rõ đường dẫn bản sao lưu trong báo cáo. Không ghi vào chỉ mục chính.
- Không chạy phiên đo đồng thời với phiên ứng dụng của người dùng (lệnh khẩn của điều phối): nếu người dùng đang dùng ứng dụng thì ghi mốc chờ, không đo.
- Mốc tiến độ tối thiểu 15 phút/lần.
