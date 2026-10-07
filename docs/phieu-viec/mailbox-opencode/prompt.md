# VÉ XẾP HÀNG: SRC-421-PROVENANCE-HOME (truy nguồn byte đúng lúc nạp chỉ mục cho 421 mã lệch băm)

- Mã vé: `SRC-421-PROVENANCE-HOME`
- Role gợi ý: DEFAULT (điều tra chỉ-đọc + băm đối chiếu)
- Máy: nhà h410asrock (phần kiểm trên kho Drive do điều phối chỉ định thêm nếu cần)
- Báo cáo: `docs/phieu-viec/ket-qua/src-421-provenance-home.md`
- Căn cứ: báo cáo `src-package-511-home.md` — 421/479 tệp ở gốc canary đã bị **tái vật liệu hoá sau khi dựng chỉ mục** nên byte hiện tại lệch vân tay chỉ mục (danh sách: `docs/phieu-viec/ket-qua/src-package-511-lech.csv`, kèm băm hiện tại + vân tay kỳ vọng từng mã). 90 mã khớp đã đóng gói riêng (vé UPLOAD + vé nhận PC0575 lo phần đó; vé này chỉ lo 421).

## Việc phải làm (CHỈ ĐỌC ở mọi kho ứng viên)

1. Liệt kê các kho ứng viên có thể còn giữ byte đúng lúc nạp cho các tài liệu canary, theo dấu vết thời gian dựng chỉ mục (canary dựng trong đợt chia kho đầu tháng 10): bản sao lưu pre-split ở máy nhà (`D:\Sandbox\AIOS_index_split_backup\...` — kiểm cả cây materialized_sources nếu có), các thư mục `local_runs/` khác ở máy nhà, và mọi vị trí vật liệu hoá cũ còn sót. Ghi rõ từng kho: đường dẫn, thời điểm, căn cứ cho rằng nó có thể chứa bản đúng.
2. Với mỗi kho ứng viên: băm đối chiếu các tệp tương ứng 421 mã (đúng hàm băm byte thô như vé PACKAGE) → đếm bao nhiêu mã tìm được byte khớp vân tay kỳ vọng, liệt kê mã nào kho nào.
3. Kết luận + khuyến nghị theo số liệu: (a) tìm đủ/phần lớn → đề xuất vé đóng gói bổ sung; (b) không kho nào có → đề xuất hướng chấp nhận nạp lại 421 mã từ tệp hiện tại phía máy công ty (kèm hệ quả: phải dựng lại phần chỉ mục của 421 mã đó + kiểm chứng lại vân tay) để điều phối trình user quyết. KHÔNG tự thực hiện hướng nào ở vé này.

## Rào cứng

- Chỉ đọc; không sửa/xoá/di chuyển tệp ở bất cứ kho nào; không ghi index; không merge `main`.
