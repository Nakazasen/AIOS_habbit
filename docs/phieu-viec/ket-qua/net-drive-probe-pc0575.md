# Báo cáo điều tra tại máy: vì sao ở mạng công ty vẫn vào được Google Drive

- Mã vé: `NET-DRIVE-PROBE-PC0575`
- Máy đo: KDTVN-PC0575 (máy công ty)
- Thời gian đo: 2026-10-09 khoảng 10:50–11:10 giờ Việt Nam
- Người đo: thợ opencode (thợ phụ tạm thời)
- Cách làm: chỉ đo và ghi, không đổi cấu hình mạng, không nạp tệp thử vào ứng dụng hay chỉ mục

## 1. Trạng thái mạng hiện tại

- Tên mạng Wi-Fi đang nối: `vn-kdwireless` (mạng công ty, chưa đổi sang `KT_CHETAO`)
- Chi tiết sóng: băng tần 2,4 GHz, kênh 1, tín hiệu 92%, chuẩn 802.11n, bảo mật WPA2-Enterprise
- Địa chỉ máy: 10.170.157.86, mặt nạ 255.255.255.0, cổng mặc định 10.170.157.254
- Đường mạng đang hoạt động: chỉ có Wi-Fi nối; các cổng dây không có địa chỉ (không cắm)
- Kết luận mục này: máy đang thực tế đi đường mạng công ty

## 2. Đường tới Drive bằng công cụ dòng lệnh

- Phân giải tên miền `drive.google.com` được (máy chủ phân giải nội bộ 10.170.162.12 trả về các địa chỉ 142.250.21.100–139 và dải IPv6 2404:6800:400b:c005::64–8b)
- Truy cập `https://drive.google.com/` bằng curl: hết thời gian chờ sau 20 giây ở bước nối cổng 443 tới 142.250.21.139, không nhận được mã trạng thái nào
- Đối chứng bằng công cụ tải của Python tới cùng địa chỉ: cũng hết thời gian chờ sau khoảng 25 giây ở bước bắt tay bảo mật
- Nguyên văn kết quả curl: đã phân giải xong tên miền, liệt kê đủ 6 địa chỉ IPv4, thử nối địa chỉ đầu tiên rồi báo hết thời gian chờ sau 20011 mili giây và đóng kết nối
- Kết luận mục này: đường tới máy chủ xem Drive bị chặn ở tầng kết nối từ mạng công ty, khớp số đo ngày 07/10 (hết thời gian chờ sau 15 giây)

## 3. Thử tải gói nhỏ để kiểm chứng kênh thật

- Liên kết tải trực tiếp (máy chủ tải tệp, khác máy chủ xem ở mục 2)
- Tệp lưu tại: `C:\Temp\net-drive-probe\small.bin` (thư mục tạm riêng, không nạp vào ứng dụng hay chỉ mục)
- Kết quả: tải xong 430.510 byte trong 3,4 giây
- Đối chiếu băm SHA-256: khớp đúng chuỗi đã biết `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403`
- Kết luận mục này: kênh tải tệp thật sự thông, có bằng chứng băm khớp

## 4. Kiểm tra gói lớn ở mức kết nối (không tải hết)

- Liên kết gói 9.153.022 byte: gửi yêu cầu chỉ lấy phần đầu, máy chủ trả mã 200 sau 5,2 giây, khai đúng độ dài 9153022 và loại tệp `application/octet-stream`
- Yêu cầu lấy thử 1024 byte đầu: máy chủ trả mã 206 sau 1,7 giây, nhận đủ 1024 byte
- Kết luận mục này: kênh gói lớn thông ở mức kết nối, sẵn sàng cho vé nhận gói nguồn sắp tới

## 5. Phạm vi mở của mạng công ty

- Thử mở trang tin quốc tế `https://www.bbc.com/`: thành công mã 200 sau 7,5 giây
- Đối chứng máy chủ tải `https://drive.usercontent.google.com/` (đường dẫn gốc, không mã tệp): máy chủ trả mã 404 sau 0,4 giây — tức đã nối được tới máy chủ, chỉ là đường dẫn gốc không có nội dung
- Không đặt biến môi trường trung gian nào trên máy
- Kết luận mục này: mạng công ty mở ra internet nói chung, không phải chỉ mở riêng Drive; việc chặn ở mục 2 là chặn theo từng máy chủ

## 6. Kết luận: vì sao chưa đổi mạng mà vẫn vào được Drive

- Máy đang thực tế ở mạng công ty `vn-kdwireless`, không phải mạng ngoài
- Việc nhìn thấy Drive trong trình duyệt là hiển thị ở tầng xem (có thể là phiên đăng nhập cũ còn lưu, hoặc đi qua máy chủ khác với máy chủ bị chặn); bằng chứng dòng lệnh cho thấy máy chủ xem `drive.google.com` hiện không nối được từ mạng này
- Kênh tải tệp từ Drive hiện thông: máy chủ tải `drive.usercontent.google.com` nối được, gói nhỏ tải xong khớp băm, gói lớn kiểm tra đầu nối thành công
- Hệ quả cho vé nhận gói nguồn sắp tới: có thể tải gói qua liên kết trực tiếp ngay trên mạng công ty, không cần đổi Wi-Fi; nếu vé nào cần mở trang xem Drive thì mới cần tính đường khác
