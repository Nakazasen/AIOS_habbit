# Vé upload-delta-drive — Báo cáo

- Trạng thái: `xong-cho-duyet`; 2 gói delta đã nằm trên Google Drive (thư mục AIOS_Data), quyền ai-có-link=Người xem, đã verify tải ẩn danh khớp byte + SHA-256.
- Máy thực hiện: máy nhà `h410asrock` (Windows), 2026-10-01 ~06:33–07:05 +07.
- Nguồn vé: `docs/phieu-viec/mailbox/prompt.md` (UPLOAD-DELTA-DRIVE).

## 0. Nhận vé + cổng gate

- Watcher tự mở OMP lúc 06:33:47 (`launchStallCount=1/4`). **Điều kiện mở đã thoả ngay** (vé đúng lane [NHÀ]; 2 file zip đã nằm trên ổ C đúng kích thước; Python/curl sẵn sàng) → không dùng nhánh "4 lần watcher"/`cho-muse`.
- OMP nhận vé: `trang-thai.md` → `dang-lam` (commit `68e434b`), không quay vòng no-op.

## 1. Bước 1 — Verify SHA-256 2 file local (khớp ghim)

| Tệp trên ổ C | Byte | SHA-256 | Kết quả |
|---|---|---|---|
| `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` | 20.867.536 | `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85` | **Khớp ghim** |
| `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` | 74.065.213 | `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3` | **Khớp ghim** |

- Băm 2 lần: trước khi upload và sau khi upload xong — cả 2 lần đều khớp, `mtime` không đổi.

## 2. Bước 2 — Upload lên thư mục AIOS_Data trên Drive

- Đích: thư mục **AIOS_Data** (đúng thư mục vé, đã có sẵn `export_dc.jsonl`, `library.sqlite`, `bge-m3-onnx-fp32.zip`…).
- Cách làm: điều khiển **cửa sổ Chrome đang đăng nhập sẵn** (`buiducvinhCT1102@gmail.com`) bằng UI Automation của Windows — thao tác tương đương người dùng, không cài thêm phần mềm, không sao chép cookie/credential:
  1. Mở tab mới điều hướng `https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F` (dán URL qua clipboard để tránh lỗi gõ).
  2. Nút `Mới` → mục `Tải tệp lên` (click theo phần tử accessibility; thử đường phím tắt `Alt+C`→`U` không ăn — Drive có thể đã tắt phím tắt).
  3. Hộp thoại `Open` của Windows: điền đầy đủ đường dẫn vào ô "File name" (bàn phím: `Alt+N` + dán clipboard + `Enter`; UIA của hộp thoại DirectUI không cho `SetValue`).
  4. Chờ upload; lặp lại cho file thứ hai.
- Kết quả: UI xác nhận **"Đã tải 2 mục lên"**; 2 dòng `gpu-262b-delta-20261001.zip` và `gpu-dc-delta-20261001.zip` xuất hiện trong danh sách thư mục.
- Ghi chú kỹ thuật (để tái lập): phiên này chạy tiến trình điều khiển **không DPI-aware** nên tọa độ UIA = tọa độ click (đã hiệu chuẩn lại bằng crosshair + đọc điểm ảnh; khác phiên trước dùng tọa độ ×1,5). Ảnh chụp/script trung gian nằm ở `C:\temp\upl*.ps1`, `C:\temp\upl*.png`.

## 3. Bước 3 — Quyền chia sẻ (ai có link = Người xem)

- Mở hộp thoại `Chia sẻ` cho từng file: trạng thái **hiện tại đã sẵn đúng yêu cầu vé**: "Bất kỳ ai có đường liên kết" + vai trò "Người xem" (mô tả "Bất kỳ ai có kết nối Internet và có đường liên kết này đều có thể xem") — giống cơ chế tiền lệ file `export_dc.jsonl`; không cần đổi thêm.
- Đã bấm `Sao chép đường liên kết` trong hộp thoại từng file (không dùng link tự chế) rồi `Xong`.

## 4. Liên kết bàn giao cho PC0575

