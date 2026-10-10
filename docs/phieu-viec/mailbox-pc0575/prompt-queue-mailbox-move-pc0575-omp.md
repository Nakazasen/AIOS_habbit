# VÉ: MAILBOX-MOVE-PC0575-OMP (chuyển hộp thư OMP máy công ty sang kho điều phối `aios-dieu-phoi`)

- Mã vé: `MAILBOX-MOVE-PC0575-OMP`
- Role gợi ý: TINY/SMOL (OMP — thợ phụ, máy công ty KDTVN-PC0575). Việc nhẹ, không gọi mô hình nặng. Đây là hộp thư đầu tiên phía máy công ty chuyển nhà — chỉ thực hiện khi máy hoạt động trở lại. Chỉ thao tác trong `D:\Sandbox` theo quy ước của máy này.
- Báo cáo: chính là commit xác nhận tại kho mới (xem bước 3) cộng một dòng tổng kết trong báo cáo ngắn `docs/phieu-viec/ket-qua/mailbox-move-pc0575-omp.md` ở kho dự án.
- Bối cảnh: user đã tạo kho điều phối riêng tư `Nakazasen/aios-dieu-phoi` làm hòm thư điều phối toàn bộ dự án. Sổ cái đã chuyển về đó xong. Đợt này chuyển lần lượt từng hộp thư thợ; giao thức đầy đủ nằm ở tệp `hop-thu/README.md` trong kho mới (đọc được sau bước 1) và phiếu `hop-thu/mailbox-pc0575/CHUYEN-NHA.md`.

## Việc phải làm

1. Clone kho điều phối `https://github.com/Nakazasen/aios-dieu-phoi.git` về `D:\Sandbox\aios-dieu-phoi` (nếu đã clone thì kéo nhánh `main` mới nhất). Nếu clone bị từ chối quyền truy cập: DỪNG ngay, ghi nguyên văn thông báo lỗi vào `trang-thai.md` của hộp thư này ở kho dự án, đặt trạng thái chờ duyệt kèm điểm gãy — không tự xử lý hay mượn thông tin đăng nhập khác.
2. Đọc `hop-thu/README.md` và `hop-thu/mailbox-pc0575/CHUYEN-NHA.md` trong bản clone để nắm giao thức. Bản sao hộp thư trong kho mới hiện là bản GIEO chưa hiệu lực — không ghi tiến độ vé nào vào đó ngoài bước xác nhận dưới đây.
3. Ghi xác nhận chuyển nhà: sửa tệp `hop-thu/mailbox-pc0575/CHUYEN-NHA.md` trong bản clone — đổi dòng trạng thái chuyển thành **ĐÃ XÁC NHẬN**, thêm vào mục "Ghi chú xác nhận" một dòng gồm: thời gian, tên máy, và cách chương trình trông coi (watcher) của bạn đã được trỏ sang thư mục clone mới (ghi rõ tệp cấu hình hoặc tệp lệnh đã sửa và sửa như thế nào; nếu watcher không tự trỏ lại được thì ghi rõ điểm đó để điều phối xử lý tiếp). Commit thay đổi này và đẩy lên nhánh `main` của kho `aios-dieu-phoi`.
4. Sau khi đẩy thành công: ghi một dòng tổng kết ngắn vào báo cáo ở kho dự án (đường dẫn ở đầu vé) gồm thời gian xác nhận và mã commit xác nhận (mấy ký tự đầu), rồi đặt hộp thư này ở kho dự án sang trạng thái `xong-cho-duyet`. Điều phối sẽ kiểm chứng commit xác nhận từ xa, ghi duyệt (dấu thứ hai) vào phiếu chuyển nhà tại kho mới — từ mốc đó hộp thư này CHỈ vận hành tại kho mới, bản ở kho dự án đóng băng.

## Rào cứng

- Không sửa nội dung nào khác trong kho mới ngoài tệp `hop-thu/mailbox-pc0575/CHUYEN-NHA.md`.
- Không xoá, không di chuyển hộp thư ở kho dự án.
- Không merge nhánh nào ở cả hai kho. Không đụng chỉ mục production. Không chạy việc nặng đồng thời với phiên ứng dụng của user trên máy.
