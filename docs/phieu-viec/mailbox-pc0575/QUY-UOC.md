# Quy ước riêng — mailbox KDTVN-PC0575 (thợ OMP)

Quy ước chung của hệ mailbox: xem `docs/phieu-viec/mailbox/QUY-UOC.md`.
File này chỉ ghi phần RIÊNG của máy công ty KDTVN-PC0575.

## Công tắc mạng PC0575 (thợ tự chuyển, KHÔNG gọi user, KHÔNG chờ Muse xác nhận)

- Lệnh: `powershell -ExecutionPolicy Bypass -File "D:\Sandbox\agent-mailbox\Chuyen-Mang.ps1" -Mang ngoai|congty`
  - Không tham số = chỉ xem trạng thái hiện tại.
  - Output: `MANG=<SSID>`, `DRIVE=OK/FAIL`.
- Ý nghĩa:
  - `ngoai` = `KT_CHETAO`: ra được Google Drive, KHÔNG vào được LAN công ty
    (endpoint C-Agent `kdtvn-ai.cmcts.vn` KHÔNG chạy trên mạng này — cấm thử).
  - `congty` = `vn-kdwireless`: vào được LAN/C-Agent, Drive hên xui.
- Áp dụng cho MỌI vé trên PC0575:
  - Vé nào cần tải Drive: thợ TỰ mở đầu bằng `-Mang ngoai`, kiểm output `DRIVE=OK`
    rồi mới tải. `DRIVE=FAIL` thì ghi mốc mailbox và chờ nhịp sau — không tải bừa.
  - Tải xong: chuyển về `-Mang congty` nếu vé tiếp theo cần LAN/C-Agent.
  - Cơ chế này THAY cổng cũ "dừng chờ user chuyển mạng + Muse ghi dòng xác nhận"
    (user chốt 2026-10-07).
