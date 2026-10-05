# VÉ: UPLOAD-DIGEST-DRIVE-HOME (đưa thành phẩm sổ tay lên Drive cho máy công ty tải về)

- Mã vé: `UPLOAD-DIGEST-DRIVE-HOME`
- Role OMP gợi ý: DEFAULT (upload Drive + đối chiếu SHA)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/upload-digest-drive-home.md`

## Bối cảnh

Vé `DIGEST-CTY-PREP-HOME` đã ĐẠT (báo cáo `docs/phieu-viec/ket-qua/digest-cty-prep.md`):
sổ tay tri thức 889 mục + manifest + 3.392 cặp hỏi-đáp đã duyệt đã kiểm kê đủ, SHA khớp.
Nhưng 2 món này (sổ tay + cặp hỏi-đáp) CHƯA có trên Drive — máy công ty không tải về
được cho vé `DIGEST-CTY-RESUME`. Vé này đưa chúng lên Drive, đối chiếu từng byte.
(Muse đã quyết: đưa lên Drive, không chép tay.)

## Việc cần làm

1. Upload 4 file sau lên thư mục backup `AIOS_Data/index-split-r5-backup`
   (ID `1T_Ao9Piy8dDtYRn6fVNxVErzQAEf14il`), tạo ngăn con `digest/` riêng
   (tránh trùng tên với 5 file đã có):
   - `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md` (1.374.070 B,
     SHA-256 `fd2b10e10f618e0f861fdd5db9ce8c30667c265d3a9c0f0ddbf70f55002cf1cd`)
   - `C:\tmp\knowledge-digest-home\so_tay_tri_thuc.md.manifest.json` (290 B)
   - `D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua\wire-qa-mapping.jsonl`
     (file local Windows 1.267.666 B — line ending CRLF, SHA-256
     `e242585724ba864c4b2131d1d0a3c072bf58508ded952f46c4c56189a3b3632a`;
     khác git blob LF 1.264.274 B — nội dung 3.392 dòng như nhau.
     Upload đúng file local đã băm, không convert line ending.)
   - `C:\tmp\knowledge-digest-home\probe-R2.json` (kết quả probe 12 câu 2 lane,
     để máy công ty tham chiếu, khỏi chạy lại lane sổ tay)
2. Đặt quyền link chia sẻ cho từng file (hoặc cả ngăn `digest/`), ghi lại link/ID.
3. Tải lại từng file qua phiên đăng nhập, băm SHA-256 đối chiếu với SHA local —
   lệch byte nào thì upload lại, không dùng cố.
4. Viết báo cáo `upload-digest-drive-home.md` gồm bảng:
   tên file | size local | SHA-256 local | link/ID Drive | SHA tải lại | kết quả.
5. Chỉ đọc thành phẩm, không sửa/xóa/di chuyển; không nhúng lại; không ghi index;
   không merge `main`. Commit chỉ báo cáo + `trang-thai.md`.
6. Heartbeat: ghi mốc bước vào `trang-thai.md` tối thiểu mỗi 15 phút khi vé kéo dài.

## Tiêu chí nghiệm thu

- ĐẠT = đủ 4 file nằm đúng ngăn `digest/`, có link/ID chia sẻ, tải lại SHA khớp
  100% với SHA local, báo cáo đủ bảng trên.
- Bonus (không bắt buộc): nếu Drive đã mở lại chia sẻ, lấy nốt 2 link riêng của
  `lsu` và `dieu_tra_loi` (lần trước báo "không thể chia sẻ vào thời điểm này"),
  ghi vào báo cáo.
