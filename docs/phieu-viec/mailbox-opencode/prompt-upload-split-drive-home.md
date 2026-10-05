# VÉ: UPLOAD-SPLIT-DRIVE-HOME (backup 4 khối index tách lên Drive)

- Mã vé: `UPLOAD-SPLIT-DRIVE-HOME`
- Role OMP gợi ý: DEFAULT (upload ~2,8GB, cần ổn định)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/upload-split-drive-home.md`

## Bối cảnh

Vé `INDEX-SPLIT-R5` đã ĐẠT (03/10): kho tri thức được tách thành 4 khối tại
`D:\Sandbox\AIOS_index_split_new\`. Bốn khối CHỈ tồn tại trên máy nhà — chưa có
backup ngoài. Sáng 05/10 máy công ty mất dữ liệu vì dọn ổ đã cho thấy rủi ro
mất dữ liệu là có thật. Vé này tạo backup Drive cho 4 khối.

## Việc cần làm

1. Kiểm tra `D:\Sandbox\AIOS_index_split_new\` còn đủ 4 khối + manifest:
   - Khối LSU (~1,16GB — 92 document / 71.945 chunk)
   - Khối Dieu-tra-loi (~1,64GB — 681 document / 74.439 chunk)
   - Khối MOM (~21,6MB — 44 document / 1.014 chunk)
   - Khối Tong-hop (~36MB — 72 document / 2.402 chunk)
   - File manifest tổng.
   Nếu thiếu khối nào thì DỪNG và báo ngay (không upload nửa vời).
2. Upload cả 4 khối + manifest lên Google Drive, vào thư mục AIOS_Data
   (`https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`),
   đặt trong thư mục con `index-split-r5-backup` cho gọn (tạo mới nếu chưa có).
3. Sau upload, đối chiếu: tên file + dung lượng từng file trên Drive phải khớp
   với local từng byte. Tải lại header mỗi file để chắc chắn không lỗi giữa chừng.
4. Ghi báo cáo: danh sách file, dung lượng, ID Drive từng file, kết quả đối chiếu.

## Tiêu chí nghiệm thu

- Đủ 5 file (4 khối + manifest) trên Drive, dung lượng khớp local 100%.
- Báo cáo `upload-split-drive-home.md` có đủ ID Drive + bảng đối chiếu.
- Verdict ĐẠT = upload đủ + đối chiếu khớp. Thiếu 1 byte cũng là CHƯA ĐẠT.
- Không xóa, không đụng file local. Không merge `main`.
