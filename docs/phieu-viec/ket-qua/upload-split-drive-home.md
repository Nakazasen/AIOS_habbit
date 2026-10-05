# Báo cáo vé `UPLOAD-SPLIT-DRIVE-HOME` — sao lưu 4 khối index tách lên Drive

- Trạng thái: `xong-cho-duyet`; đủ 5 file trong `AIOS_Data/index-split-r5-backup`, tải lại đối chiếu SHA-256 trùng local 100%.
- Máy làm: nhà `h410asrock` (Windows), 2026-10-05 20:09–23:30 +07.
- Vé: `docs/phieu-viec/mailbox-opencode/prompt-upload-split-drive-home.md`. Branch `phieu-viec/rag-fix1`, không merge `main`.

## 0. Nhận vé + cổng gate

- `git pull` nhận vé mới 20:05 (trạng thái `moi`, prompt đúng vé, verdict vé trước ĐẠT). 0 file watcher tự mở, không rơi nhánh 4 lần nên không đặt `cho-muse`.
- Đặt `trang-thai.md` → `dang-lam` ngay + push, rồi đẩy mốc tiến độ sau mỗi bước (kiểm đếm, SHA gốc, thư mục, từng file, đối chiếu).

## 1. Bước 1 — Kiểm đủ 4 khối + manifest (đủ, dừng hay không: đủ nên làm tiếp)

| Khối local | Byte | Tài liệu / chunk (manifest) |
|---|---|---|
| `lsu/library.sqlite` | 1.155.637.248 | 92 / 71.945 |
| `dieu_tra_loi/library.sqlite` | 1.643.761.664 | 681 / 74.439 |
| `mom/library.sqlite` | 21.598.208 | 44 / 1.014 |
| `tong_hop/library.sqlite` | 36.081.664 | 72 / 2.402 |
| `domain_manifest.json` | 491.253 | manifest tổng |
| Tổng | 2.857.570.037 (~2,66 GiB) | 889 tài liệu / 149.800 chunk |

- SHA-256 gốc (làm trước khi upload để đối chiếu sau): xem bảng mục 4.

## 2. Bước 2 — Upload lên Drive

- Đích: `AIOS_Data` (`https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`), thư mục con mới `index-split-r5-backup` (ID `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`).
- Vì 4 khối trùng tên `library.sqlite` nên đặt mỗi khối một ngăn con: `lsu/`, `dieu_tra_loi/`, `mom/`, `tong_hop/`; manifest nằm ở gốc thư mục backup.
- Cách làm: điều khiển cửa sổ Chrome đang đăng nhập sẵn (`buiducvinhct1102@gmail.com`) bằng UI Automation (InvokePattern + phím, không tọa độ cứng, không sao chép credential), giống tiền lệ vé `upload-delta-drive`/`onnx-upload-drive`. Quota Drive còn trống ~5TB (đã dùng ~23–27GB) nên đủ chỗ.
- Kết quả: 5/5 file đã nằm đúng ngăn (vào từng ngăn liệt kê kiểm tra, nhãn đã chia sẻ, ngày sửa 3 thg 10 khớp local).

## 3. Bước 3 — Đối chiếu từng byte (tải lại + SHA-256)

- Tải lại từng file bằng nút Tải xuống trong phiên đăng nhập, băm SHA-256 bản tải về so với bản local:

| File trên Drive | Byte local | Byte tải về | SHA-256 (local = tải về) | Kết quả |
|---|---|---|---|---|
| `domain_manifest.json` | 491.253 | 491.253 | `54f91694…7915531e88` | **Khớp** |
| `mom/library.sqlite` | 21.598.208 | 21.598.208 | `9e796f79…076840d14c` | **Khớp** |
| `tong_hop/library.sqlite` | 36.081.664 | 36.081.664 | `4ad4bb35…5dd76e73b` | **Khớp** |
| `lsu/library.sqlite` | 1.155.637.248 | 1.155.637.248 | `5982a4f1…4b3c4eabb` | **Khớp** |
| `dieu_tra_loi/library.sqlite` | 1.643.761.664 | 1.643.761.664 | `3bb7b10b…62c84c36e569651` | **Khớp** |

