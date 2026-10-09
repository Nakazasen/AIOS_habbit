# VÉ: OPEN-DIAG-XCHECK-PC0575 (kiểm chứng chéo độc lập kết quả vé chẩn đoán mở sổ)

- Mã vé: `OPEN-DIAG-XCHECK-PC0575`
- Role gợi ý: TINY (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/open-diag-xcheck-pc0575.md`
- Bối cảnh: vé `APP-OPEN-DIAG-PC0575` của thợ chính đã được duyệt đạt với kết quả mở lạnh sổ giảm từ khoảng 92 giây xuống khoảng 3 giây nhờ bộ nhớ đệm hai tầng cho trạng thái chỉ mục. Vé này là lượt kiểm chứng độc lập của thợ phụ: chạy lại và đo lại bằng tay của người khác, trên cùng máy, để xác nhận kết quả đứng vững ngoài phiên làm việc của thợ chính.

## Việc phải làm

1. Ghi mã commit đầu nhánh tại thời điểm kiểm chứng. Chạy lại tệp kiểm thử về trạng thái chỉ mục và ghi kết quả đầy đủ.
2. Tự đo lại bằng thao tác thật trên ứng dụng (khởi động lại ứng dụng trước khi đo): thời gian mở lạnh sổ MOM và sổ LSU tới khi gõ được câu hỏi, rồi thời gian mở ấm của hai sổ. Ghi số giây từng lượt vào báo cáo kèm tệp dữ kiện đo.
3. Kiểm tra tính an toàn của bộ nhớ đệm theo đúng thiết kế: xác nhận tệp đệm nằm ngoài tệp cơ sở dữ liệu chính; xác nhận băm của tệp chỉ mục không đổi trước và sau các lượt đo; thử tắt bộ nhớ đệm bằng biến môi trường đã công bố và đo lại một lượt mở lạnh để xác nhận đường hoàn lui hoạt động (số giây quay về mức chậm như trước khi sửa, không lỗi).
4. Đối chiếu toàn bộ số đo với báo cáo của thợ chính và ghi rõ mục nào khớp, mục nào lệch (nếu có) — không tự sửa gì trong vé này.

## Rào cứng

- Chỉ kiểm chứng: không sửa mã, không sửa kiểm thử, không ghi chỉ mục (băm trước/sau khớp). Không chạy việc nặng đồng thời với phiên ứng dụng của người dùng trên cùng máy — đo khi máy rảnh. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
