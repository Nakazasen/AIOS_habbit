# VÉ: TEST-NESTED-GUARD-SCAN-HOME (rà soát các ca kiểm thử còn lại có cùng mẫu chập chờn theo môi trường)

- Mã vé: `TEST-NESTED-GUARD-SCAN-HOME`
- Role gợi ý: TINY (opencode — thợ phụ tạm thời, máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/test-nested-guard-scan-home.md`
- Bối cảnh: ca đóng gói đầu-cuối vừa được bịt điểm chập chờn bằng hai điều kiện bỏ qua rõ ràng (thiếu thư mục model tại máy; lượt kiểm thử lồng hết giờ vì tốc độ máy). Trước khi coi tín hiệu của bộ kiểm thử là sạch bền vững, cần rà soát toàn bộ thư mục kiểm thử xem còn ca nào có cùng mẫu rủi ro mà chưa được bảo vệ hay không, để các lượt chạy sau không lại bất ngờ đỏ vì điều kiện máy.

## Việc phải làm

1. Rà toàn bộ các tệp trong thư mục kiểm thử, tìm các ca có một trong các mẫu sau:
   - Gọi tiến trình con có trần thời gian cứng (dạng chạy lệnh ngoài kèm giới hạn giây) mà không có xử lý cho trường hợp hết giờ.
   - Phụ thuộc vào thư mục model hoặc tệp dữ liệu chỉ có ở một số máy mà không có điều kiện bỏ qua khi vắng mặt.
   - Khẳng định bằng số tuyệt đối gắn với một máy cụ thể (kích thước tệp, số lượng cố định của kho máy khác) thay vì quan hệ.
2. Lập bảng kết quả trong báo cáo: tên ca, tệp, mẫu rủi ro thuộc loại nào, đã có điều kiện bảo vệ hay chưa, và mức độ cần xử lý theo ý kiến của thợ.
3. **Không sửa bất kỳ tệp nào trong vé này** — chỉ rà soát và báo cáo; phần sửa do điều phối quyết định và phát hành riêng sau khi xem bảng.

## Rào cứng

- Chỉ đọc và báo cáo: không sửa mã, không sửa kiểm thử, không ghi chỉ mục, không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần nếu việc rà soát kéo dài.