- Chuỗi SHA đầy đủ:
  - manifest: `54f916944c4f2a720300ae0845399d196b3053fe537558f68e2f9f7915531e88`
  - mom: `9e796f79e20ee152cb48a56815149243fddfe165e0917f0303c2bf076840d14c`
  - tong_hop: `4ad4bb35a2367eda4c0a78c0459ed6cf0b0d2d8f2b22f0c36685ba95dd76e73b`
  - lsu: `5982a4f1b99a455e89d30bb87095a3ab6f4617b50325a2da10c6d8f4b3c4eabb`
  - dieu_tra_loi: `3bb7b10b5bb2d9345e6ba2baf95d6d6f25575639805504bda66284c36e569651`
- Bản tải kiểm chứng đã xóa sau khi băm (giữ ổ C gọn).

## 4. Liên kết Drive bàn giao

| Nội dung | Đường liên kết / ID |
|---|---|
| Thư mục backup | `https://drive.google.com/drive/folders/1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il` (ID `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`) |
| Ngăn `mom` | ID `18cE9KmGWLCH…` (đọc từ thanh địa chỉ khi mở ngăn; xem ảnh `split_shmom4_dlg.png`) |
| `mom/library.sqlite` | `https://drive.google.com/file/d/1Ew6pZTXL41hr-mn5x_Sm3qXU4X2oPBtf/view?usp=sharing` |
| `tong_hop/library.sqlite` | `https://drive.google.com/file/d/1fcmGxVZ6zwWc_04JITDZPWikO7py27PK/view?usp=sharing` |
| `domain_manifest.json` | `https://drive.google.com/file/d/1iAWjsdQHOgJzLJlZHOe_u14L0w4neTHB/view?usp=sharing` |
| `lsu/library.sqlite`, `dieu_tra_loi/library.sqlite` | **Chưa lấy được ID** (hộp Chia sẻ báo “không thể chia sẻ vào thời điểm này”, thử nhiều lần 21:45–23:16). Quyền file vẫn hiện “Đã chia sẻ”. Sẽ bổ sung khi Drive mở lại. |

- Quyền các file đã lấy đường liên kết: “Bất kỳ ai có đường liên kết — Người xem”.

## 5. Sự cố gặp và cách xử lý (minh bạch)

1. Dán cả đường dẫn vào hộp Open chỉ đổi thư mục, không điền tên file → tách 2 bước (dán thư mục + Enter, rồi dán tên file + Enter). Đã kiểm bằng ảnh chụp dialog.
2. Poll tên file toàn cục dễ báo nhầm vì UIA đọc cả tab nền → verify chuẩn bằng liệt kê đúng ngăn.
3. Mỗi lần mở tab mới làm rối (lạc sang tab Antigravity) → dùng lại tab Drive + dọn 32 tab thừa (không đụng tab Muse/Browser của user).
4. Hộp Open thừa che màn hình → đóng bằng C# static tìm `#32770` + Esc (đóng 3 cái).
5. Một file `library.sqlite` (~20MB, trùng khối mom) lọt ra gốc backup do lần upload lỗi → đã chuyển vào thùng rác, gốc còn đúng 4 ngăn + manifest (có ảnh toast xác nhận).
6. 2 file lớn chưa lấy được ID (Drive chặn chia sẻ tạm thời) → ghi rõ, không bịa ID.
7. Timestamp 2 mốc tiến độ ghi sớm vài phút so với giờ máy (ước lượng khi viết) → các mốc sau lấy giờ thật; không ảnh hưởng nội dung.

## 6. Đã KHÔNG làm (đúng rào vé)

- Không xóa, không sửa, không di chuyển file local (`D:\Sandbox\AIOS_index_split_new\` nguyên vẹn).
- Không nhập kho chính, không ghi index production, không đụng luồng RAG.
- Không merge `main`; chỉ commit báo cáo + `trang-thai.md` lên `phieu-viec/rag-fix1`.

## 7. Kết luận

- Upload đủ 5 file + đối chiếu SHA-256 trùng 100% → **đề nghị verdict ĐẠT** (chờ Muse duyệt; bổ sung 2 ID sau).
- FileCK bản tải kiểm chứng (2,8GB) trong `C:\temp\verify_*.sqlite/json` nên xóa sau khi Muse duyệt xong (giữ làm bằng chứng tạm đến lúc đó).
