# Ticket P5b — Kiểm tra lại truy cập app trên mạng mới

## Bối cảnh
- Vé P5 đã ĐẠT trên mạng công ty cũ (app mở ở `192.168.1.41:8501`, máy khác truy cập được).
- Máy đã chuyển sang mạng ngoài → IP đổi, Windows Firewall có thể áp luật khác → cần kiểm tra lại truy cập từ máy khác.

## Việc cần làm
1. Ghi lại mạng hiện tại: tên WiFi/mạng + địa chỉ IP hiện tại của máy (chạy `ipconfig`, lấy dòng IPv4).
2. Kiểm tra app còn chạy không: mở trình duyệt ngay trên máy, vào `http://127.0.0.1:8501`.
   - Vào được → ghi nhận. Không vào được → khởi động lại app theo runbook cũ rồi làm tiếp.
3. Từ một máy khác (điện thoại hoặc máy tính khác, **cùng mạng mới**): mở `http://<IP-của-máy>:8501`.
   - Vào được → chụp màn hình. Không vào được → ghi rõ thông báo lỗi hiện ra.
4. Nếu máy khác không vào được: kiểm tra Windows Firewall đã có rule mở port 8501 chưa. Không tự tắt firewall diện rộng.
5. Báo cáo: `docs/phieu-viec/ket-qua/p5b-mang-moi.md` — IP mới, link truy cập, kết quả từ máy khác, ảnh chụp màn hình.

## Cấm
- Không tải lại model, không embed lại, không ghi/sửa index production.
- Không merge `main`. Không đụng ổ D máy nhà. Không tắt hẳn firewall.
