# VÉ: SRC-PACKAGE-511-UPLOAD-HOME (v2 — user đã chốt: cài kênh đồng bộ Drive CHÍNH THỨC một lần ở máy nhà, rồi tải gói 90)

- Mã vé: `SRC-PACKAGE-511-UPLOAD-HOME`
- Role gợi ý: DEFAULT (thao tác máy + kiểm chứng)
- Máy: nhà h410asrock
- Báo cáo: bổ sung mục 8 vào `docs/phieu-viec/ket-qua/src-package-511-home.md`
- Quyết định nền: user chốt 2026-10-08 ~05:45 +07 — phương án (a): dùng kênh đồng bộ chính thức ở máy nhà để các gói sau dùng lại; bỏ hướng bấm Chrome UI Automation (đã gãy ở lần thử trước, mục 7 của báo cáo gốc).
- **Cập nhật thực tế 2026-10-08 ~06:15 +07 (user gửi ảnh chụp máy nhà):** Google Drive ĐÃ CÓ SẴN trên máy nhà — đã đăng nhập (giao diện web mở được, thấy thư mục AIOS_Data được chia sẻ; biểu tượng Drive hiện ở khay hệ thống). Vì vậy KHÔNG mặc định cài mới: việc đầu tiên là kiểm tra kênh có sẵn theo bước 1 dưới đây; chỉ khi kênh có sẵn thật sự không dùng được từ phía thợ mới tính cài đặt, và phải nêu rõ lý do kỹ thuật cụ thể trong báo cáo.

## Đối tượng tải

- Tệp: `local_runs\src-package-511\src-package-511-home-match90.zip` trong thư mục dự án máy nhà — 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403` (kiểm lại băm tại máy trước khi tải; lệch thì DỪNG và báo).
- Đích: thư mục Drive **AIOS_Data** (folder id `1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`).

## Việc phải làm

1. **Kiểm tra kênh Drive có sẵn trước tiên:** (a) tiến trình/ứng dụng Google Drive cho máy tính có đang chạy không; (b) ổ ảo (thường là `G:`) hoặc thư mục mirror/stream của Drive có truy cập được từ phiên làm việc của thợ không; (c) thư mục **AIOS_Data** (được chia sẻ với tài khoản này) có thấy và ghi được qua đường đó không — thử bằng một tệp kiểm tra nhỏ rồi xoá tệp kiểm tra. Ghi kết quả từng điểm vào báo cáo. Nếu kênh có sẵn dùng được: đó chính là kênh chính thức cho vé này và các gói sau — ghi rõ đường dẫn cách dùng lại. Nếu không dùng được (vd phiên nền không thấy ổ ảo): nêu đúng điểm gãy, khi đó mới cài Google Drive cho máy tính hoặc rclone OAuth và ghi lý do.
2. **TUYỆT ĐỐI TỰ XOAY — không có điểm chờ người (user chốt 2026-10-08 ~06:56):** user đi làm, máy nhà bật nhưng KHÔNG ai tác động được vào máy. Vé này phải hoàn thành 100% bằng thao tác của thợ (Drive trên máy đã đăng nhập sẵn — xem cập nhật thực tế ở đầu vé). Cấm ghi `cho-cong` chờ user, cấm mở màn hình đăng nhập chờ bấm. Nếu gặp một bước thật sự không qua được nếu thiếu tương tác người (vd phiên thợ không thấy ổ đồng bộ và mọi đường lập trình đều gãy): DỪNG, ghi vào báo cáo đúng điểm gãy kỹ thuật + đã thử những đường nào, đặt `xong-cho-duyet` với kết luận CHƯA ĐẠT phần đó để điều phối đổi phương án — không đứng chờ.
3. **Tải lên:** đưa tệp zip vào thư mục AIOS_Data qua kênh đã xác minh (chép vào thư mục/ổ đồng bộ và chờ đồng bộ xong, hoặc `rclone copy` đúng folder id).
4. **Kiểm chứng phía Drive:** tệp xuất hiện trong AIOS_Data với đúng kích thước 430.510 byte; nếu kênh hỗ trợ đối chiếu băm thì đối chiếu; chụp ảnh hoặc trích danh sách tệp làm bằng chứng trong báo cáo. Ghi rõ thời điểm đồng bộ hoàn tất.

## Rào cứng

- Không di chuyển/xoá tệp zip gốc ở máy nhà; không tải thêm tệp nào khác; không đụng chỉ mục; không merge `main`.
- Không dùng lại đường Chrome UI Automation đã gãy.
- Tài khoản Google dùng để đăng nhập là của user tại máy — thợ không nhận, không ghi, không truyền credential qua mailbox/chat.
