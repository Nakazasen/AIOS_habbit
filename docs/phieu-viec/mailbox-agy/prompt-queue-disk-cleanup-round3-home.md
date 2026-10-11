# VÉ: DISK-CLEANUP-ROUND3-HOME (quét dọn định kỳ máy nhà — vòng 3)

- Mã vé: `DISK-CLEANUP-ROUND3-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/disk-cleanup-round3-home.md`
- Điều kiện bốc: ngay (vé `CSV-STRUCTURED-LANE-FIX-HOME` đã verdict ĐẠT).

## Việc 0 (bắt buộc, làm trước việc chính): bổ sung bằng chứng ảnh của vé LANE-FIX

Hai ảnh `ui-csv-structured-lane-04-q0824.png` và `ui-csv-structured-lane-05-q0668.png` của vé trước chụp lệch khung (thân đáp án nằm ngoài vùng chụp, chỉ thấy dòng trạng thái + khung soạn). Chụp lại hai ảnh này trong một phiên giao diện thật (khối `lsu`, hai câu Q0824 + Q0668) sao cho **trọn thân đáp án nằm trong khung hình**, ghi đè đúng hai tên tệp trên, commit kèm ghi chú đầu tiên của vé này. Nội dung đáp án không đổi (điều phối đã kiểm chứng bằng tệp văn bản đáp án + tự tính lại) — đây thuần tuý là sửa khung hình bằng chứng.

## Việc chính: quét dọn theo cơ chế đã chốt (user quyết 2026-10-10 ~16:21)

Chuỗi sửa dữ liệu missing5 đã khép (BLOCK-FIX + LANE-FIX đều verdict xong) nên phần giữ staging của chuỗi đó hết hiệu lực. Quét các hạng mục sau, mọi hạng mục đều phải qua đủ cổng kiểm: **tuổi tệp đủ cũ, không tiến trình nào đang tham chiếu, không thuộc danh sách loại trừ**:

1. Phần còn lại của staging missing5 trong `C:\tmp` (chẩn đoán trước dặn giữ cho tới khi chuỗi sửa khép — nay đã khép).
2. `C:\tmp\file_attach_test\` (dữ kiện kiểm thử của vé FILE-ATTACH đã khép).
3. Bộ nhớ đệm npm (`npm-cache`) nếu đã qua cổng tuổi 24 giờ.
4. Tàn dư cục bộ của các lượt nghiệm thu computer use mà gói của chúng **đã xác nhận có trên Drive** (thư mục kho `AIOS - Nghiem thu Computer Use / May nha - h410asrock`) — chỉ xoá bản tạm/staging ngoài cây git; tệp trong clone kho điều phối/kho mã là cơ chế vận chuyển, giữ nguyên.

## Loại trừ tuyệt đối (không đụng)

- Cây production `C:\AIOS_workspace_chat_rag_v2_production` và mọi `library.sqlite` + các tệp sao lưu `*.bak-*` của chỉ mục.
- Thư mục làm việc của các vé đang chạy và cây git của hai kho.
- Mọi mục user từng dặn giữ (kiểm tra lại sổ cái/báo cáo các vòng dọn trước nếu không chắc).

## Nghiệm thu

- Báo cáo liệt kê từng hạng mục: đường dẫn, dung lượng trước, cổng kiểm đã qua (tuổi, tiến trình tham chiếu), dung lượng thu hồi; tổng dung lượng ổ C: trống trước và sau (mốc đối chiếu gần nhất đã kiểm chứng: 24,742 GB trống sau vòng 2).
- Không xoá hạng mục nào không qua đủ cổng — ghi rõ hạng mục bị giữ lại và lý do.
- Đây là vé dọn dẹp: không sửa mã, không đụng hộp thư/vé khác.
