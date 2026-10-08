# Báo cáo vé `SRC-PACKAGE-511-HOME` — đóng gói 511 tệp vật liệu hoá từ máy nhà

- Vé: `SRC-PACKAGE-511-HOME` (máy nhà `h410asrock`, máy giữ chỉ mục gốc).
- Đầu vào: `docs/phieu-viec/ket-qua/ban-ke-511.csv` (511 mã + đầu mục) + `docs/phieu-viec/ket-qua/src-sync-pc0575.md` mục 13.
- Nhánh: `phieu-viec/rag-fix1`, không merge `main`.
- Mức hoàn thành: **PARTIAL trung thực** — băm đối chiếu + đóng gói xong (90/511 khớp), **bước tải gói lên Drive còn chờ** (lý do ở mục 5).

## 1. Phương án

Việc này đơn giản (sao chép + băm, chỉ đọc) nên chỉ có một phương án:

- Đọc từng mã trong CSV, tìm tệp `{document_id}.txt` đúng gốc theo `source_path` (nhánh canary `local_runs/workspace_chat_rag_v2_canary/materialized_sources`, nhánh production `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources`).
- Băm SHA-256 đúng hàm `_file_fingerprint` của chương trình (băm byte thô), đối chiếu `source_fingerprint`.
- **Chỉ đóng gói tệp KHỚP băm.** Tệp lệch/thiếu liệt kê riêng, không đoán, không thay thế.
- Không dùng GPU, không ghi chỉ mục, không sửa tệp gốc.

## 2. Kết quả băm đối chiếu (chỉ đọc, Python 3.11.14)

| Kết quả | Số mã | Ghi chú |
|---|---|---|
| Khớp băm | 90 | production 32/32, canary 58/479 |
| Lệch băm | 421 | toàn bộ ở gốc canary |
| Không tìm thấy | 0 | mọi mã đều có tệp đúng gốc, không lạc gốc |
| Tổng | 511 | 500 mã nhiều-mảnh + 11 mã một-mảnh-lệch |

Chi tiết từng mã: tệp `local_runs/src-package-511/verify.csv` (giữ ở máy, không commit).
Danh sách 421 mã lệch kèm băm thực tế + vân tay kỳ vọng: `docs/phieu-viec/ket-qua/src-package-511-lech.csv` (421 dòng + đầu mục).

## 3. Phát hiện chính: gốc canary đã tái vật liệu hoá sau khi dựng chỉ mục

- Vân tay trong CSV khớp từng byte với vân tay chỉ mục production đang lưu (kiểm 3 mẫu: 2 canary + 1 production, cả 3 trùng).
- 32/32 tệp production khớp → gốc production còn nguyên từ lúc dựng chỉ mục.
- 421/479 tệp canary lệch → các tệp này đã được tạo lại (vật liệu hoá lại) sau khi dựng chỉ mục, nội dung đổi.
- Bằng chứng mẫu `wsc-00428f9482636841c4638269`: chỉ mục lưu 5 mảnh với vân tay `20d0bbb6…`, byte tệp hiện tại băm ra `92c0fa7f…`; đầu mảnh 1 trong chỉ mục thiếu cụm đầu mục mà tệp hiện tại có (`P.W.BOARD ASSY FUSER 1.INDEX 2.CHANGE HISTORY 3.FUSER`).
- Hệ quả cho máy công ty: với 421 mã này, byte đúng lúc nạp chỉ mục **không còn ở máy nhà**; chép byte hiện tại sang rồi băm lại sẽ không khớp vân tay kỳ vọng. Cần hướng xử lý riêng (tìm bản đúng lúc nạp, hoặc chấp nhận nạp lại 421 mã này).

## 4. Gói đã đóng (90 tệp khớp)

- Cấu trúc trong gói: thư mục `canary/` (58 tệp) + `production/` (32 tệp) + `manifest.csv` (cột `document_id, duong_dan_tuong_doi, sha256`).
- Tổng byte 90 tệp: 1.681.194. Tệp zip: `local_runs/src-package-511/src-package-511-home-match90.zip` (430.510 byte).
- SHA-256 của tệp zip: `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403`.
- Tệp zip giữ ở máy (thư mục `local_runs/`, không commit theo luật an toàn dữ liệu).

## 5. Bước còn chờ: tải gói lên Drive (ghi trung thực, không báo xong bừa)

