# VÉ: INFRA-PARITY-DIAG-PC0575 (rà soát hạ tầng vòng lặp tại máy công ty, đối chiếu chuẩn máy nhà) — CHỈ ĐỌC

- Mã vé: `INFRA-PARITY-DIAG-PC0575`
- Role gợi ý: TINY/SMOL (opencode — vai audit, máy công ty KDTVN-PC0575). Việc nhẹ, CHỈ ĐỌC: không cài đặt, không sửa, không clone, không đổi cấu hình. Phát hiện lệch thì ghi vào biên bản, điều phối phát vé nối thông riêng.
- Điều kiện mở vé: máy công ty hoạt động trở lại; được phép chạy sớm bất cứ lúc nào máy rảnh (kể cả trong lúc chờ cổng của vé đo giao diện), theo ghi_chu điều phối 2026-10-12 ~06:50 trong trang-thai.md của hộp thư này.
- Báo cáo (biên bản): `docs/phieu-viec/ket-qua/infra-parity-diag-pc0575.md` — bảng từng hạng mục: chuẩn máy nhà | thực tế PC0575 | lệch | đề xuất vé đóng lệch. Chỉ thao tác trong `D:\Sandbox\AIOS_habbit` và các thư mục hạ tầng nêu dưới đây (đọc).

## Bối cảnh

User lệnh 2026-10-12: trước mọi chuyển giao tính năng, phải rà soát toàn bộ hạ tầng vòng lặp khép kín điều phối ↔ thợ giữa máy công ty và máy nhà, rồi nối thông cho giống nhau về kỹ thuật. Vé này lập biên bản BB-INFRA-PARITY-01 (phần thực tế tại PC0575). Chuẩn máy nhà dưới đây là số liệu điều phối đã kiểm chứng; việc của vé là đo thực tế tại PC0575 cho từng dòng.

## Các hạng mục phải kiểm tại máy (ghi thực tế + bằng chứng: đường dẫn, phiên bản, mã commit, tên tiến trình/task)

1. **Bản sao các kho:**
   - Kho mã `AIOS_habbit` tại `D:\Sandbox\AIOS_habbit`: có mặt? remote đúng `Nakazasen/AIOS_habbit`? HEAD hiện tại (kỳ vọng lệch sau tip chung `05cacc37` — ghi số thực tế, không tự kéo về).
   - Kho điều phối `aios-dieu-phoi`: có thư mục local chưa (chuẩn máy nhà: `D:\Sandbox\aios-dieu-phoi`, vault trỏ vào `so-cai`)? Kỳ vọng CHƯA có — ghi xác nhận vắng mặt.
   - Kho khung watcher `agent-mailbox`: thư mục clone tại máy này tên gì (phía công ty khác tên với `D:\Sandbox\Vong_lap_giao_viec` của máy nhà)? HEAD/tip hiện tại là gì (chuẩn khung mới nhất đã kiểm chứng: `b0612345`, có engine `Watch-Project.ps1` đa project)?
2. **Hộp thư và nhà của chúng:** hai hộp thư pc0575-agy và pc0575-opencode hiện đọc từ kho mã — xác nhận watcher thực tế đang trỏ vào đường nào; bản gieo ở kho điều phối (`hop-thu/mailbox-pc0575-*`) đã có ai đọc chưa (kỳ vọng chưa).
3. **Watcher/picker từng làn:** liệt kê các Windows Scheduled Task + tiến trình watcher đang cài/chạy cho từng làn (agy, opencode); tệp cấu hình watcher dùng (config.local.ps1 hay tương đương) trỏ vào hộp thư nào; vị trí state/registry của watcher nằm trong hay ngoài cây git (chuẩn bắt buộc: NGOÀI cây git). Làn desktop (picker sidecar trong Antigravity) tại máy này: kỳ vọng chưa tồn tại — ghi xác nhận.
4. **Thợ:** agy CLI (có mặt? phiên bản? lệnh gọi watcher dùng?), opencode (có mặt? phiên bản?), Antigravity (đã cài chưa? phiên bản? dấu hiệu đã đăng nhập chưa — chỉ ghi có/không, không thao tác đăng nhập; phần sẵn sàng sâu thuộc vé ANTIGRAVITY-READY-DIAG-PC0575 riêng).
5. **Obsidian:** đã cài chưa (kỳ vọng chưa — vé OBSIDIAN-SETUP-PC0575 xử lý, vé này chỉ ghi trạng thái).
6. **Quyền truy cập GitHub (chỉ đọc):** chạy `git ls-remote` cho cả ba kho `AIOS_habbit`, `aios-dieu-phoi`, `agent-mailbox` — ghi OK/lỗi nguyên văn cho từng kho (đây là lần đầu thử kho điều phối riêng mới từ máy này).
7. **Cấu hình ứng dụng — phần chưa kiểm của BB-CONFIG-PARITY-01:** liệt kê các mục phía PC0575 trong biên bản `so-cai/Bien-ban-sai-khac-cau-hinh-hai-may.md` (đọc từ kho mã hoặc bản sao nếu có) đang ghi chưa kiểm, và kiểm tại máy những mục kiểm được bằng đọc cấu hình (chỉ ghi tên biến/cờ và trạng thái có/không — TUYỆT ĐỐI không ghi giá trị key/bí mật).

## Kỷ luật

- Không thay đổi bất cứ thứ gì trên máy ngoài tệp báo cáo; không chạy việc nặng đồng thời với phiên ứng dụng của user.
- Báo cáo nộp về kho mã tại đường ở trên + lật trạng thái trong trang-thai.md của hộp thư này theo quy ước (khối mới trên cùng).
