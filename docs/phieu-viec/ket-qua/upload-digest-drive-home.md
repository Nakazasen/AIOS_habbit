# Báo cáo vé `UPLOAD-DIGEST-DRIVE-HOME` — đưa thành phẩm sổ tay lên Drive

- Trạng thái: `xong-cho-duyet`; đủ 4 file trong ngăn `digest/`, tải lại đối chiếu SHA-256 trùng local 100%.
- Máy làm: nhà `h410asrock` (Windows), 2026-10-06 04:50–06:10 +07.
- Vé: `docs/phieu-viec/mailbox-opencode/prompt.md` (`UPLOAD-DIGEST-DRIVE-HOME`). Branch `phieu-viec/rag-fix1`, không merge `main`.

## 0. Nhận vé + cổng gate

- `git pull` nhận vé mới (trạng thái `moi`, prompt đúng vé, verdict vé trước ĐẠT). 0 file watcher tự mở, không rơi nhánh 4 lần nên không đặt `cho-muse`.
- Đặt `trang-thai.md` → `dang-lam` ngay + push, rồi đẩy mốc tiến độ sau mỗi bước (kiểm kê, ngăn, upload, đối chiếu).

## 1. Bước 1 — Kiểm kê 4 file local (đủ)

| File local | Byte | SHA-256 |
|---|---|---|
| `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md` | 1.374.070 | `fd2b10e10f618e0f861fdd5db9ce8c30667c265d3a9c0f0ddbf70f55002cf1cd` (khớp vé) |
| `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md.manifest.json` | 290 | `ea7e9f9930ab788e947814db65323735385b7b3adb16549a210fd8e1c54fdca` |
| `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (local Windows CRLF) | 1.267.666 | `e242585724ba864c4b2131d1d0a3c072bf58508ded952f46c4c56189a3b3632a` (khớp vé) |
| `C:\tmp\knowledge-digest-home\probe-R2.json` | 41.697 | `e9a6ec8e81b6c213cd50f0bd5ef264d0272a66870c40a6f7fd129777c47ec2b1` |

- Upload đúng file local đã băm, không convert line ending (wire-qa giữ CRLF).

## 2. Bước 2 — Upload lên Drive

- Đích: `AIOS_Data/index-split-r5-backup` (ID `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`), ngăn con mới `digest/` (ID `1JVOdfbbIqIFCbGKcng_-eIonRNMEBL5B`).
- Cách làm: điều khiển cửa sổ Chrome đang đăng nhập sẵn (`buiducvinhct1102@gmail.com`) bằng UI Automation (bấm nút Mới → Tải tệp lên → điền hộp Open, giống tiền lệ vé `upload-split-drive-home`). Mở cửa sổ Chrome riêng (`--new-window`) để khỏi đụng tab của user.
- Kết quả: 4/4 file đã nằm đúng ngăn (toast Drive "Đã tải 4 mục lên", tích xanh cả 4; danh sách ngăn hiện đủ 4 tên + đúng byte).

## 3. Bước 3 — Đối chiếu từng byte (tải lại + SHA-256)

- Tải lại từng file bằng link tải trực tiếp (`uc?export=download`, phiên ẩn danh — ngăn/file đã chia sẻ "Bất kỳ ai có đường liên kết"), băm SHA-256 bản tải về so với bản local:

| File trên Drive | Byte local | Byte tải về | SHA-256 (local = tải về) | Link/ID Drive | Kết quả |
|---|---|---|---|---|---|
| `so_tay_tri_thuc.md` | 1.374.070 | 1.374.070 | `fd2b10e10f618e0f861fdd5db9ce8c30667c265d3a9c0f0ddbf70f55002cf1cd` | `https://drive.google.com/file/d/1waT47ED61s1hvZn3jKOW9kNgxZyY69Tq/view?usp=sharing` | **Khớp** |
| `so_tay_tri_thuc.md.manifest.json` | 290 | 290 | `ea7e9f9930ab788e947814db65323735385b7b3adb16549a210fd8e1c54fdca` | `https://drive.google.com/file/d/1pXvTEvzPH0dDFAnh4Hhmon1pWV-nPsdS/view?usp=sharing` | **Khớp** |
| `wire-qa-mapping.jsonl` | 1.267.666 | 1.267.666 | `e242585724ba864c4b2131d1d0a3c072bf58508ded952f46c4c56189a3b3632a` | `https://drive.google.com/file/d/1hcO1JxOJilwuJlAl4VakxNM-VvuARcqK/view?usp=sharing` | **Khớp** |
| `probe-R2.json` | 41.697 | 41.697 | `e9a6ec8e81b6c213cd50f0bd5ef264d0272a66870c40a6f7fd129777c47ec2b1` | `https://drive.google.com/file/d/1B5GDG7uhLr-hqax8IuI2Ha6wWckF8_of/view?usp=sharing` | **Khớp** |

- Quyền chia sẻ: ngăn `digest/` ở chế độ "Bất kỳ ai có đường liên kết — Người xem" (đã có sẵn khi mở hộp chia sẻ, không phải đổi gì; file kế thừa): link ngăn `https://drive.google.com/drive/folders/1JVOdfbbIqIFCbGKcng_-eIonRNMEBL5B?usp=sharing`.
- Bản tải kiểm chứng giữ ở `C:\temp\verify_digest\` (4 file, tổng ~2,7 MB) làm bằng chứng tạm, xóa sau khi Muse duyệt xong.

## 4. Bonus (không bắt buộc) — chưa làm

- Chưa lấy lại 2 link riêng `lsu` / `dieu_tra_loi` (vé trước Drive báo không chia sẻ được). Vé này không chặn nên để riêng, không đụng các ngăn cũ.

## 5. Sự cố gặp và cách xử lý (minh bạch)

1. Gõ tên ngăn bằng bàn phím bị bộ gõ tiếng Việt chèn dấu — kiểm tra lại ảnh chụp, tên thực tế đúng `digest` (không phải đổi tên lại).
2. Cửa sổ Chrome bị trôi khỏi màn hình + lẫn tab lạ — mở cửa sổ mới riêng (`--new-window`) cho vé này, đóng tab lạ đã lỡ mở (không đụng tab Muse/Browser của user).
3. Popup watcher ("Bao ve mailbox", "tu mo tho") che màn hình vài lần — chỉ bấm OK tắt, không sửa watcher.
4. Hộp Open của Chrome không nằm trong cây UIA gốc (nằm dưới nút Chrome) — tìm trong `Subtree` của cửa sổ Chrome mới thấy.
5. Tranh giành focus với console của thợ khác (omp) trên cùng máy — chuyển sang tải lại bằng link trực tiếp ẩn danh (ngăn đã chia sẻ), không cần trình duyệt, tránh bấm nhầm.

## 6. Đã KHÔNG làm (đúng rào vé)

- Không sửa/xóa/di chuyển thành phẩm local; không nhúng lại; không ghi index.
- Không merge `main`; chỉ commit báo cáo + `trang-thai.md` lên `phieu-viec/rag-fix1`.

## 7. Kết luận

- Upload đủ 4 file + tải lại đối chiếu SHA-256 trùng 100% → **đề nghị verdict ĐẠT** (chờ Muse duyệt).