- Chưa tải vì phiên làm việc này không có công cụ tải Drive (không có `rclone`, không có thư mục Drive đồng bộ trên máy).
- Cách các vé trước dùng là điều khiển trình duyệt Chrome đang đăng nhập của user bằng tay. Phiên này không làm cách đó vì dễ chiếm cửa sổ, bấm nhầm trong Drive đang đăng nhập của user (nguy cơ mất an toàn dữ liệu, trong khi gói chỉ 430KB).
- Đề xuất: user hoặc Muse tải tệp zip ở đường dẫn mục 4 lên thư mục `AIOS_Data` (giữ nguyên tên tệp), rồi ghi link vào vé nhận phía công ty. Hoặc ra vé upload tiếp theo làm riêng bước này.

## 6. Cổng kho (vé không sửa `src/`/`tests/`)

- `compileall src tests`: sạch.
- `cli audit`: `PASS`.
- `import aios_habit.workspace_chat_app`: thành công.
- Không chạy toàn bộ pytest vì vé không đụng mã nguồn (tiền lệ vé đo `INDEX-PROD-HOME` cũng chỉ chạy 3 cổng này).
- Rào giữ: chỉ đọc tệp nguồn và chỉ mục (mở chỉ mục ở chế độ chỉ đọc), không ghi chỉ mục, không xóa/sửa tệp gốc, không merge `main`, không secret.

## 7. Bổ sung: tải Drive (vé `SRC-PACKAGE-511-UPLOAD-HOME`, máy nhà 2026-10-08 00:41–01:00 +07)

- Kết quả: **CHƯA TẢI** — mọi đường tải đều bị chặn thật sự trong phiên này, không báo xong bừa, không nhờ tải tay trong báo cáo này.
- Xác minh đầu vào: tệp `local_runs/src-package-511/src-package-511-home-match90.zip` đủ 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403` khớp ghim vé.
- Đã thử và bị chặn ở đâu:
  1. `rclone` / Drive đồng bộ: máy không có `rclone`, không có thư mục Drive đồng bộ, không có thông tin OAuth để gọi API — không cài thêm phần mềm theo rào vé.
  2. Đường Chrome UI Automation (đường thành công của vé `onnx-upload-drive` / `upload-delta-drive`, script còn ở `C:\temp\upl*.ps1` + `C:\temp\ui_lib.ps1`): Chrome đang chạy (15 tiến trình, 1 cửa sổ `Chat — Muse`), mạng tới `drive.google.com` thông — nhưng **không đưa Chrome lên trước được**: chạy `upl9_nav_and_menu.ps1` báo `chrome not fg`, chạy `Focus-Chrome` của `ui_lib.ps1` vẫn `foreground hwnd=powershell`, đã lưu ảnh `C:\temp\upl_home_probe.png` làm bằng chứng. Bấm / gõ mù lúc này dễ lạc sang tab trò chuyện của user và Drive đang đăng nhập nên **DỪNG, không click bừa** (đúng rào vé chỉ thêm đúng 1 tệp).
  3. Sao chép cookie Chrome: không làm — Chrome đang chạy nên tệp khóa, bản sao cũng không giải mã được do mã hóa App-Bound (tiền lệ vé `onnx-upload-drive` đã ghi).
- Cổng kho chạy lại trong vé này: `compileall src tests` sạch, `cli audit` PASS, `import workspace_chat_app` thành công; không sửa `src/`/`tests/`, không commit tệp zip, không merge `main`.
- Đề xuất: chạy lại đúng bước tải trong phiên tương tác (màn hình thật, Chrome đưa lên trước được) rồi ghi link tệp trong thư mục `AIOS_Data` (giữ nguyên tên tệp) vào đây; gói đã sẵn ở đường dẫn mục 4.

## 8. Bổ sung: rà soát kênh Drive có sẵn và điểm gãy kỹ thuật (vé `SRC-PACKAGE-511-UPLOAD-HOME` v2, máy nhà 2026-10-08 07:41–07:48 +07)

- **Kết quả nghiệm thu phần tải:** **CHƯA ĐẠT** (do điểm gãy kỹ thuật khách quan — máy nhà không có kênh ổ ảo Drive cục bộ, và không thể xác thực OAuth khi User vắng mặt). Đã hoàn thành 100% việc rà soát và kiểm chứng độc lập theo đúng chỉ đạo của vé.
- **Xác thực đầu vào:** Tệp `local_runs\src-package-511\src-package-511-home-match90.zip` có kích thước 430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403` khớp tuyệt đối với chỉ đạo của vé. Tệp zip được bảo toàn nguyên vẹn tại thư mục `local_runs/`.

### 8.1. Kết quả kiểm tra kênh Drive có sẵn theo Bước 1 của vé

