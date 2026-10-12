# Báo cáo ANTIGRAVITY-READY-DIAG-PC0575 — chẩn đoán sẵn sàng Antigravity tại KDTVN-PC0575 (chỉ đọc)

- Ngày: 2026-10-12 ~11:00 +07
- Máy: KDTVN-PC0575
- Vé: `ANTIGRAVITY-READY-DIAG-PC0575` (chạy ngay theo lệnh user 10:46, chỉ đọc, không cài đặt, không đăng nhập hộ)
- Kho điều phối tại chỗ: `D:\Sandbox\aios-dieu-phoi` HEAD `cbc26fc` (ghi nhận hiện tại, không clone lại)

## 1. Antigravity: có, đang chạy

- Cài đặt: có. `HKCU Uninstall` ghi `Antigravity 2.22.0` (DisplayVersion 2.22.0) và `Antigravity IDE (User) 2.5.5`.
- Tiến trình đang chạy: 6 tiến trình tên `Antigravity` (PID 320, 5940, 13636, 19760, 25320, 25416) tại thời điểm đo.
- Thư mục dữ liệu: `%APPDATA%\Antigravity` tồn tại (User, Local State, Preferences, logs...), `%LOCALAPPDATA%\Antigravity` có `bin`, `staging`.
- Trạng thái đăng nhập: không kiểm được từ ngoài mà không vi phạm rào (không mở app, không đọc file nhạy cảm). Không ghi email/token/tên tài khoản. Lý do ghi rõ theo rào vé.

Kết luận mục 1: có cài + đang chạy; đăng nhập chưa xác định được bằng cách chỉ đọc ngoài.

## 2. Node cho sidecar: có

- Lệnh `node --version` chạy được: `v24.13.0`.
- Thư mục Antigravity không thấy runtime Node kèm theo (chỉ `bin` + `staging`, `bin` chỉ thấy `rg_embedded`), nhưng Node hệ thống đã có nên sidecar có thể dùng Node hệ thống.

Kết luận mục 2: có Node hệ thống, đủ điều kiện chạy sidecar bằng Node.

## 3. Chrome: có

- `HKCU Uninstall` ghi `Google Chrome 154.0.8037.99`.
- Lệnh `chrome` không có trên PATH (Get-Command không thấy), nhưng bản cài tồn tại theo registry.

Kết luận mục 3: có Chrome, đủ điều kiện nghiệm thu giao diện.

## 4. Bản clone kho điều phối: có

- Thư mục `D:\Sandbox\aios-dieu-phoi` tồn tại, `git log -1` hiện tại: `cbc26fc diem-danh: Antigravity PC0575`.
- Lưu ý: mốc clone nhẹ lúc 10:24 ghi HEAD `efa0acf`; hiện tại đã là `cbc26fc` (kho có commit mới hoặc đã cập nhật tại chỗ sau đó). Ghi nhận hiện trạng, không clone lại theo đúng dặn vé.
- Thư mục `so-cai` tồn tại bên trong.

Kết luận mục 4: có bản clone, đang ở `cbc26fc`, có `so-cai`.

## 5. Thư mục vận hành agent-mailbox tại máy này: `D:\Sandbox\agent-mailbox`

- Tương đương `Vong_lap_giao_viec` ở máy nhà là `D:\Sandbox\agent-mailbox`.
- Vài tệp tiêu biểu thấy được: `Watch-Mailbox.ps1`, `Watchdog-Mailbox.ps1`, `Chuyen-Mang.ps1`, `watcher-mailbox-pc0575-opencode-opencode.log`, `watcher_state-mailbox-pc0575-opencode-opencode.json`, `watcher-mailbox-pc0575-agy-agy.log`, thư mục `pc0575` (bên trong có `sparse_head`).

Kết luận mục 5: có thư mục vận hành, đủ tệp trông coi.

## 6. Tài nguyên máy

- Ổ D: đã dùng 161178927104 byte, còn trống 17274023936 byte (khoảng 16,1 GB).
- Tổng RAM: 17044373504 byte (khoảng 15,9 GB).

Kết luận mục 6: đĩa còn khoảng 16 GB, RAM khoảng 16 GB — điều phối dùng để tính trần hội thoại đồng thời.

## Tổng kết: máy còn thiếu điều kiện nào

- Còn thiếu duy nhất: xác nhận trạng thái đăng nhập Antigravity (cần người có quyền mở app kiểm tra, thợ không tự mở/đăng nhập hộ).
- Các điều kiện còn lại đủ: Antigravity đã cài + đang chạy, Node hệ thống có, Chrome có, bản clone kho điều phối có, thư mục vận hành có, tài nguyên đã đo.

## Rào đã giữ

- Chỉ đọc toàn bộ, không cài đặt, không sửa cấu hình, không mở app Antigravity, không chạm thông tin đăng nhập.
- Không đụng chỉ mục production, không merge nhánh.
- Không đoán mục không kiểm được, đã ghi rõ lý do.
