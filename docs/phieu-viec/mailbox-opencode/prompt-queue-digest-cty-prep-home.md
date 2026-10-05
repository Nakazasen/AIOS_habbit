# VÉ: DIGEST-CTY-PREP-HOME (kiểm kê thành phẩm sổ tay để máy công ty khỏi làm lại)

- Mã vé: `DIGEST-CTY-PREP-HOME`
- Role OMP gợi ý: DEFAULT (đọc file lớn, đối chiếu SHA)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/digest-cty-prep.md`

## Bối cảnh

Vé `KNOWLEDGE-DIGEST-HOME-R2` đã ĐẠT (05/10): sổ tay tri thức 889/889 mục xong.
Máy công ty (PC0575) sắp tới cần cuốn sổ tay này, nhưng PC0575 dùng index TẠM
khác máy nhà — nếu làm lại từ đầu sẽ tốn công trùng lặp. Vé này kiểm kê kỹ
những gì máy nhà đã làm xong, để vé `DIGEST-CTY-RESUME` (phát sau) chỉ việc
tái sử dụng, không làm lại.

## Việc cần làm

1. Kiểm tra các thành phẩm của R2 còn nguyên vẹn trên máy nhà:
   - File sổ tay 889 mục + manifest SHA (đường dẫn, dung lượng, SHA-256).
   - File `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (3.392 cặp hỏi-đáp đã duyệt).
   - 4 khối index tách trên Drive (`index-split-r5-backup`, đã backup 05/10).
2. Đối chiếu SHA/manifest với báo cáo R2 — thành phẩm nào lệch/thiếu thì ghi rõ,
   không tự sửa.
3. Viết báo cáo `digest-cty-prep.md` gồm:
   - Bảng kê thành phẩm tái sử dụng được (tên, vị trí local, vị trí Drive/ID nếu có, SHA).
   - Danh sách việc máy công ty CẦN làm tiếp (tải gì về, đo gì lại vì index khác).
   - Danh sách việc máy công ty KHÔNG CẦN làm lại (đã xong ở nhà).
4. Chỉ đọc, không sửa/xóa thành phẩm, không nhúng lại, không ghi index.

## Tiêu chí nghiệm thu

- ĐẠT = báo cáo có đủ 3 bảng trên, số liệu SHA khớp với báo cáo R2, phân biệt rõ
  "tái dùng" vs "làm lại". Thiếu bảng nào cũng là CHƯA ĐẠT.
- Không merge `main`.
