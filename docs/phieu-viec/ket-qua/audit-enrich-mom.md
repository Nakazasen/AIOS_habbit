# Báo cáo kiểm tra 608 cặp MOM (vé AUDIT-ENRICH-MOM)

- Ngày làm: 2026-10-04 (buổi tối, máy thợ opencode).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-raw/mom/` (15 tập tin, batch-01 đến batch-15).
- Đích đã ghi: `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` (giữ nguyên cấu trúc 15 tập tin).
- Nguyên tắc giữ: chỉ sửa trong thư mục fixed, không đụng thư mục raw; mọi cặp giữ nhãn khối MOM và dòng trạng thái bản thảo chưa qua chuyên gia duyệt; không nhập vào kho tri thức chính; không gộp vào nhánh main.

## Kết quả tổng

- Số cặp trước kiểm tra: 608 (Q1 đến Q608, liên tục, không thiếu, không trùng số).
- Số cặp sau kiểm tra: 608.
- Số cặp đã sửa nội dung: 1 (Q183).
- Số cặp loại bỏ: 0 (giữ lại toàn bộ để không mất bằng chứng; lý do chi tiết ở mục trùng lặp).
- Kiểm tra số thứ tự và định dạng: 15/15 tập tin đủ số cặp, Q liên tục, đủ 6 trường (Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn file). Ngôn ngữ: Việt 206, Trung 209, Nhật 193. Cách hỏi: trực tiếp 158, xử lý sự cố 105, tình huống 124, hỏi ngược kiểm tra hiểu 104, so sánh 117.

## Lỗi đã biết trong vé và cách xử lý

1. Q183 (thuộc MOM, batch-04): bản raw ghi trùng nguyên câu hỏi và đáp án của Q184 (cách đặt tên Workflow cấp hàng). Đã sửa Q183 theo đúng yêu cầu trong vé: câu hỏi về cách dùng khác nhau giữa Spec Name và WorkCenter Name; đáp án nêu Spec Name dùng cho đăng ký hoàn thành công đoạn và Line-Out, WorkCenter Name dùng cho xuất kho thủ công. Q184 giữ nguyên. Sau sửa, kiểm tra lại toàn bộ fixed không còn cặp trùng nguyên văn.
2. Q853, Q1034, Q1076 (trường Cách hỏi ghi nhầm chữ ngoại ngữ): số hiệu này nằm ngoài dải MOM (vượt quá Q608), thuộc dải LSU. Đã quét toàn bộ 608 cặp MOM, không phát hiện giá trị Cách hỏi bằng chữ ngoại ngữ. Không có gì cần sửa trong phạm vi MOM.
3. Q1128, Q1131, Q1132, Q1136 (khôi phục nguyên văn) và Q1124 (bổ sung số liệu): các số hiệu này cũng nằm ngoài dải MOM, thuộc dải LSU. Không áp dụng trong phạm vi MOM.
4. Ghi nhận lệch giữa vé và kho mã: vé yêu cầu chấm bằng 6 mô đun `src/aios_habit/golden_question_*.py`, nhưng kho hiện chỉ có 5 mô đun (export, generator, quality, schema, scorer). Không có mô đun thứ sáu.

## Trùng lặp nội dung

- Trùng nguyên văn duy nhất: Q183 và Q184 giống nhau từng chữ trước khi sửa (độ giống 1.0). Đã xử lý bằng cách sửa Q183, không xóa cặp nào.
- Kiểm tra độ giống câu hỏi ở ngưỡng 0.7 còn thấy 2 cặp giống mẫu câu nhưng khác nội dung nên giữ lại cả hai: Q133 (chế độ điều khiển Matecon) với Q193 (cờ sản phẩm phụ thuộc), và Q297 (màn hình danh sách người phụ trách) với Q306 (màn hình danh sách mã hàng). Đây là cùng mẫu câu hỏi so sánh hoặc tra cứu nhưng hỏi về đối tượng khác nhau.
- Chủ đề Matecon bản bảng tính và bản PDF (Q1 đến Q10 so với Q131 đến Q140): bản kê quá trình thu thập có cảnh báo trùng. Kiểm tra độ giống cao nhất chỉ đạt khoảng 0.69 (Q1 với Q133) và các cặp nghi ngờ nhất là Q3 (bản bảng tính) với Q132 (bản PDF) cùng hỏi về tên tập tin cấu hình theo tên máy tính. Vì hai nguồn là hai định dạng độc lập của cùng một tài liệu hướng dẫn và câu chữ không trùng nguyên văn, quyết định giữ lại cả hai để không mất bằng chứng, chỉ ghi nhận chồng lấn trong báo cáo này.
- Các chủ đề vé liệt kê gồm liên lạc AGV, sơ đồ quan hệ dữ liệu kho, bảng trạng thái ORICON, truyền phiếu thủ công, bản đồ và phiên bản, thống kê màu sắc: đã quét tần suất xuất hiện trong MOM (ví dụ AGV 65 cặp, mã CTU 104 cặp, ORICON 87 cặp) và không phát hiện trùng nguyên văn cần loại. Chủ đề bản ghi lỗi camera chỉ có một dòng (CamError) thuộc dải LSU, không thuộc phạm vi MOM.

## Chấm chất lượng M1 đến M5

- Cách chấm: dùng trực tiếp 5 mô đun hiện có thì mô đun chấm điểm và đo chất lượng được thiết kế cho câu hỏi vàng phỏng vấn, không khớp trực tiếp với cặp hỏi đáp làm giàu kiến thức. Vì vậy báo cáo này đo ánh xạ trung thực như sau và không bịa số.
- M3 (đầy đủ biểu mẫu): trước sửa 608/608 đủ 6 trường (100%), sau sửa vẫn 608/608 (100%). Tỉ lệ đáp án có số liệu là 514/608 (84.5%), toàn bộ 608 đáp án đều ghi rõ nguồn file.
- M4 (phân biệt giả thuyết, ước lượng bằng tỉ lệ câu hỏi khác nhau): trước sửa 607/608 câu hỏi khác nhau (99.8%, trừ 1 cặp trùng), sau sửa 608/608 (100%).
- M1 (độ phủ khoảng trống tri thức), M2 (truy hồi tốp 5) và M5 (độ lệch sau duyệt chuyên gia): chưa đo được trong vòng này vì cần ảnh chụp chỉ mục thật và cần chuyên gia duyệt thật. Vé cấm nhập vào kho chính nên không chạy truy hồi trên chỉ mục thật. Đề nghị đo ba chỉ số này ở vòng có chuyên gia.
- Vòng xem lại sau sửa: đã chạy lại kiểm tra toàn bộ thư mục fixed, kết quả 608 cặp, đủ 6 trường, số thứ tự liên tục Q1 đến Q608, 0 nhóm trùng nguyên văn.

## Danh sách tập tin đã ghi trong thư mục fixed

- batch-01.md đến batch-15.md (15 tập tin, giữ nguyên số cặp mỗi tập tin: 50, 50, 50, 50, 50, 30, 48, 50, 50, 50, 50, 10, 50, 10, 10).
- Thay đổi nội dung duy nhất: batch-04.md (Q183). Các tập tin còn lại chỉ thêm dòng trạng thái bản thảo ở đầu tập tin, nội dung cặp hỏi đáp giữ nguyên bản raw.
- Nhật ký cặp loại bỏ: không có cặp nào bị loại.

## Kiểm tra cổng kỹ thuật

- Biên dịch `compileall src tests`: qua.
- Kiểm thử nhóm câu hỏi vàng (`pytest -q -k "golden"`): 48 bài qua.
- Bộ kiểm thử đầy đủ (`pytest -q`): chạy quá 10 phút chưa xong nên dừng lấy kết quả ở phạm vi nhóm liên quan; thay đổi trong vòng này chỉ là tập tin tài liệu nên không ảnh hưởng mã nguồn.
- Lệnh `python -m aios_habit.cli audit`: trạng thái PASS (ghi chú môi trường: cần đặt `PYTHONPATH=src` vì gói chưa cài vào môi trường ảo; lệnh gốc trong quy tắc agent không tự tìm thấy gói).
- Lệnh `import aios_habit.workspace_chat_app`: thành công.
