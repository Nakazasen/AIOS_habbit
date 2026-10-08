# VÉ: SRC-DRIVE-WEB-UPLOAD-HOME (tải 2 gói nguồn lên Drive bằng Chrome đã đăng nhập sẵn — đường tiền lệ 01/10)

- Mã vé: `SRC-DRIVE-WEB-UPLOAD-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/src-drive-web-upload-home.md`
- Căn cứ đính chính: vé `SRC-PACKAGE-511-UPLOAD-HOME` sáng 08/10 kết luận "chặn kênh" vì chỉ rà 2 đường (Google Drive cho máy tính — không có; rclone OAuth — cần người bấm). Kết luận đó THIẾU: ngày 01/10 thợ trên chính máy nhà đã tải thành công 2 gói zip (21MB + 74MB) lên đúng thư mục AIOS_Data bằng cách điều khiển cửa sổ Chrome ĐANG ĐĂNG NHẬP SẴN tài khoản Google của user qua UI Automation, kiểm chứng ẩn danh khớp byte + SHA-256 (báo cáo `docs/phieu-viec/ket-qua/upload-delta-drive.md` mục 2–5 — đọc kỹ trước khi làm, có cả ghi chú kỹ thuật DPI/tọa độ). Vé này đi lại đúng đường tiền lệ đó cho 2 gói nhỏ hơn nhiều.

## Việc phải làm

1. **Kiểm gói trước khi tải:** xác nhận 2 tệp tồn tại + khớp băm:
   - Gói 90: `local_runs/src-package-511/src-package-511-home-match90.zip` — 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403`.
   - Gói 421: tệp zip của vé `SRC-421-PACKAGE-HOME` (`src-421-current-home.zip` trong `local_runs` — tra đúng đường dẫn từ báo cáo `src-421-package-home.md`) — 9.153.022 byte, SHA-256 `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5`.
2. **Mở kênh tiền lệ:** mở cửa sổ Chrome chính của user trên máy nhà (profile thường dùng hằng ngày — KHÔNG phải profile antigravity-browser), vào thư mục AIOS_Data (`https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`):
   - Nếu phiên ĐÃ ĐĂNG NHẬP SẴN: tải cả 2 tệp lên bằng UI Automation theo kỹ thuật tiền lệ (nút Mới → Tải tệp lên → hộp thoại Open điền đường dẫn đầy đủ). Chờ xác nhận "Đã tải lên" cho từng tệp.
   - Nếu phiên CHƯA đăng nhập hoặc bị đòi mật khẩu/mã 2 bước: **DỪNG NGAY**, ghi mốc báo đúng điểm gãy này (đây là điểm duy nhất cần người thật), KHÔNG thử đăng nhập thay, KHÔNG mở màn hình chờ bấm để đó.
3. **Quyền + liên kết:** với từng tệp vừa tải: mở hộp thoại Chia sẻ, đặt/kiểm tra quyền "Bất kỳ ai có đường liên kết — Người xem" như tiền lệ, bấm "Sao chép đường liên kết" lấy link thật (cấm tự chế link). Ghi link + file ID vào báo cáo và ghi_chu mailbox.
4. **Kiểm chứng ẩn danh:** dùng curl KHÔNG cookie tải lại từng tệp từ link trực tiếp, đối chiếu byte + SHA-256 phải khớp tuyệt đối băm ở bước 1; xóa bản tải kiểm chứng sau khi băm.

## Rào cứng

- Không cài phần mềm mới (không Google Drive cho máy tính, không rclone), không tạo OAuth mới, không sao chép/xuất cookie hay credential dưới bất kỳ hình thức nào — chỉ thao tác trong phiên Chrome đã đăng nhập sẵn như chính người dùng.
- Chỉ tải đúng 2 tệp ở bước 1 lên đúng thư mục AIOS_Data; không đụng các tệp khác trên Drive.
- Không merge `main`. Mốc tiến độ tối thiểu 15 phút/lần.
- Vé này xong (cả 2 gói lên Drive + kiểm chứng khớp) là điều kiện để điều phối phát hành vé nhận phía PC0575 ngay trong cùng chu kỳ poll.
