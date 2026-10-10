# VÉ: MAILBOX-MOVE-HOME-OPENCODE (chuyển hộp thư opencode máy nhà sang kho điều phối `aios-dieu-phoi`)

- Mã vé: `MAILBOX-MOVE-HOME-OPENCODE`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy nhà h410asrock). Việc nhẹ, không gọi mô hình nặng.
- Báo cáo: chính là commit xác nhận tại kho mới (xem bước 3) cộng một dòng tổng kết trong báo cáo ngắn `docs/phieu-viec/ket-qua/mailbox-move-home-opencode.md` ở kho dự án.
- Bối cảnh: user đã tạo kho điều phối riêng tư `Nakazasen/aios-dieu-phoi` làm hòm thư điều phối toàn bộ dự án. Sổ cái đã chuyển về đó xong; vé `OBSIDIAN-SETUP-HOME` vừa được duyệt đạt — theo thứ tự đã chốt, hộp thư này chuyển nhà ngay sau vé đó. Bạn đã có sẵn bản clone của kho điều phối tại `D:\Sandbox\aios-dieu-phoi` từ vé cài Obsidian. Giao thức đầy đủ nằm ở tệp `hop-thu/README.md` trong kho mới và phiếu `hop-thu/mailbox-opencode/CHUYEN-NHA.md`.

## Việc phải làm

1. Kéo nhánh `main` mới nhất của kho điều phối tại bản clone `D:\Sandbox\aios-dieu-phoi` (đầu nhánh hiện đã có cả mục sổ cái mới nhất của điều phối). Nếu kéo về bị từ chối quyền truy cập: DỪNG ngay, ghi nguyên văn thông báo lỗi vào `trang-thai.md` của hộp thư này ở kho dự án, đặt trạng thái chờ duyệt kèm điểm gãy — không tự xử lý hay mượn thông tin đăng nhập khác.
2. Đọc lại `hop-thu/README.md` và `hop-thu/mailbox-opencode/CHUYEN-NHA.md` trong bản clone để nắm giao thức. Bản sao hộp thư trong kho mới hiện là bản GIEO chưa hiệu lực — không ghi tiến độ vé nào vào đó ngoài bước xác nhận dưới đây.
3. Ghi xác nhận chuyển nhà: sửa tệp `hop-thu/mailbox-opencode/CHUYEN-NHA.md` trong bản clone — đổi dòng trạng thái chuyển thành **ĐÃ XÁC NHẬN**, thêm vào mục "Ghi chú xác nhận" một dòng gồm: thời gian, tên máy, và cách chương trình trông coi (watcher) của bạn đã được trỏ sang thư mục clone mới (ghi rõ tệp cấu hình hoặc tệp lệnh đã sửa và sửa như thế nào; nếu watcher không tự trỏ lại được thì ghi rõ điểm đó để điều phối xử lý tiếp). Commit thay đổi này và đẩy lên nhánh `main` của kho `aios-dieu-phoi`.
4. Sau khi đẩy thành công: ghi một dòng tổng kết ngắn vào báo cáo ở kho dự án (đường dẫn ở đầu vé) gồm thời gian xác nhận và mã commit xác nhận (mấy ký tự đầu), rồi đặt hộp thư này ở kho dự án sang trạng thái `xong-cho-duyet`. Điều phối sẽ kiểm chứng commit xác nhận từ xa, ghi duyệt (dấu thứ hai) vào phiếu chuyển nhà tại kho mới — từ mốc đó hộp thư này CHỈ vận hành tại kho mới, bản ở kho dự án đóng băng.

## Rào cứng

- Không sửa nội dung nào khác trong kho mới ngoài tệp `hop-thu/mailbox-opencode/CHUYEN-NHA.md`.
- Không xoá, không di chuyển hộp thư ở kho dự án.
- Không merge nhánh nào ở cả hai kho. Không đụng chỉ mục production.
- Kích thước tệp trong báo cáo (nếu có nêu) phải đo trên bản đã nộp vào kho sau khi commit — lưu ý bài học cũ: số đo trên bản ở đĩa Windows (xuống dòng CRLF) luôn lớn hơn bản đã chuẩn hoá trong kho, ghi số trên đĩa là sai.
