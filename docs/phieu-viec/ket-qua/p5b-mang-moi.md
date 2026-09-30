# P5b — Kiểm tra lại truy cập app trên mạng mới (KDTVN-PC0575)

- Ngày: 2026-09-30 ~10:55–11:10 (+07, giờ máy `KDTVN-PC0575`)
- Repo: `D:\Sandbox\AIOS_habbit`, nhánh `phieu-viec/rag-fix1` (HEAD khi nhận vé: `3c44002`)
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (`p5b-kiem-tra-mang-moi`; watcher tự mở OMP lần 1/4 lúc 10:55:04)
- Kết luận: app **vẫn chạy tốt** trên mạng mới (`192.168.1.41:8501`), nhưng **máy khác trong mạng hiện không vào được**: Windows Firewall đang **chặn (Block) inbound cho đúng tiến trình python của app trên profile Public** (mạng mới bị Windows xếp loại Public) và không có rule mở cổng 8501. Máy không có quyền admin nên không thể sửa — cần người/IT chạy mục 5.
- Lưu ý độ tin cậy: kết luận "máy khác bị chặn" là **kết luận từ bằng chứng cấu hình firewall** (rule + mặc định inbound), không phải test vật lý hai thiết bị — phiên OMP chạy trên chính máy này nên không có thiết bị thứ hai. Cách test nhanh 10 giây nằm ở mục 5.4.

## 1. Mạng hiện tại (bước 1 của vé)

| Hạng mục | Giá trị đo được |
|---|---|
| Wi-Fi | SSID `KT_CHETAO` (Intel Wireless-AC 9560, WPA2-Personal, 2,4 GHz, RSSI −69 dBm) |
| IPv4 | `192.168.1.41/24`, gateway `192.168.1.1` (ping 2 ms) |
| Phân loại mạng | **Public** (`Get-NetConnectionProfile`) → firewall áp profile **Public** |
| Adapter khác | Ethernet / Ethernet 3 / Ethernet 4 + 2 WLAN ảo đều `169.254.x` (APIPA, không có mạng) |

Ghi chú: `192.168.1.41` **trùng địa chỉ đã ghi trong báo cáo P5** (mạng cũ) — DHCP của mạng mới cấp lại đúng subnet `192.168.1.x` và host `.41`, nên giả định "IP đổi" trong prompt không xảy ra trên thực tế. ARP thấy gateway MAC `98-4a-6b-5e-43-b7` (kèm địa chỉ phụ `10.170.157.254` cùng MAC — cùng một thiết bị mạng).

## 2. App còn chạy (bước 2) — ĐẠT, không cần khởi động lại

- `netstat`: `TCP 0.0.0.0:8501 LISTENING` PID **1632**.
- PID 1632 chạy ảnh `...\uv\python\cpython-3.11-windows-x86_64-none\python.exe` (thư mục này là **junction** trỏ về `cpython-3.11.15-windows-x86_64-none`); PID 15864 là tiến trình cha `D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe` (theo báo cáo P5: mở bằng `scratch\p5_run_lan.ps1`).
- HTTP: `http://127.0.0.1:8501/` → **200**; `http://192.168.1.41:8501/` → **200**.
- **Trình duyệt thật** (Chromium do OMP điều khiển, thử cả 2 URL): render đủ màn hình đầu — "AIOS Workspace Chat / Chọn hoặc tạo sổ tài liệu để bắt đầu", tab title "Hỏi tài liệu"; không lỗi. Ảnh chụp lưu phiên: `scratch\p5b-localhost-8501.png` (scratch bị git-ignore, không commit).

## 3. Vì sao máy khác chưa vào được (bước 3–4) — nguyên nhân gốc

Test vật lý hai thiết bị không thực hiện được từ phiên tự động này; thay bằng bằng chứng cấu hình firewall của máy (đọc trực tiếp registry `FirewallRules` + `Get-NetFirewall*`):

1. Rule đang bật, chặn **đúng chương trình** đang giữ cổng 8501:
   - `TCP Query User{C91566E5-0DE5-4C63-83E0-732F2DD184A2}…`: `Dir=In`, `Action=Block`, `Protocol=6 (TCP)`, `Profile=Public`, `Active=TRUE`,
     `App=C:\users\tvn183660\appdata\roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe` — đúng đường dẫn thật của tiến trình app (đã kiểm junction 3.11 → 3.11.15).
   - Kèm rule UDP tương ứng; ngoài ra còn các rule Block python 3.12.13/3.11.15 ở profile Domain và python313 (Domain) — không áp cho mạng hiện tại nhưng là dạng rule Windows tự tạo từ hộp thoại "cho phép truy cập" (người dùng không bấm Allow).
