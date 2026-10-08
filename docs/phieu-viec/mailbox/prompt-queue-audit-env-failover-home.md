# VÉ NHỎ: AUDIT-ENV-FAILOVER-HOME (kiểm nhất quán cấu hình tuyến tổng hợp sau khi áp 3 tầng)

- Mã vé: `AUDIT-ENV-FAILOVER-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà, chỉ đọc cấu hình)
- Báo cáo: `docs/phieu-viec/ket-qua/audit-env-failover-home.md`
- Căn cứ: sau vé `CONFIG-SYNTH-TIERS-HOME` (đã verdict ĐẠT phần cấu hình), cấu hình tuyến tổng hợp tại máy nhà đã đổi sang chuỗi 3 tầng. Vé này kiểm độc lập tính nhất quán của cấu hình hiện tại so với cấu hình đã chốt, và rà các biến sót/mâu thuẫn còn sót từ các giai đoạn trước.

## Việc phải làm (chỉ ở mức TÊN biến và giá trị KHÔNG NHẠY CẢM như tên model/cờ bật-tắt — tuyệt đối không chép bất kỳ giá trị khóa/API key nào)

1. Liệt kê các biến liên quan tuyến tổng hợp đang có mặt trong tệp cấu hình môi trường tại máy nhà (chỉ tên biến): biến model chính, biến chuỗi dự phòng, biến công tắc cho phép nhà cung cấp bên ngoài, cờ hợp đồng trích dẫn nghiêm ngặt, các biến failover/giới hạn lượt thử nếu có.
2. Đối chiếu: model chính + thứ tự chuỗi dự phòng có đúng cấu hình chốt (Ling 3.1 chính → Laguna → DeepSeek) không; có biến nào mâu thuẫn nhau (ví dụ hai nơi cùng định nghĩa model chính khác nhau, biến cũ từ các lượt đo tạm còn sót và đang có hiệu lực) không.
3. Kiểm tệp sao lưu cấu hình trước khi đổi của vé 3 tầng có tồn tại và khớp phần nó ghi không.
4. Ghi chú thời điểm: vé mở cổng tổng hợp cho giao diện chưa chạy tại thời điểm kiểm này — nếu công tắc cho phép nhà cung cấp bên ngoài đang TẮT thì đó là trạng thái ĐÚNG tại thời điểm kiểm, không tính là lệch; ghi rõ để đối chiếu lại sau khi vé mở cổng chạy.
5. Kết luận: cấu hình nhất quán hay có điểm nào cần dọn — liệt kê cụ thể tên biến cần dọn (không tự sửa).

## Rào cứng

- Chỉ đọc; không sửa bất kỳ biến nào, không chạy lại lượt đo, không đụng chỉ mục. Không merge `main`.
- Báo cáo ngắn dạng bảng. Tuyệt đối không in bất kỳ ký tự nào của khóa vào báo cáo/log/commit.