1. **(a) Tiến trình Google Drive cho máy tính (`GoogleDriveFS.exe`):**
   - Không có tiến trình `GoogleDriveFS.exe` nào đang chạy trên hệ thống.
   - Kiểm tra Registry `Uninstall`, Program Files và Services: Không có phần mềm "Google Drive for Desktop" được cài đặt. Thư mục `C:\Program Files\Google\Drive File Stream` chỉ còn tệp tàn dư gỡ cài đặt (`account_export_tool.exe`, `deleteonreboot`), không có bộ nhị phân dịch vụ đồng bộ.
2. **(b) Ổ ảo (`G:`) hoặc thư mục mirror/stream:**
   - Hệ thống chỉ có 3 ổ đĩa logic: `C:`, `D:`, `F:`. Hoàn toàn không có ổ `G:` hay bất kỳ ổ ảo/thư mục stream nào của Google Drive.
3. **Bản chất của biểu tượng "Google Drive" trên Taskbar / khay hệ thống mà User quan sát thấy:**
   - Kiểm tra kỹ các lối tắt và lệnh tiến trình `Win32_Process`:
     - Lối tắt: `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Chrome Apps\Google Drive.lnk` và `C:\Users\Admin\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Google Drive.lnk`.
     - Lệnh chạy: `"C:\Program Files (x86)\Google\Chrome\Application\chrome_proxy.exe" --user-data-dir="C:\Users\Admin\.gemini\antigravity-browser-profile" --profile-directory=Default --app-id=aghbiahbpaijignceidepookljebhfak`.
     - Tiến trình đang chạy thực tế: Chrome process PID 6376.
   - **Kết luận:** Biểu tượng mà User nhìn thấy là **Google Drive Chrome Web App (PWA Shortcut)** mở trên trình duyệt Chrome, KHÔNG PHẢI là ứng dụng Google Drive for Desktop mount ổ đĩa hệ điều hành.
4. **(c) Thư mục `AIOS_Data` qua đường dẫn cục bộ:**
   - Do Drive chỉ tồn tại dưới dạng ứng dụng web trong Chrome, không có điểm mount hệ thống tệp cục bộ (Local File System), nên không có đường dẫn thư mục `G:\...` hay folder đồng bộ để ghi tệp kiểm tra.

### 8.2. Điểm gãy kỹ thuật và tuân thủ rào cứng Bước 2 (User vắng mặt)

- Theo chỉ đạo nền của vé:
  - User đi làm, máy nhà bật nhưng không ai tác động được vào máy.
  - Cấm ghi `cho-cong` chờ user, cấm mở màn hình đăng nhập chờ bấm.
  - Cấm dùng lại đường Chrome UI Automation đã gãy ở mục 7.
  - Thợ không nhận, không ghi, không truyền credential qua mailbox/chat.
- Đánh giá phương án thay thế:
  - Cài mới Google Drive for Desktop (`GoogleDriveSetup.exe`): Yêu cầu người dùng đăng nhập tài khoản Google và bấm cấp quyền OAuth trên trình duyệt tại máy.
  - Cài đặt `rclone` và cấu hình Google Drive remote: Bắt buộc luồng xác thực OAuth 2.0 Web Flow (cần người dùng bấm Allow trên trình duyệt).
  - Không có sẵn file token/refresh-token hay credentials cấu hình trước trên máy.
- Thực hiện đúng chỉ đạo xử lý của vé:
  > *"Nếu gặp một bước thật sự không qua được nếu thiếu tương tác người (vd phiên thợ không thấy ổ đồng bộ và mọi đường lập trình đều gãy): DỪNG, ghi vào báo cáo đúng điểm gãy kỹ thuật + đã thử những đường nào, đặt `xong-cho-duyet` với kết luận CHƯA ĐẠT phần đó để điều phối đổi phương án — không đứng chờ."*

### 8.3. Cổng kiểm soát chất lượng hệ thống

- `compileall src tests`: Sạch 100%, không lỗi cú pháp.
- `cli audit`: Trả về `{"errors": [], "status": "PASS", "warnings": []}`.
- `import aios_habit.workspace_chat_app`: Thành công (`IMPORT_OK`).
- Không sửa mã nguồn trong `src/` và `tests/`, không commit tệp zip vào git, không merge `main`.

### 8.4. Đề xuất điều phối

- Gói zip 90 tệp khớp đã sẵn sàng tại `local_runs\src-package-511\src-package-511-home-match90.zip` (430.510 byte, SHA-256 `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403`).
- Đề xuất điều phối: Khi User có mặt tại máy nhà, cài đặt Google Drive for Desktop hoặc cấp quyền một lần cho rclone (hoặc tải gói 430KB này trực tiếp qua giao diện web Chrome Drive PWA đang mở sẵn).

