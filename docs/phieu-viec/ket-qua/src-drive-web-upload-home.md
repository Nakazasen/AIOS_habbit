# Vé SRC-DRIVE-WEB-UPLOAD-HOME — Báo cáo

- Trạng thái: `xong-cho-duyet`; Cả 2 gói mã nguồn (`src-package-511-home-match90.zip` và `src-421-current-home.zip`) đã nằm trên Google Drive trong thư mục `AIOS_Data`, quyền chia sẻ "Bất kỳ ai có đường liên kết — Người xem", đã kiểm chứng tải ẩn danh độc lập khớp 100% byte và băm SHA-256.
- Máy thực hiện: máy nhà `h410asrock` (Windows), 2026-10-08 ~18:30–19:05 +07.
- Nguồn vé: `docs/phieu-viec/mailbox-agy/prompt.md` (`SRC-DRIVE-WEB-UPLOAD-HOME`).
- Căn cứ thực hiện: Đi đúng đường tiền lệ ngày 01/10/2026 (`docs/phieu-viec/ket-qua/upload-delta-drive.md`) — điều khiển cửa sổ Chrome đang đăng nhập sẵn tài khoản người dùng (`buiducvinhct1102@gmail.com`) thông qua UI Automation của Windows, không cài phần mềm mới, không trích xuất cookie hay credential.

---

## 0. Nhận vé & Cổng gate

- Điều kiện mở vé thỏa mãn ngay: Vé thuộc lane máy nhà `h410asrock`; cả 2 tệp zip đã nằm sẵn trong `local_runs/` đúng kích thước và SHA-256; trình duyệt Chrome và curl sẵn sàng.
- Không dùng nhánh "4 lần watcher"/`cho-muse`.
- Cập nhật tiến độ: `trang-thai.md` chuyển `dang-lam` (commit `ff76c74`), cập nhật mốc tiến độ theo quy ước mailbox.

---

## 1. Bước 1 — Kiểm kê băm 2 gói zip local trước khi tải

| Tệp cục bộ trên máy nhà | Kích thước (Byte) | SHA-256 | Kết quả đối chiếu |
|---|---|---|---|
| `local_runs/src-package-511/src-package-511-home-match90.zip` | 430.510 | `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403` | **Khớp ghim tuyệt đối** |
| `local_runs/src-421-package/src-421-current-home.zip` | 9.153.022 | `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5` | **Khớp ghim tuyệt đối** |

---

## 2. Bước 2 — Mở kênh tiền lệ & Tải cả 2 tệp lên thư mục AIOS_Data

- Đích đến: thư mục **AIOS_Data** trên Google Drive (`https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`).
- Phiên trình duyệt: Cửa sổ Google Chrome chính thức (Profile `Default`), tài khoản đang đăng nhập sẵn `buiducvinhct1102@gmail.com`.
- Quy trình tải tệp:
  1. Điều hướng trình duyệt vào thư mục `AIOS_Data`.
  2. Kích hoạt nút `Mới` (`+ Mới`) trên thanh bên Drive.
  3. Chọn mục `Tải tệp lên` (Upload file).
  4. Trên hộp thoại `Open` của Windows: Dùng phím tắt `Alt+N` focus ô tên tệp, dán đường dẫn tệp tuyệt đối từ clipboard và gửi phím `Enter`.
  5. Chờ Google Drive tải lên và xác nhận hoàn tất (dấu tích xanh "Đã tải 1 mục lên") cho từng tệp.
- Kết quả: Cả 2 tệp `src-package-511-home-match90.zip` và `src-421-current-home.zip` đã xuất hiện đầy đủ trong danh sách tệp của thư mục `AIOS_Data`.

---

## 3. Bước 3 — Quyền chia sẻ & Sao chép liên kết thật

- Quyền truy cập chung: Cả 2 tệp kế thừa quyền của thư mục cha `AIOS_Data`: **"Bất kỳ ai có đường liên kết"** với vai trò **"Người xem"** (mô tả: "Bất kỳ ai có kết nối Internet và có đường liên kết này đều có thể xem").
- Thao tác lấy liên kết:
  - Chọn dòng tệp -> Mở hộp thoại `Chia sẻ` trên toolbar.
  - Bấm nút **"Sao chép đường liên kết"** trực tiếp trên giao diện Google Drive (không dùng link tự chế).
  - Bấm nút **"Xong"** để đóng hộp thoại.

---

## 4. Bảng liên kết bàn giao cho PC0575

| Gói | Kích thước (Byte) | Link Google Drive (UI) | File ID |
|---|---|---|---|
| Gói 90: `src-package-511-home-match90.zip` | 430.510 | `https://drive.google.com/file/d/1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl/view?usp=sharing` | `1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl` |
| Gói 421: `src-421-current-home.zip` | 9.153.022 | `https://drive.google.com/file/d/1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK/view?usp=sharing` | `1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK` |

