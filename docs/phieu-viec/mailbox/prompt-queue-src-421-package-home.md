# VÉ: SRC-421-PACKAGE-HOME (đóng gói 421 tệp HIỆN TẠI ở máy nhà + bản kê vân tay mới, tải qua kênh Drive)

- Mã vé: `SRC-421-PACKAGE-HOME`
- Role gợi ý: DEFAULT (đóng gói + băm + tải)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/src-421-package-home.md`
- Quyết định nền: user chốt 2026-10-08 ~05:54 +07 — xử lý 421 mã lệch băm theo hướng **chép tệp hiện tại sang PC0575 và cập nhật vân tay trong chỉ mục theo bản mới** (không nạp lại, không để nguyên). Căn cứ truy nguồn: báo cáo `src-421-provenance-home.md` (byte gốc lúc nạp đã mất ở mọi kho máy nhà) và danh sách lệch `docs/phieu-viec/ket-qua/src-package-511-lech.csv` (421 dòng).
- Điều kiện tiên quyết: kênh Drive của vé `SRC-PACKAGE-511-UPLOAD-HOME` đã sống (cùng hàng chờ, vé đó chạy trước). Nếu tới lượt mà kênh chưa sống: ghi mốc chờ vào trang-thai và báo, không tự chế đường khác.

## Việc phải làm

1. Theo danh sách 421 mã trong `src-package-511-lech.csv`, xác định tệp hiện tại tương ứng trong kho canary ở máy nhà (đường dẫn đã có trong các báo cáo SRC trước; mã nào không tìm thấy tệp hiện tại thì ghi riêng vào báo cáo — không đoán).
2. Với mỗi tệp: tính SHA-256 của byte hiện tại + kích thước. Lập `manifest-421.csv`: mã, đường dẫn tương đối đích (đường dẫn materialized mà chỉ mục PC0575 đang trỏ tới — lấy từ bản kê/báo cáo SRC trước), kích thước, sha256.
3. Đóng gói: `src-421-current-home.zip` chứa 421 tệp theo cấu trúc đường dẫn tương đối trong manifest + `manifest-421.csv` nằm trong gói. Ghi SHA-256 + kích thước của chính tệp zip vào báo cáo.
4. Tải gói lên thư mục Drive **AIOS_Data** qua kênh đã cài ở vé UPLOAD; kiểm chứng phía Drive (xuất hiện + đúng kích thước).

## Rào cứng

- Chỉ đọc + chép tệp nguồn; không sửa tệp nguồn, không đụng chỉ mục ở máy nhà, không merge `main`.
- Không nén lẫn 421 tệp này vào gói 90 (hai gói tách bạch, hai manifest tách bạch).
