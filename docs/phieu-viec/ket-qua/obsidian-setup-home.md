# Báo cáo vé OBSIDIAN-SETUP-HOME (máy nhà h410asrock)

- Vé: `OBSIDIAN-SETUP-HOME` (bản đính chính đích vault 09:15 ngày 10/10)
- Máy: h410asrock (đúng máy nhà). Thời gian làm: 08:21–09:35 +07 ngày 2026-10-10.
- Kết luận: ĐẠT cả 6 bước. Obsidian 1.14.4 đã cài, vault thật `so-cai` đã mở thấy sổ, tệp lệnh một chạm đã chạy thật và dòng kiểm chứng đã lên kho từ xa.

## 1. Cập nhật kho (bước 1)

- `git pull origin phieu-viec/rag-fix1` về đầu nhánh mới nhất (lúc nhận: `d4f8297`).
- Giữa chừng (09:10–09:15) kho từ xa có 2 commit mới của điều phối: đính chính đích vault sang kho `aios-dieu-phoi` + bản đính chính prompt. Đã `pull --rebase` và làm theo bản mới, bản cũ `docs/so-cai-vault` giữ nguyên làm lưu trữ, không đụng.
- Clone kho điều phối: `https://github.com/Nakazasen/aios-dieu-phoi.git` về `D:\Sandbox\aios-dieu-phoi`, nhánh `main` tại `5577b4e`. Không bị từ chối quyền.

## 2. Tải + cài Obsidian (bước 2, nguồn chính thức)

- Nguồn: kho phát hành chính thức `obsidianmd/obsidian-releases`, thẻ `v1.14.4` (phát hành 05/10/2026, đúng bản vé nêu). Không tải nguồn lạ.
- Tệp: `Obsidian-1.14.4.exe`, 341.331.008 byte.
- Cài cho người dùng hiện tại: `C:\Users\Admin\AppData\Local\Programs\Obsidian\Obsidian.exe` (239.103.760 byte).
- Kiểm tra bản: chạy `Obsidian.exe --version` báo `Latest version is 1.14.4, App is up to date`.
- Số đo thật: tải ~9 giây (mạng máy nhà), cài im lặng `/S` mất ~2–3 phút mới hiện thư mục (lần đầu tưởng chưa cài — xem phát hiện §7).

## 3. Mở vault (bước 3, dùng thật)

- Vault: `D:\Sandbox\aios-dieu-phoi\so-cai` (đăng ký vào `obsidian.json`, mở bằng Obsidian 1.14.4).
- Thời gian mở: tiến trình khởi động 09:17:29, cửa sổ vault hiện đầy đủ ~09:19 (khoảng 1,5 phút lần đầu).
- Kiểm chứng: cây tệp trái hiện `README` + `So-cai-AIOS_habbit.md`; nội dung mở ra là sổ cái, mục mới nhất ở Nhật ký là `Cập nhật 2026-10-10 ~09:25 +07 — Đợt chuyển hộp thư...` (đúng mốc kho điều phối đã mở mà vé yêu cầu).
- Không cài thêm plugin nào (tệp `core-plugins.json` sinh ra chỉ là mặc định).

## 4. Tệp lệnh đồng bộ một chạm (bước 4)

- Đường dẫn: `D:\Sandbox\aios-dieu-phoi\dong-bo-so-cai.ps1` (1.667 byte, mã hoá UTF-8 có BOM `EF BB BF`).
- Hành vi đúng vé, chỉ thao tác trong bản clone đó: kéo `main` mới nhất về → chỉ `git add -- so-cai` và ghi một commit riêng → kéo lại `--rebase` → đẩy lên. Không có lệnh nào đụng ngoài `so-cai`.
- Thông điệp mặc định khi không truyền tham số: `So cai: dong bo <yyyy-MM-dd HH:mm>`.

## 5. Kiểm chứng đồng bộ thật (bước 5, dùng thật)

- Khi Obsidian đang mở vault, đã thêm đúng một dòng vào cuối `so-cai/README.md`:
  `- Dong kiem chung may nha h410asrock 2026-10-10 09:22 +07 qua Obsidian 1.14.4 (vault so-cai).`
- Chạy `dong-bo-so-cai.ps1`: 4 bước đều xanh. Commit `1076bcdf2dd1d0d6e1cbf5df333daea9540ee0f4` (`So cai: dong bo 2026-10-10 09:21`) đã đẩy lên `origin/main` kho `aios-dieu-phoi`.
- Xác minh từ xa: `git fetch` rồi đọc `origin/main:so-cai/README.md` thấy đúng dòng kiểm chứng trên.
- Tệp lệnh được nộp riêng bằng commit thủ công `a542acfc36eb83550454241cadf7e1b8de9bfc65` (không đi qua chính tệp lệnh, đúng rào "một commit riêng cho so-cai").

## 6. Ảnh màn hình (bước 6)

- Tệp: `docs/phieu-viec/ket-qua/obsidian-setup-home.png` (205.586 byte, đo trên bản đã nộp vào kho sau commit).
- Nội dung ảnh: cửa sổ Obsidian tiêu đề `So-cai-AIOS_habbit - so-cai`, cây tệp trái thấy `README` + `So-cai-AIOS_habbit`, vùng giữa là sổ cái với mục Nhật ký mới nhất 09:25. (Hai lần chụp đầu hỏng vì Photos/Antigravity che mất — lần 3 đã đưa cửa sổ Obsidian ra trước bằng `SetForegroundWindow` rồi chụp.)

## Đối chiếu rào cứng

- Không sửa mục cũ của sổ: commit đồng bộ không chứa `So-cai-AIOS_habbit.md` (chỉ `README.md` + 3 tệp cấu hình `.obsidian` do Obsidian tự sinh + 1 canvas rỗng đã dọn ở commit sau).
- Không plugin ngoài mặc định: không cài gì thêm.
- Không merge `main` kho dự án, không đụng chỉ mục production: mọi commit mới nằm ở `aios-dieu-phoi` (2 commit) và nhánh `phieu-viec/rag-fix1` chỉ có báo cáo + trạng thái + ảnh.
- Kích thước trên đã đo sau commit: ảnh 205.586 byte, `dong-bo-so-cai.ps1` 1.667 byte.

## 7. Phát hiện thêm (ghi trung thực)

1. Cài im lặng Obsidian `/S` rất chậm hiện thư mục (tưởng lỗi, hoá ra sau ~2–3 phút mới có `Programs\Obsidian`).
2. Mở vault lần đầu Obsidian tự sinh/sửa: `app.json`, `appearance.json`, `core-plugins.json`, `Untitled.canvas` rỗng và (sau khi xong) `graph.json` chưa theo dõi. Đã dọn `Untitled.canvas`; `graph.json` để lại chưa theo dõi, đề nghị bổ sung vào `.gitignore` của vault ở vé sau.
3. `Add-Content` ghi dòng kiểm chứng không dấu (tránh lỗi mã hoá console máy) — nội dung vẫn đủ thời gian + máy + bản Obsidian để điều phối đối chiếu.
