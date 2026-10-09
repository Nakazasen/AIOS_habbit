# VÉ: NET-DRIVE-PROBE-PC0575 (điều tra tại máy: vì sao đang ở mạng công ty mà vẫn vào được Google Drive)

- Mã vé: `NET-DRIVE-PROBE-PC0575`
- Role gợi ý: DEFAULT (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/net-drive-probe-pc0575.md`
- Bối cảnh: sáng 09/10, người dùng đang ở máy công ty, chưa đổi Wi-Fi sang mạng KT_CHETAO mà vẫn đăng nhập được vào Google Drive. Theo số đo thật ngày 07/10 trên chính máy này, khi ở Wi-Fi mạng công ty `vn-kdwireless` thì lệnh kiểm tra tới `drive.google.com` bị timeout sau 15 giây — tức Drive vốn không tới được từ mạng công ty. Cần số đo tại máy để phân định dứt điểm nguyên nhân, đồng thời kiểm chứng kênh Drive cho vé nhận gói nguồn sắp tới.

## Việc phải làm (toàn bộ là đo và ghi, không sửa cấu hình mạng)

1. **Trạng thái mạng hiện tại:** ghi tên mạng Wi-Fi đang kết nối, địa chỉ cổng mặc định, và danh sách các đường mạng đang hoạt động trên máy (Wi-Fi, dây, khác) — để biết máy đang thực tế đi đường nào.
2. **Kiểm tra đường tới Drive bằng công cụ dòng lệnh:** đo thời gian và kết quả khi truy cập `drive.google.com` (gồm cả phân giải tên miền), ghi nguyên văn kết quả đo.
3. **Thử tải gói nhỏ để kiểm chứng kênh thật:** tải tệp 430.510 byte từ liên kết trực tiếp dưới đây vào một thư mục tạm riêng trên máy, đo thời gian tải, rồi đối chiếu băm SHA-256 — khớp băm là bằng chứng kênh tải thật sự thông:
   - Liên kết: `https://drive.usercontent.google.com/download?id=1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl&export=download&confirm=t`
   - Băm đúng: `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403`
4. **Kiểm tra gói lớn ở mức kết nối:** chỉ kiểm tra phản hồi ban đầu tới liên kết gói 9.153.022 byte (không tải hết): `https://drive.usercontent.google.com/download?id=1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK&export=download&confirm=t`
5. **Phân định phạm vi mở:** thử truy cập một trang ngoài bất kỳ khác (một trang tin quốc tế) và ghi kết quả — để kết luận mạng công ty đang mở ra internet nói chung, chỉ mở riêng Drive, hay trình duyệt đang đi đường riêng trong khi công cụ dòng lệnh bị chặn.
6. **Kết luận trong báo cáo:** trả lời thẳng câu hỏi "vì sao chưa đổi sang KT_CHETAO mà vẫn vào được Drive" bằng đúng số đo đã thu, phân biệt rõ: máy đang thực tế ở mạng nào; việc đăng nhập được là truy cập thật hay chỉ là phiên cũ hiển thị; kênh tải tệp từ Drive hiện thông hay không.

## Rào cứng

- Chỉ đo và ghi: không đổi cấu hình mạng của máy, không nạp tệp tải thử vào ứng dụng hay chỉ mục (tệp để ở thư mục tạm, ghi rõ đường dẫn trong báo cáo). Không chạy việc nặng đồng thời với phần nghiệm thu của thợ chính trên cùng máy. Không ghi chỉ mục. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
