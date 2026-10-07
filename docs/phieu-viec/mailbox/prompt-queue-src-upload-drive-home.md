# VÉ: SRC-PACKAGE-511-UPLOAD-HOME (v2 — user đã chốt: cài kênh đồng bộ Drive CHÍNH THỨC một lần ở máy nhà, rồi tải gói 90)

- Mã vé: `SRC-PACKAGE-511-UPLOAD-HOME`
- Role gợi ý: DEFAULT (thao tác máy + kiểm chứng)
- Máy: nhà h410asrock
- Báo cáo: bổ sung mục 8 vào `docs/phieu-viec/ket-qua/src-package-511-home.md`
- Quyết định nền: user chốt 2026-10-08 ~05:45 +07 — phương án (a): cài kênh đồng bộ chính thức MỘT LẦN ở máy nhà để các gói sau dùng lại; bỏ hướng bấm Chrome UI Automation (đã gãy ở lần thử trước, mục 7 của báo cáo gốc).

## Đối tượng tải

- Tệp: `local_runs\src-package-511\src-package-511-home-match90.zip` trong thư mục dự án máy nhà — 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403` (kiểm lại băm tại máy trước khi tải; lệch thì DỪNG và báo).
- Đích: thư mục Drive **AIOS_Data** (folder id `1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`).

## Việc phải làm

1. **Cài kênh đồng bộ chính thức (một lần):** ưu tiên **Google Drive cho máy tính** (bản chính thức của Google). Nếu bản đó không cài được sạch trên máy này thì dùng **rclone** với cấu hình OAuth riêng. Ghi vào báo cáo: kênh đã chọn + phiên bản + cách thợ các lần sau dùng lại kênh này (đường dẫn thư mục đồng bộ / lệnh rclone mẫu).
2. **Điểm cần người:** bước đăng nhập Google (OAuth) là việc CHỈ user làm được. Chuẩn bị mọi thứ tới đúng bước đó, mở sẵn màn hình đăng nhập, ghi mốc `cho-cong: cho user dang nhap Google tai may nha | han <+24h>` vào trang-thai rồi chờ — không bấm thay, không vòng qua.
3. **Tải lên:** đưa tệp zip vào thư mục AIOS_Data qua kênh vừa cài (chép vào thư mục đồng bộ và chờ đồng bộ xong, hoặc `rclone copy` đúng folder id).
4. **Kiểm chứng phía Drive:** tệp xuất hiện trong AIOS_Data với đúng kích thước 430.510 byte; nếu kênh hỗ trợ đối chiếu băm thì đối chiếu; chụp ảnh hoặc trích danh sách tệp làm bằng chứng trong báo cáo. Ghi rõ thời điểm đồng bộ hoàn tất.

## Rào cứng

- Không di chuyển/xoá tệp zip gốc ở máy nhà; không tải thêm tệp nào khác; không đụng chỉ mục; không merge `main`.
- Không dùng lại đường Chrome UI Automation đã gãy.
- Tài khoản Google dùng để đăng nhập là của user tại máy — thợ không nhận, không ghi, không truyền credential qua mailbox/chat.
