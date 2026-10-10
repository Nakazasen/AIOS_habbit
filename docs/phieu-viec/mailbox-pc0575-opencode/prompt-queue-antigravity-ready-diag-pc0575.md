# VÉ: ANTIGRAVITY-READY-DIAG-PC0575 (chẩn đoán sẵn sàng triển khai vòng tự động Antigravity 2.0 tại máy công ty — CHỈ ĐỌC)

- Mã vé: `ANTIGRAVITY-READY-DIAG-PC0575`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575). Việc chẩn đoán nhẹ, chỉ đọc.
- Bối cảnh: vòng khép kín Antigravity đã chạy thật ở máy nhà (bộ nhặt vé bằng sidecar trong app desktop, trần 3 hội thoại, vé DESKTOP-NOTEBOOK-CREATE-HOME đạt nghiệm thu computer use ngày 10/10). Điều phối chuẩn bị đường triển khai ngang sang máy công ty. Vé này CHỈ kiểm tra điều kiện sẵn sàng và báo cáo — không cài đặt, không cấu hình, không đăng nhập hộ bất kỳ thứ gì.

## Việc phải làm (mọi mục đều chỉ đọc, ghi kèm bằng chứng lệnh/đầu ra)

1. **Antigravity**: máy đã cài Antigravity chưa (tìm trong thư mục cài đặt chuẩn, danh sách ứng dụng đã cài, tiến trình nếu đang chạy)? Nếu có: phiên bản bao nhiêu (đọc từ thông tin phiên bản của ứng dụng/tệp thực thi). Trạng thái đăng nhập: app đã đăng nhập tài khoản hay chưa — CHỈ ghi "đã đăng nhập / chưa đăng nhập", tuyệt đối không ghi địa chỉ email, tên tài khoản, token hay bất kỳ thông tin đăng nhập nào khác.
2. **Node cho sidecar**: lệnh `node --version` có chạy được trên máy không (bộ nhặt vé ở máy nhà chạy bằng Node trong môi trường của app)? Nếu không có trên PATH, ghi rõ; đồng thời ghi nhận thư mục cài Antigravity (nếu có) có kèm runtime nào không — chỉ ghi đường dẫn, không chạy thử sidecar.
3. **Chrome**: đã cài Google Chrome chưa, phiên bản bao nhiêu (browser agent của desktop cần Chrome để nghiệm thu giao diện).
4. **Bản clone kho điều phối**: thư mục `D:\Sandbox\aios-dieu-phoi` đã tồn tại trên máy này chưa; nếu có, nó đang ở commit nào (chỉ đọc `git log -1`). Vé OBSIDIAN-SETUP-PC0575 ở hàng chờ trước cũng dùng bản clone này cho vault sổ cái.
5. **Thư mục vận hành agent-mailbox tại máy này**: đường dẫn tương đương thư mục `Vong_lap_giao_viec` ở máy nhà là gì trên máy này (nơi chứa các tệp trông coi hộp thư hiện hành)? Ghi đường dẫn + vài tệp tiêu biểu thấy được (chỉ liệt kê tên).
6. **Tài nguyên máy**: dung lượng trống của ổ chứa `D:\Sandbox`, tổng RAM — để điều phối tính trần hội thoại đồng thời cho máy này.

## Sản phẩm

- Báo cáo: `docs/phieu-viec/ket-qua/antigravity-ready-diag-pc0575.md` — đủ 6 mục, mỗi mục một kết luận rõ ràng dạng "có/không + số liệu", kèm một dòng tổng kết: máy còn thiếu điều kiện nào để triển khai vòng Antigravity.
- Ghi mốc vào `trang-thai.md` của hộp thư này: `dang-lam` khi bắt đầu, `xong-cho-duyet` khi xong.

## Rào cứng

- CHỈ ĐỌC toàn bộ: không cài đặt phần mềm, không sửa cấu hình, không mở ứng dụng Antigravity nếu nó chưa chạy (chỉ kiểm tra tiến trình/tệp), không đăng nhập hay chạm vào thông tin đăng nhập.
- Không đụng chỉ mục production, không merge nhánh.
- Nếu một mục không kiểm tra được, ghi rõ "không kiểm được + lý do", không đoán.
