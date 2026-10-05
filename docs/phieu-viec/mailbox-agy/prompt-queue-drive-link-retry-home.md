# VÉ: DRIVE-LINK-RETRY-HOME (lấy nốt 2 link chia sẻ Drive + dọn file tạm)

- Mã vé: `DRIVE-LINK-RETRY-HOME`
- Role OMP gợi ý: SMOL (việc kiểm tra nhanh, không upload lại)
- Máy: nhà h410asrock
- Báo cáo: cập nhật `docs/phieu-viec/ket-qua/upload-split-drive-home.md` (thêm mục bổ sung, không viết lại)

## Bối cảnh

Vé `UPLOAD-SPLIT-DRIVE-HOME` đã ĐẠT (05/10 ~23:39): 5/5 file (~2,66GB) đã nằm trên
Drive, SHA-256 khớp local 100%. Còn 2 điểm dở dang ghi trong verdict:
1. 2/5 link chia sẻ (khối LSU, khối Dieu-tra-loi) chưa lấy được ID — Drive báo
   "không thể chia sẻ vào thời điểm này" trong khung 21:45–23:16 ngày 05/10.
2. File tải về để kiểm chứng (~2,8GB trong `C:\temp\verify_*`) thợ hẹn xóa sau
   duyệt cho gọn ổ C.

## Việc cần làm

1. Thử lấy lại ID/link chia sẻ cho 2 file còn thiếu (LSU ~1,16GB, Dieu-tra-loi
   ~1,64GB) trong thư mục `index-split-r5-backup` trên Drive. Nếu Drive vẫn chặn,
   ghi trung thực "Drive vẫn chưa cho chia sẻ lúc <giờ>" — không bịa ID.
2. Kiểm tra nhanh cả 5 file vẫn còn trên Drive (tên + dung lượng khớp báo cáo cũ).
3. Xóa các file tạm `C:\temp\verify_*` (file thợ tự tải về để đối chiếu — bản gốc
   vẫn còn đủ trên Drive và local, xóa an toàn). Chỉ xóa đúng các file verify_*,
   không đụng gì khác trong C:\temp.
4. Bổ sung vào báo cáo cũ một mục "Bổ sung ngày 06/10": 2 link (hoặc lý do chưa
   lấy được) + xác nhận 5 file còn nguyên + đã xóa file tạm giải phóng ~2,8GB.

## Tiêu chí nghiệm thu

- ĐẠT = đã thử lấy 2 link (có link hoặc lý do trung thực vì sao chưa) + 5 file
  xác nhận còn nguyên + file tạm đã xóa + báo cáo được bổ sung.
- Không upload lại, không xóa file local/Drive. Không merge `main`.