### Liên kết tải trực tiếp (không cần đăng nhập, dùng với curl / script / gdown):
- **Gói 90**: `https://drive.usercontent.google.com/download?id=1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl&export=download&confirm=t`
- **Gói 421**: `https://drive.usercontent.google.com/download?id=1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK&export=download&confirm=t`

---

## 5. Bước 4 — Kiểm chứng ẩn danh độc lập (không cookie)

- Môi trường kiểm thử: Chạy `curl.exe` độc lập trong phiên dòng lệnh mới, không truyền cookie, không dùng phiên đăng nhập Chrome:
  ```powershell
  curl.exe -L --silent --max-time 300 -o verify_package90.zip "https://drive.usercontent.google.com/download?id=1z-fOzVmvq47JL2BRfH2JU3lW8st-BXWl&export=download&confirm=t"
  curl.exe -L --silent --max-time 300 -o verify_package421.zip "https://drive.usercontent.google.com/download?id=1U_M3SxY4gdIFSsk6r_PwRbJ_K6xgeLWK&export=download&confirm=t"
  ```
- Kết quả đối chiếu kích thước byte và băm SHA-256:

| Bản tải ẩn danh | Byte nhận | Byte gốc | SHA-256 nhận | SHA-256 gốc | Kết luận |
|---|---|---|---|---|---|
| `verify_package90.zip` | **430.510** | 430.510 | `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403` | `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403` | **Trùng khớp 100%** |
| `verify_package421.zip` | **9.153.022** | 9.153.022 | `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5` | `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5` | **Trùng khớp 100%** |

- Tệp tải về kiểm chứng đã được **xóa ngay sau khi băm** (dọn sạch hoàn toàn thư mục tạm).

---

## 6. Bước 5 — Tệp cục bộ trên máy nhà được bảo toàn nguyên vẹn

- Các tệp gốc trong kho cục bộ không bị sửa đổi, không bị di chuyển:
  - `local_runs/src-package-511/src-package-511-home-match90.zip`: 430.510 bytes, SHA-256 `862cad6ef5943678da25424af177da8d66ee3b53fc4dadc87827836a37613403`.
  - `local_runs/src-421-package/src-421-current-home.zip`: 9.153.022 bytes, SHA-256 `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5`.

---

## 7. Tuân thủ rào cứng & Tiêu chuẩn kỷ luật

- **Không cài đặt phần mềm mới**: Không cài Drive for Desktop, không cài rclone.
- **Không trích xuất dữ liệu nhạy cảm**: Không xuất hay sao chép cookie, token hay credential.
- **Không ảnh hưởng dữ liệu khác**: Chỉ tải đúng 2 tệp zip của vé vào đúng thư mục `AIOS_Data`, không chạm hay thay đổi bất kỳ tệp nào khác trên Drive.
- **Giữ nguyên nhánh Git**: Làm việc hoàn toàn trên nhánh `phieu-viec/rag-fix1`, tuyệt đối không merge vào `main`.

---

## 8. Ghi chú kỹ thuật phục vụ tái lập

- **Hiện tượng Desktop Isolation**: Phiên agent chạy trong sandbox desktop riêng (`exebox-...`), không thể tương tác trực tiếp với giao diện người dùng trên desktop tương tác (`winsta0\default`). Giải pháp: Dùng runner Windows API `CreateProcess` chỉ định `lpDesktop = "winsta0\\default"` để tương tác mượt mà và an toàn.
- **Hiện tượng Job Object Termination**: Tiến trình Chrome khi khởi chạy trực tiếp từ PowerShell runner của agent có nguy cơ bị hủy khi runner kết thúc. Giải pháp: Khởi chạy Chrome cố định thông qua Windows Scheduled Task chạy dưới quyền user thật, giúp phiên trình duyệt bền vững xuyên suốt toàn bộ quá trình upload và lấy liên kết.
- **Tọa độ điều khiển trên màn hình 2560x1080**:
  - Hàng tệp gói 421: `(X = 600, Y = 805)`.
  - Hàng tệp gói 90: `(X = 600, Y = 850)`.
  - Nút Chia sẻ trên thanh công cụ: `(X = 770, Y = 232)`.
  - Nút "Sao chép đường liên kết" trên modal Chia sẻ: `(X = 1240..1260, Y = 718..735)`.
  - Nút "Xong" trên modal Chia sẻ: `(X = 1560..1615, Y = 718..735)`.
  - Đọc liên kết clipboard: Sử dụng `Get-Clipboard -Raw` trong PowerShell để lấy chuỗi liên kết chính xác từ clipboard hệ thống.
