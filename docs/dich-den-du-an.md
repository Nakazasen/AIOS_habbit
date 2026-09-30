# Đích đến dự án AIOS_habbit (ghim 2026-09-30)

Hai lộ trình dưới đây là đích đến đã chốt với user. Mọi vé mới phải đối chiếu vào đây
trước khi phát hành. Trạng thái live từng bước được theo dõi ở tab Goals (Muse),
không ghi trong file này để tránh xung đột.

## 1. Hệ thống điều tra lỗi AIOS — lộ trình Bước 0–5

| Bước | Nội dung | Đầu ra | Điều kiện hoàn thành | Mong muốn | Kì hạn |
|---|---|---|---|---|---|
| 0. Chuẩn hóa dữ liệu | - Gộp KDTPS theo FY về 1 nguồn duy nhất.<br>- Chuẩn hóa trường: Model / Line / Công đoạn / Tên lỗi / Error code / Hiện tượng / Nội dung điều tra / Nguyên nhân / Đối sách / Bộ phận PT / Ngày phát sinh – ngày đóng / Link báo cáo.<br>- Số hóa bảng mã lỗi, thông số thiết kế, sơ đồ mạch điện / báo cáo lỗi hiện có | 1 database duy nhất + từ điển thuật ngữ | ≥90% đủ 5 trường bắt buộc: error code, hiện tượng, nguyên nhân, đối sách, công đoạn | Không còn file rời theo FY; mọi báo cáo mới nhập trực tiếp theo form chuẩn | 28/09/2026 (số hóa: 30/09/2026) |
| 1. Tra cứu lịch sử lỗi tương tự | Tìm kiếm ngữ nghĩa trên database (không chỉ khớp từ khóa) | Nhập error code/hiện tượng → Top 3–5 lỗi tương tự kèm nguyên nhân & đối sách đã áp dụng, có link báo cáo gốc | Chỉ cần nhập error code là ra gợi ý, AI không hỏi ngược lại; mỗi gợi ý phải dẫn được về báo cáo gốc | Thời gian tra cứu ban đầu giảm từ 3 phút xuống dưới <1 phút | 15/10/2026 |
| 2. Vòng phản hồi (feedback loop) | Sau mỗi lần gợi ý, người dùng bấm đánh giá: đúng / sai / một phần. Khi lỗi được đóng, bắt buộc nhập nguyên nhân thật + đối sách thật ngược trở lại kho dữ liệu | Log đánh giá + record được cập nhật kết quả thực tế | Không đóng được phiếu lỗi nếu chưa nhập nguyên nhân thật & đối sách thật; ≥80% lượt gợi ý có đánh giá | Tỉ lệ gợi ý "đúng/một phần" tăng dần theo từng quý (có số đo) | 15/10/2026 |
| 3. Gợi ý hướng điều tra | Nhập hiện tượng → AI sinh cây điều tra theo 4M + Why-Why, kèm hạng mục cần xác nhận và dữ liệu cần thu thập | Checklist điều tra + danh sách dữ liệu/hiện vật cần thu thập | Output khớp đúng format báo cáo điều tra hiện dùng (xuất ra được file để dán thẳng vào báo cáo) | Người mới (G3 trở xuống) tự chạy được bước điều tra đầu tiên mà không cần hỏi người có kinh nghiệm | 15/11/2026 |
| 4. Phân tích dữ liệu & cảnh báo sớm | Phân tích khuynh hướng theo model / line / công đoạn / loại giấy / máy cấp thấp / dữ liệu data từ jig | Biểu đồ xu hướng + cảnh báo tự động (ngưỡng định sẵn) | Tự động sinh báo cáo định kỳ; cảnh báo khi vượt ngưỡng tỉ lệ phát sinh | Bỏ được các thao tác phân tích thủ công đang làm (tỉ lệ phát sinh theo máy cấp thấp, theo loại giấy…) | 15/11/2026 |
| 5. Phân loại tự động + cảnh báo tái phát | Khi nhập lỗi mới, AI tự gán: công đoạn / phân loại nguyên nhân (lắp ráp – thiết kế – linh kiện – khác) / bộ phận phụ trách, rồi đối chiếu lịch sử để cảnh báo "lỗi này đã phát sinh N lần, đã có đối sách X" | Nhãn phân loại tự động + cảnh báo tái phát | Độ chính xác phân loại ≥80% trên tập kiểm tra; 100% lỗi mới được đối chiếu với lịch sử | Phát hiện lỗi tái phát ngay tại thời điểm nhập, không để trôi sang tháng sau | 15/10/2026 |

## 2. Tool phân tích log JIG — kế hoạch công ty

**Mục tiêu cuối cùng:** AI có chức năng phân tích dữ liệu được truyền Realtime từ Sever và
cảnh báo khi dữ liệu có xu hướng dẫn đến phát sinh NG trên công đoạn. Có thể áp dụng
cho nhiều công đoạn.

| Bước | Nội dung | Chi tiết | Kì hạn |
|---|---|---|---|
| 1 | Chuẩn bị chức năng AI (thao tác bằng tay, chưa bàn đến kết nối tự động server và tự động thiết lập ngưỡng cảnh báo) | - Chức năng phân tích dữ liệu JIG từ người dùng đưa vào:<br>  + Có 1 cơ chế cho từng dòng log vào file mà AI phân tích (23/09/2026)<br>  + Có cơ chế nhập cả file csv log jig và cho phép chọn biểu đồ (áp dụng luôn) (15/10/2026)<br>- Chức năng cảnh báo theo ngưỡng do người dùng thiết lập:<br>  + Ví dụ: thiết lập giới hạn trên/dưới của một giá trị thông số được phân tích (23/09/2026)<br>  + Cảnh báo xu hướng<br>  + Thông báo: mail + đính kèm biểu đồ mà AI phân tích<br>  + Tự chọn biểu đồ mà người dùng setup, tự động gửi email đính kèm biểu đồ thông báo đó<br>- Chức năng thu thập dữ liệu, trích xuất nội dung từ người dùng đưa vào (Hoàn thành)<br>- Chức năng nâng cao: mở cổng API (đầu nhận/chuyển thông tin) để khi dữ liệu từ jig đẩy lên server realtime; từ server đẩy về AI Realtime<br>- Chuẩn bị Server:<br>  1. Chuẩn bị sẵn hạ tầng để LOG của JIG đẩy dòng dữ liệu (hoặc cột dữ liệu được yêu cầu) lên server<br>  2. Chuẩn bị cho server đẩy ngược dữ liệu về AI | 23/09/2026 – 15/10/2026 |
| 2 | Xác nhận chức năng đã được tạo ra và chỉnh sửa trước khi đưa cho người dùng thử | Kiểm tra các chức năng đã được triển khai ở Bước 1 | 15/10/2026 |
| 3 | Triển khai dùng thử, thu thập thông tin cải tiến | | 15/11/2026 |
| 4 | Chạy thử nghiệm | Theo dõi độ ổn định và độ chính xác của kết quả cảnh báo | 15/12/2026 |
| 5 | Chạy thật | Đưa hệ thống vào vận hành chính thức; kết nối luồng dữ liệu thực tế, theo dõi cảnh báo và đánh giá định kỳ để tiếp tục tối ưu mô hình | 15/01/2027 |

Ghi chú: "15-Jan" trong kế hoạch gốc được đọc là 15/01/2027 (nối tiếp chuỗi 15/10 → 15/11 → 15/12).
