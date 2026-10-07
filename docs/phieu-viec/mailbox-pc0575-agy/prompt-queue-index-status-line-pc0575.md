# VÉ: INDEX-STATUS-LINE-PC0575 (dòng trạng thái chỉ mục trong khung chat)

- Mã vé: `INDEX-STATUS-LINE-PC0575`
- Role gợi ý: DEFAULT (code UI nhỏ + test)
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/index-status-line-pc0575.md`
- Điều kiện bốc vé: xếp hàng sau `RETRIEVAL-ENTITY-PC0575` — chỉ bắt đầu khi điều phối phát hành (vé hiện tại của mailbox đã xong-cho-duyet + có verdict).

## Bối cảnh

User kiểm chứng theo checklist ngày 07/10, mở app và nhận xét: trên giao diện không có chỗ nào cho biết app đang dùng tệp chỉ mục nào. Đúng sự thật: app chọn chỉ mục theo cấu hình cố định (ô chọn tay đã bỏ theo hướng chat-first tối giản — xem ghi chú trong code quanh `workspace_chat_app.py`). User duyệt bổ sung **một dòng trạng thái trong khung chat** để nhìn là biết app đang chạy trên chỉ mục nào. Không làm ô chọn, không thêm nút.

## Việc phải làm

1. Thêm **1 dòng trạng thái mảnh** (caption, chữ nhỏ/mờ) trong khung chat của `src/aios_habit/workspace_chat_app.py` — ngay trên vùng hội thoại hoặc dưới ô nhập, đúng 1 dòng, không nút bấm, không menu, không sidebar mới.
2. Nội dung dòng, lấy từ **chính chỉ mục app đang nạp** (không hardcode, không đọc nguồn khác):
   - Tên tệp chỉ mục (vd `workspace_chat.sqlite`).
   - Số tài liệu + số mảnh đếm trực tiếp từ DB đang mở (trên máy này kỳ vọng 889 tài liệu / 149.800 mảnh — lấy số thật lúc chạy, không gõ cứng).
   - Mã nhận diện rút gọn = 12 ký tự hex đầu của **vân tay logic**: SHA-256 trên danh sách đã sắp xếp của (mã tài liệu + vân tay nguồn từng tài liệu). Rẻ (889 dòng), ổn định khi SQLite chốt sổ — đây là thước chuẩn điều phối đã chốt ở vé SRC-SYNC thay cho MD5 thô của tệp.
   - Backend đang dùng (vd `ONNX fp32`).
   - Mẫu định dạng: `Kho đang dùng: workspace_chat.sqlite · 889 tài liệu · 149.800 mảnh · mã <12-hex> · ONNX fp32`.
3. **Trạng thái lỗi phải hiện rõ:** chỉ mục thiếu/không đọc được → dòng trạng thái hiện cảnh báo (vd `⚠ Không nạp được kho tri thức`), cấm im lặng để trống hoặc hiện số liệu cũ của phiên trước.
4. Số liệu tính 1 lần khi app nạp chỉ mục (cache theo phiên), không tính lại mỗi câu hỏi.

## Rào cứng

- CHỈ hiển thị: không đổi cách app chọn chỉ mục, không thêm ô chọn/nút/menu, không đụng logic retrieval/synthesis, không ghi index.
- Tương thích Python 3.11. Không merge `main`.
- Vòng cải thiện theo luật user: metric đo được = test khẳng định số hiển thị khớp số đọc trực tiếp từ DB; có test cho trạng thái lỗi.

## Kiểm chứng & báo cáo

- Unit test cho hàm dựng dòng trạng thái (DB giả lập: số đếm khớp đầu ra; DB thiếu → trạng thái cảnh báo).
- Cổng kiểm chứng theo AGENTS.md của repo: compileall + pytest liên quan + `cli audit` + import app.
- Chạy app thật trên PC0575: ghi lại dòng trạng thái hiển thị thực tế; đối chiếu số đếm bằng truy vấn DB độc lập và mã rút gọn bằng script tính vân tay logic độc lập — cả hai phải khớp tuyệt đối mới kết luận ĐẠT trong báo cáo.
