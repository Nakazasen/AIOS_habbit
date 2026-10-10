# VÉ: MAILBOX-MOVE-WATCHER-CUT-HOME-OPENCODE (cắt chương trình trông coi của hộp thư opencode máy nhà sang kho điều phối)

- Mã vé: `MAILBOX-MOVE-WATCHER-CUT-HOME-OPENCODE`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy nhà h410asrock). Việc nhẹ, không gọi mô hình nặng.
- Báo cáo: bước cuối ghi thẳng vào hộp thư tại kho mới (xem việc 4); ở kho dự án chỉ cần đặt trạng thái `xong-cho-duyet` kèm một dòng tổng kết vào `trang-thai.md` sau khi bước cuối ở kho mới xong.
- Bối cảnh: vé `MAILBOX-MOVE-HOME-OPENCODE` đã đủ hai dấu — bạn xác nhận tại commit `f9703a7` trên kho `aios-dieu-phoi`, điều phối đã kiểm chứng và ghi duyệt kèm điều kiện: chương trình trông coi (watcher) chưa được cắt sang bản clone mới. Ghi chú của bạn đã nêu đúng điểm khó: tác vụ `MailboxWatcher-opencode` hiện gọi tệp lệnh `D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1` với thư mục hộp thư ở kho mã nguồn, và tệp cấu hình `config.local.ps1` là cấu hình CHUNG cho cả watcher của OMP và agy. Vé này xử lý riêng khâu cắt đó.

## Việc phải làm

1. Đọc lại cách watcher hiện hành được cấu hình (tác vụ theo lịch `MailboxWatcher-opencode`, tham số của tệp lệnh trông coi, phần liên quan trong `config.local.ps1`). Chụp lại cấu hình gốc vào báo cáo trước khi sửa, để hoàn lui được.
2. Cắt watcher của RIÊNG hộp thư opencode sang bản clone mới: hộp thư hiệu lực từ nay là `hop-thu\mailbox-opencode` trong `D:\Sandbox\aios-dieu-phoi` (nhánh `main`). Cách làm do bạn chọn (thêm một tác vụ trông coi riêng cho đường dẫn mới, hoặc thêm một mục cấu hình riêng cho hộp thư này) với điều kiện cứng: không đổi hành vi của watcher OMP và watcher agy — hai watcher đó vẫn trỏ kho mã nguồn như cũ; nếu cấu trúc cấu hình chung không cho phép tách riêng mà không đụng hai watcher kia, DỪNG và ghi rõ điểm gãy vào `trang-thai.md` ở kho dự án, không sửa liều.
3. Kiểm chứng cắt thành công: watcher mới phải thực sự chạy và đọc được hộp thư ở kho mới — bằng chứng là mốc kiểm chứng ở việc 4 được watcher bốc lên xử lý, hoặc nhật ký của watcher ghi rõ chu kỳ chạy trên đường dẫn mới. Ghi mã commit của bản clone tại thời điểm kiểm chứng.
4. Bước cuối (bằng chứng hoàn thành + đóng băng kênh cũ): ghi vào `trang-thai.md` của hộp thư tại kho MỚI một khối trạng thái `xong-cho-duyet` cho chính vé này, kèm dòng tổng kết (thời gian cắt, cách cắt, bằng chứng watcher chạy ở đường dẫn mới, cách hoàn lui). Đẩy lên kho `aios-dieu-phoi`. Sau đó quay lại hộp thư ở kho dự án, đặt trạng thái `xong-cho-duyet` kèm một dòng "đã chuyển kênh — xem hộp thư tại kho aios-dieu-phoi". Từ mốc này bạn chỉ nhận vé tại kho mới.

## Rào cứng

- Không sửa cấu hình/hành vi của watcher OMP và watcher agy.
- Không xoá tác vụ trông coi cũ cho tới khi watcher mới đã kiểm chứng chạy được; giữ cách hoàn lui rõ ràng trong báo cáo.
- Không đụng chỉ mục production, không merge nhánh nào.
- Kích thước tệp (nếu có nêu) đo trên bản đã nộp vào kho sau khi commit.
