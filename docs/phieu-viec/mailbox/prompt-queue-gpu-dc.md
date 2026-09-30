# Vé GPU-DC — Nhúng GPU 344 tài liệu "Điều chỉnh" + đóng gói delta cho PC0575

## Vị trí hàng chờ
Chạy SAU khi GPU-262b `xong-cho-duyet`. KHÔNG chạy song song với GPU-262b
(máy i3/16GB — tránh làm chậm nhúng GPU đang chạy).

## Bối cảnh
- User yêu cầu "nhúng nốt" bộ Điều chỉnh sau vụ LSU (rạng sáng 01/10/2026).
- Audit của Muse trên VM: ZIP Drive `Điều chỉnh-20260905T053942Z-1-001.zip`
  (`https://drive.google.com/file/d/1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP/view`,
  858.190.286 byte, SHA-256
  `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7`)
  là superset của cây local (2.147/2.147 file trùng khớp + 54 file nhỏ bên trong
  `log.tar` đã bung).
- Phân loại của Muse (xem `KET-QUA-DOI-CHIEU.md` trên VM):
  - **344 file ĐÁNG NHÚNG** (tài liệu con người đọc được, pipeline trích được):
    231 `.xlsx`, 88 `.pdf`, 8 `.msg`, 6 `.csv`, 5 `.xls`, 3 `.png`, 2 `.bmp`,
    1 `.html` — tổng ~621 MB. Gồm: bảng mã lỗi (`Bang ma loi/`), manual service
    tiếng Nhật 158 MB, biên bản C Call, sơ đồ điện (PDF có text trích được —
    Muse kiểm mẫu `ENGINE_3V2XF47020_03.pdf` có text), file lẻ
    (`Maintenance mode 3.xlsx`, `UWCA…xls`, `SCT…xls`).
  - **1.803 file KHÔNG nhúng**: 1.175 `.gz` + 423 `.log` + 101 `.txt` là log máy
    (bài học vụ CSV tối 30/09 — giá trị hỏi-đáp ≈ 0, để cho track phân tích log
    JIG); 28 `.zip` + 7 `.tar` (+2 `.7z`) là archive lồng nhau; 24 `.wzd` +
    18 `.menu` + `.prg`/`.bin`/`.tcd`/… là định dạng máy chuyên dụng, pipeline
    không trích được.
  - `Loi KDTPS.xlsx` KHÔNG nhúng: đã có trong DB `error_cases` (15.707 ca +
    3.820 mã lỗi qua buoc0-deploy, dùng cho B1-FEAT); nhúng lại ~15k dòng vừa
    trùng lặp vừa tốn ~6–7h GPU ở tốc độ hiện tại.
- Gộp được với index công ty: cùng cơ chế vé GPU-262b — nhúng vào staging riêng,
  đóng gói delta, merge vào production PC0575 bằng cách thêm dòng mới và SKIP
  `document_id` đã tồn tại (không ghi đè, không re-embed).
- Production PC0575 — vé này KHÔNG ĐỤNG tới. Merge là vé khác sau review độc lập.

## Việc cần làm
1. Lấy dữ liệu: file ZIP đã có sẵn trên máy nhà tại
   `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip`
   (user xác nhận 01/10/2026). CHỈ ĐỌC từ ổ D — CẤM ghi ổ D (hỏng vật lý).
   Verify size 858.190.286 byte + SHA-256
   `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7`;
   khớp → giải nén ra ổ C. Không khớp → báo `cho-muse` (phương án dự phòng:
   tải từ Drive `https://drive.google.com/file/d/1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP/view`).
2. Lọc file theo quy tắc: extension (hoa/thường) trong
   {`.xlsx`, `.xls`, `.pdf`, `.msg`, `.png`, `.bmp`, `.html`, `.csv`}
   VÀ tên file khác `Loi KDTPS.xlsx`.
   Báo cáo số file + dung lượng lọc được (kỳ vọng ~344 file / ~621 MB).
   Lệch nhiều → DỪNG, mailbox `cho-muse`, ghi số đo thực tế.
3. Chạy pipeline trích text + chunk ĐÚNG của app (như `export_262`: đúng
   `content_text` + registry + chunker hiện tại — text là chuẩn tuyệt đối,
   KHÔNG trích tay) ra file JSONL (mỗi dòng: `document_id`, `source_name`,
   text chunk). Báo cáo: số `document_id`, tổng chunk, chunk rỗng.
4. Upload JSONL lên Drive, ghi link + size + SHA-256 vào báo cáo để Muse audit
   độc lập (như `text_export.jsonl`).
5. Tạo staging MỚI `C:\AIOS_staging_dc\library.sqlite` (schema y hệt collection
   `tri_thuc`). CẤM ghi production, CẤM ghi staging GPU-262b, CẤM ổ D.
6. Nhúng GPU toàn bộ chunk: BGE-M3 rev `5617a9f`, `onnxruntime==1.28.0`,
   checksum cây onnx máy nhà `sha256:9f81075f…b11093`. Ghi thời gian + tốc độ.
7. Verify (chỉ đọc): đủ `document_id`; fingerprint `016c5255…`; đếm chunk
   retrievable; spot-check cosine GPU/CPU ≥ 0,999 vài chunk mẫu.
8. Đóng gói delta cho PC0575 (zip ra ổ C) + manifest (ghi rõ `document_id` nào
   đã tồn tại trong production để vé merge SKIP).
9. Mailbox → `xong-cho-duyet` + báo cáo `docs/phieu-viec/ket-qua/gpu-dc.md`.