2. Quét **toàn bộ** rule trong registry: **0 rule** chứa cổng `8501`; **0 rule Allow nào cho python** (mọi rule python đều là Block).
3. `DefaultInboundAction` cả 3 profile: chưa cấu hình → mặc định Windows = **Block inbound**. Không có rule Allow nào khớp ⇒ gói tin từ máy khác bị chặn.
4. Windows Firewall: **rule Block thắng rule Allow** khi cùng khớp ⇒ muốn mở phải xử lý rule Block trước (mục 5.2).

⇒ Trong trạng thái hiện tại, từ điện thoại/máy đồng nghiệp cùng mạng, `http://192.168.1.41:8501` sẽ **không mở được** (điển hình: timeout / "không truy cập được"). Đây là firewall của máy PC0575 chặn — **không phải lỗi app**.

So với P5: mạng cũ cũng bị chặn nhưng chưa xác định được rule cụ thể; lần này xác định được **đúng rule Block theo chương trình**, và phát hiện thêm điểm quan trọng: lệnh gợi ý ở P5 (`profile=domain,private`) **không đủ** vì mạng mới bị xếp loại **Public**.

## 4. Phạm vi đã kiểm (không thay đổi gì)

- Không tải model, không embed, không ghi/sửa index production, không mở app mới (app cũ đang chạy từ P5).
- Không tắt/đổi rule firewall; không đổi cấu hình mạng; không cài gì (không có quyền admin).
- Không merge `main`; chỉ commit trên nhánh `phieu-viec/rag-fix1`.

## 5. Việc cần người/IT làm (máy không có quyền admin)

5.1. Đã kiểm `IsInRole(Administrator) = False` → các lệnh dưới cần PowerShell **Run as Administrator**.

5.2. Xóa 2 rule Block theo chương trình cho python 3.11.15 (TCP + UDP):
```powershell
Get-NetFirewallRule -Direction Inbound -Action Block |
  Get-NetFirewallApplicationFilter | Where-Object Program -like '*uv*'
# nếu đúng 2 rule {C91566E5…} (TCP) và {768186E8…} (UDP):
Remove-NetFirewallRule -Name '{C91566E5-0DE5-4C63-83E0-732F2DD184A2}'
Remove-NetFirewallRule -Name '{768186E8-0F0C-480B-A71B-FD0DF2B53618}'
```

5.3. Thêm rule mở cổng cho app — **phải gồm profile `public`** (khác lệnh cũ ở P5):
```powershell
netsh advfirewall firewall add rule name="AIOS Workspace Chat 8501" dir=in action=allow protocol=TCP localport=8501 profile=public,private,domain
```
(muốn giới hạn trong LAN: thêm `remoteip=localsubnet`)

5.4. Kiểm lại từ điện thoại (cùng Wi-Fi `KT_CHETAO`): mở `http://192.168.1.41:8501` → vào được thì chụp màn hình; vẫn không được thì ghi nguyên văn thông báo lỗi.
- Phương án thay thế (khuyến nghị nếu IT cho phép): đổi phân loại Wi-Fi sang Private — `Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private` (cần admin) — rồi làm 5.2 + 5.3.

## 6. Link truy cập (theo vé)

- Trang chọn sổ: `http://192.168.1.41:8501/`
- Vào thẳng sổ "Điều tra lỗi LSU": `http://192.168.1.41:8501/?nb=NB-E35A7BEE&conv=CONV-9C730D76` (như P5)

Hiện các link này chỉ mở được **trên chính máy PC0575**; từ máy khác cần mục 5.2–5.4.

## 7. Tệp sinh trong phiên (git-ignored, không commit)

`scratch\p5b_probe.ps1`, `scratch\p5b_fw_registry.ps1`, `scratch\p5b_fw2.ps1`, `scratch\p5b_fw3.ps1` (dò tiến trình + đọc rule firewall), `scratch\p5b-localhost-8501.png` (ảnh app render trên máy).

## 8. Commit của vé

- `4ffbd59` — nhận vé, `trang-thai.md` → `dang-lam`
- `4ac7835` — mốc 1–2 (mạng + app + kết quả firewall)
- commit kế tiếp — báo cáo này + `xong-cho-duyet`

## 9. Còn treo cho vé sau (không thuộc P5b)

- Mở firewall cần admin (mục 5) — nếu user muốn "cả phòng dùng" thì cần vé/việc này.
- Nhắc lại từ P5: 171 nguồn của sổ "Điều tra lỗi LSU" chưa có vector (embed) và sổ "MOM / Opcenter" sẽ tự embed khi mở — vẫn chờ Muse/user quyết.