| Gói | Link Drive | File ID |
|---|---|---|
| `gpu-262b-delta-20261001.zip` (20.867.536 B) | `https://drive.google.com/file/d/1TE6mHBAE0CzD5I4pleO-23zVYaspnsVz/view?usp=sharing` | `1TE6mHBAE0CzD5I4pleO-23zVYaspnsVz` |
| `gpu-dc-delta-20261001.zip` (74.065.213 B) | `https://drive.google.com/file/d/1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ/view?usp=sharing` | `1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ` |

- Link tải trực tiếp (không cần đăng nhập), dùng được với `curl`/`gdown`:
  - `https://drive.usercontent.google.com/download?id=1TE6mHBAE0CzD5I4pleO-23zVYaspnsVz&export=download&confirm=t`
  - `https://drive.usercontent.google.com/download?id=1Smteq_Iyjx2uZjh2RlrK1wvASFjXJ3yZ&export=download&confirm=t`

## 5. Bước 4 — Verify độc lập ẩn danh (không cookie)

- Lệnh đã chạy (curl mới, không cookie, không dùng phiên Chrome):
  `curl -L --silent --max-time 300 -o verify_262b.zip "<link trực tiếp 262b>"` và tương tự cho DC.
- Kết quả:

| Bản tải ẩn danh | Byte nhận | SHA-256 nhận | So với ghim |
|---|---|---|---|
| `verify_262b.zip` | **20.867.536** | `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85` | **Trùng khớp** |
| `verify_dc.zip` | **74.065.213** | `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3` | **Trùng khớp** |

- Bản tải kiểm chứng đã **xóa sau khi băm** (không để lại file rác).

## 6. Bước 5 — Bản local trên ổ C còn nguyên

- Không xóa, không sửa, không di chuyển: `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` (20.867.536 B, SHA `5bd7c56d…9a85`, mtime 01:01) và `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` (74.065.213 B, SHA `31afe1e3…63e3`, mtime 03:12).

## 7. Đã KHÔNG làm (đúng lệnh cấm của vé)

- Không đụng production, staging (không ghi), không đụng ổ D (repo D chỉ đọc + commit/push git theo quy ước mailbox).
- Không merge `main`; branch vẫn là `phieu-viec/rag-fix1`.
- Không xóa 2 bản local trên ổ C.

## 8. Tác động phụ khi điều khiển Chrome (minh bạch, đã khôi phục mức tối đa)

- Chrome: mở thêm **1 tab `AIOS_Data - Google Drive`** (giữ lại làm kết quả bàn giao — như tiền lệ vé `gpu-dc`); 4 tab gốc (`Chat — Muse`, 2 tab Drive cũ, `Hỏi tài liệu`) giữ nguyên; kiểm kê cuối: đúng 1 cửa sổ Chrome, 5 tab.
- Có thử `omp browser-relay install` để mở đường điều khiển DOM (chỉ ghi extension vào `C:\Users\Admin\.omp\browser-relay\extension`; **chưa nạp vào Chrome**, không đổi cấu hình Chrome) — không dùng đến vì phải thao tác `chrome://extensions` thủ công; hướng UI Automation là đủ.
- Trong lúc thử đó, phím lỡ bắn vào cửa sổ **Antigravity** đang mở 1 lần (cửa sổ này không lộ cây UIA nên không dọn được): 1 dòng `chrome://extensions` lỡ nhập vào ô chat và **1 tin nhắn đang treo ở "Queued Messages 1"** của Antigravity — user kiểm tra/hủy tay trong Antigravity nếu thấy; không liên quan Chrome/dữ liệu.
- Một lần tab mới bị chuyển hướng sang trang `iqoption.net` (hành vi của profile khi mở tab mới trong lúc thử; không rõ cấu hình) — tab này **không còn** trong kiểm kê cuối.
- VS Code (đang minimized) bị bật lên 1 lần do click nhầm vào taskbar (vùng y>≈695 bị taskbar auto-hide cướp click); đã **minimize lại**; kiểm tra nhanh: không file nào bị sửa (tab đang mở vẫn sạch).
- Không cài phần mềm; không đọc/copy cookie; không đổi cấu hình Chrome.

## 9. Phạm vi kiểm tra

- Vé không đụng mã nguồn → không chạy lại full test suite (đúng phạm vi), chỉ git thêm 1 file báo cáo + cập nhật `trang-thai.md`.
