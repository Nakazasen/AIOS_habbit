# VÉ: SRC-PACKAGE-511-UPLOAD-HOME (tải gói 90 tệp đã đóng lên Drive + ghi link cho vé nhận)

- Mã vé: `SRC-PACKAGE-511-UPLOAD-HOME`
- Role gợi ý: SMOL/TINY (việc ngắn, một thao tác tải lên + kiểm chứng)
- Máy: nhà h410asrock
- Báo cáo: bổ sung mục vào `docs/phieu-viec/ket-qua/src-package-511-home.md` (mục "Bổ sung: tải Drive")
- Đầu vào (đã có sẵn ở máy nhà, từ vé `SRC-PACKAGE-511-HOME`): tệp `local_runs/src-package-511/src-package-511-home-match90.zip` — 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403`, kèm `manifest.csv` trong gói (90 tệp khớp băm: 58 canary + 32 production).

## Việc phải làm

1. Tải tệp zip lên thư mục **AIOS_Data** trên Google Drive (folder id `1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`), giữ nguyên tên tệp. Dùng đường tải mà các vé trước trên máy này đã dùng thành công (kiểm mailbox/tra cứu cách làm cũ trong repo trước khi thử cách mới); thao tác cẩn thận trong Drive đang đăng nhập — chỉ thêm đúng 1 tệp, không di chuyển/xoá/đổi tên bất cứ thứ gì khác.
2. Kiểm chứng sau tải: tệp xuất hiện trong thư mục với đúng tên + đúng kích thước 430.510 byte; ghi **link tệp Drive** vào mục bổ sung của báo cáo.
3. Nếu mọi đường tải đều bị chặn thật sự: ghi rõ đã thử những đường nào, chặn ở đâu — không báo xong bừa, không nhờ user tải tay.

## Rào cứng

- Chỉ tải lên, không sửa/xoá dữ liệu Drive hiện có; không commit tệp zip vào git; không merge `main`.
