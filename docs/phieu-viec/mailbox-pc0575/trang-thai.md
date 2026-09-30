# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong`

- `verdict_p5b`: **ĐẠT** (Muse review 2026-09-30 ~11:1x +07 trên VM): điều tra đầy đủ theo vé — mạng `KT_CHETAO` / IP `192.168.1.41` (profile Public); app chạy (PID 1632, HTTP 200 qua 127.0.0.1 và 192.168.1.41, render thật bằng Chromium); nguyên nhân gốc đã xác định: rule firewall **Block inbound** đúng `python.exe` của app trên profile **Public** + 0 rule Allow cho 8501 + default inbound Block → máy khác hiện **không vào được** (kết luận từ bằng chứng cấu hình, đã khai báo trung thực chưa test vật lý 2 thiết bị). Commit báo cáo `f74508f` chỉ thêm file (+91/−0). Không tải model, không embed, không ghi index, không merge `main`.
- Việc còn lại cần người/IT (máy không có quyền admin): chạy mục 5 của `docs/phieu-viec/ket-qua/p5b-mang-moi.md` (PowerShell admin: xóa 2 rule Block python 3.11.15 + thêm rule allow 8501 gồm profile `public`), rồi test 10 giây từ điện thoại cùng Wi-Fi.

Lịch sử: P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
