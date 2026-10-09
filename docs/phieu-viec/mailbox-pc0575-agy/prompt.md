# VÉ: QA-CONTEXT-DIAG-PC0575 (chẩn đoán và sửa lỗi báo "Thiếu ngữ cảnh" với câu hỏi khái niệm cơ bản trong khối đã chọn)

- Mã vé: `QA-CONTEXT-DIAG-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/qa-context-diag-pc0575.md`
- Bối cảnh: lúc 21:29 ngày 09/10, người dùng dùng thật tại máy công ty: tạo sổ mới thành công, chọn khối tri thức MOM (44 tài liệu), hỏi câu "WMS là gì?" — ứng dụng báo "Thiếu ngữ cảnh — Chưa có nguồn nào." và không tạo ra đáp án nào. Đây là lỗi trải nghiệm người dùng gặp trực tiếp trên đường hỏi đáp chính. Nhãn báo nằm ở `src/aios_habit/workspace_chat_ui.py` (hàm dựng huy hiệu "Thiếu ngữ cảnh", khoảng dòng 1573) và khoá ngôn ngữ `insufficient_context` / `no_sources` trong `src/aios_habit/i18n.py`.

## Việc phải làm

1. Tái hiện tại máy với đúng câu hỏi "WMS là gì?" và đúng khối MOM, ở chế độ chỉ dùng bộ xử lý trung tâm. Phân rã toàn đường: truy hồi thô trên toàn kho cho câu này ra bao nhiêu mảnh; riêng trong khối MOM ra bao nhiêu mảnh; khâu nào làm số nguồn về 0 — lọc khối theo mã tài liệu, ngưỡng điểm truy hồi, cổng kiểm chứng bằng chứng, hay phân loại ý định. Ghi số đếm từng khâu vào báo cáo.
2. Sửa gốc ở khâu gây ra, theo nguyên tắc: câu hỏi khái niệm cơ bản trong khối đã chọn phải nhận được đáp án có trích dẫn từ tài liệu thuộc khối, chừng nào tài liệu trong khối thật sự có nội dung liên quan. Nếu sau phân rã thấy tài liệu trong khối thật sự không có nội dung về chủ đề được hỏi, sửa phần thông báo để nói đúng sự thật đó (phân biệt rõ "khối đã chọn không có tài liệu về chủ đề này" với tình trạng lỗi hệ thống) thay vì một thông báo chung chung. Mọi thay đổi về ngưỡng phải có số đếm phân rã chống lưng và kiểm thử bảo vệ kèm cờ hoàn lui.
3. Nghiệm thu dùng thật qua giao diện: hỏi lại đúng câu "WMS là gì?" trong khối MOM; hỏi thêm 2 câu khái niệm tương tự, mỗi câu trong một khối khác (Điều tra lỗi và LSU). Nộp đáp án nguyên văn và ảnh chứa đáp án trong khung hình cho cả 3 câu. Ghi rõ mã commit đang chạy.

## Rào cứng

- Không ghi vào chỉ mục chính. Không nới cổng kiểm chứng bằng chứng vô căn cứ — cổng này là chủ đích an toàn, chỉ chỉnh khi dữ kiện phân rã chỉ rõ khâu chặn oan.
- Không chạy phiên đo đồng thời với phiên ứng dụng của người dùng trên cùng máy (lệnh khẩn của điều phối): đo khi người dùng không đang dùng ứng dụng, nếu chưa được thì ghi mốc chờ.
- Mốc tiến độ tối thiểu 15 phút/lần.
