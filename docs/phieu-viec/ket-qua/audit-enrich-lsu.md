# Báo cáo kiểm tra 1.790 cặp LSU (vé AUDIT-ENRICH-LSU)

- Ngày làm: 2026-10-04 (buổi tối, máy thợ opencode).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-raw/lsu/` (39 tập tin, batch-16 đến batch-54; cùng 15 tập tin MOM batch-01..15 thành 54 tập tin toàn bộ như vé mô tả).
- Đích đã ghi: `docs/phieu-viec/chatgpt-enrichment-fixed/lsu/` (giữ nguyên cấu trúc 39 tập tin).
- Nguyên tắc giữ: chỉ sửa trong thư mục fixed, không đụng thư mục raw; mọi cặp giữ nhãn khối LSU và dòng trạng thái bản thảo chưa qua chuyên gia duyệt; giá trị `999`/`9999`/`0`/`--` chỉ giữ là Raw value, không tự gán nghĩa OK/NG; không nhập vào kho tri thức chính; không gộp vào nhánh main.

## Kết quả tổng

- Số cặp trước kiểm tra: 1.790 (Q609 đến Q2408, thiếu đúng Q639–Q648 bỏ trống có chủ đích vì `Thumbs.db`, không trùng số).
- Số cặp sau kiểm tra: 1.790.
- Số cặp đã sửa nội dung: 7 điểm trên 6 câu (Q853, Q1034, Q1076, Q1128, Q1131, Q1132, Q1136) + 1 ghi chú audit cho Q1124 (không bịa số).
- Số cặp loại bỏ: 0 (giữ lại toàn bộ để không mất bằng chứng; lý do chi tiết ở mục trùng lặp).
- Kiểm tra số thứ tự và định dạng: 39/39 tập tin đủ số cặp, Q liên tục (trừ dải trống có chủ đích), đủ 6 trường (Khối, Ngôn ngữ, Bối cảnh, Cách hỏi, Hỏi, Đáp kèm nguồn file), 0 lỗi thiếu trường. Ngôn ngữ: Việt 610, Trung 605, Nhật 575. Cách hỏi sau sửa: trực tiếp 398, tình huống 356, xử lý sự cố 329, hỏi ngược kiểm tra hiểu 328, so sánh 379.

## Lỗi đã biết trong vé và cách xử lý

1. Q853 (batch-21), Q1034 (batch-25), Q1076 (batch-26): trường "Cách hỏi" bản raw ghi nhầm chữ ngoại ngữ "直接". Đã sửa cả 3 thành "trực tiếp" (cả 3 đều là câu hỏi sự thật trực tiếp, khớp ngữ cảnh).
2. Q1131, Q1132, Q1136 (batch-27): trường "Cách hỏi" bị agent chép lại dạng diễn giải trong ngoặc đơn khi thu hồi nguyên văn. Đã tách lấy giá trị lõi: Q1131 → trực tiếp, Q1132 → so sánh, Q1136 → so sánh.
3. Q1128 (batch-27): trường "Hỏi" chỉ là câu giữ chỗ meta của agent ("Câu hỏi về việc có được tự định nghĩa 999 không — trường này được agent diễn giải lại khi thu hồi"). Đã khôi phục câu hỏi tiếng Trung đúng ngữ cảnh từ Bối cảnh + Đáp: hỏi có được tự định nghĩa 999 thành "không dò được Beam" không; Đáp giữ nguyên (không được tự gán nghĩa).
4. Q1124 (batch-27): Đáp raw ghi dở "-1 và ±0 theo file" (thiếu số). Không bịa số; đã giữ nguyên giá trị -2=57 là Raw value và thêm ghi chú audit nêu rõ -1/±0 thiếu số trong bản raw.
5. Vé yêu cầu chấm bằng 6 mô đun `src/aios_habit/golden_question_*.py`, nhưng kho hiện chỉ có 5 mô đun (export, generator, quality, schema, scorer). Không có mô đun thứ sáu (ghi nhận giống vé MOM).
6. Giá trị `999`/`9999`/`0`/`--`: đã quét toàn bộ 1.790 cặp, không phát hiện gán nghĩa sai. Các cặp hỏi trực diện về 999 (ví dụ Q757, Q1568) đều trả lời đúng "chỉ giữ Raw value, không tự kết luận NG"; Q1175 chứa "9999" trong số serial (không phải raw value) nên không vi phạm.

## Trùng lặp nội dung

- Trùng nguyên văn cả Hỏi + Đáp (chuẩn hóa, không phân biệt hoa/thường/khoảng trắng): 0 nhóm. Không xóa cặp nào.
- Trùng nguyên văn chỉ câu Hỏi: 51 nhóm (mẫu câu tái sử dụng qua nhiều file, ví dụ cùng mẫu "Serial xuất hiện nhiều nhất" áp cho các CSV khác nhau). Vì Đáp khác nhau (số liệu và nguồn file khác nhau), giữ lại toàn bộ để không mất bằng chứng theo từng file, chỉ ghi nhận chồng lấn mẫu câu trong báo cáo này.
- Nhóm vé nêu: mẻ 39 (~30/50 cặp lặp ý "Raw value 0" vì Yellow/Magenta Profile toàn waveform 0), các batch Sirius2 chỉ có `999`/`0`/`--`, các cặp hỏi cùng record/ngưỡng khác diễn đạt, mẻ 28 (CamError 1 record, Q1139–1148 trùng cao). Kiểm tra thực tế: đây là các câu hỏi song song trên các kênh/file/record khác nhau, Đáp ghi số liệu riêng từng kênh và đều giữ Raw value không gán nghĩa. Không phát hiện cặp nào trùng cả Hỏi lẫn Đáp nên không loại; các cặp hỏi ngược (ví dụ Q757, Q1568, Q1128) chính là rào chống diễn giải sai, cần giữ lại.
- Nhật ký cặp loại bỏ: không có cặp nào bị loại.

## Chấm chất lượng M1 đến M5

- Cách chấm: dùng trực tiếp 5 mô đun hiện có thì mô đun chấm điểm và đo chất lượng được thiết kế cho câu hỏi vàng phỏng vấn, không khớp trực tiếp với cặp hỏi đáp làm giàu kiến thức. Vì vậy báo cáo này đo ánh xạ trung thực như sau và không bịa số (giống vé MOM).
- M3 (đầy đủ biểu mẫu): trước sửa 1.790/1.790 đủ 6 trường (100%), sau sửa vẫn 1.790/1.790 (100%). Tỉ lệ đáp án có số liệu là 1.772/1.790 (99,0%), toàn bộ 1.790 đáp án đều ghi rõ nguồn file.
- M4 (phân biệt giả thuyết, ước lượng bằng tỉ lệ cặp Hỏi+Đáp khác nhau): trước và sau sửa đều 1.790/1.790 tổ hợp khác nhau (100%, 0 nhóm trùng nguyên văn cả Hỏi lẫn Đáp).
- M1 (độ phủ khoảng trống tri thức), M2 (truy hồi tốp 5) và M5 (độ lệch sau duyệt chuyên gia): chưa đo được trong vòng này vì cần ảnh chụp chỉ mục thật và cần chuyên gia duyệt thật. Vé cấm nhập vào kho chính nên không chạy truy hồi trên chỉ mục thật. Đề nghị đo ba chỉ số này ở vòng có chuyên gia.
- Vòng xem lại sau sửa: đã chạy lại kiểm tra toàn bộ thư mục fixed, kết quả 1.790 cặp, đủ 6 trường, số thứ tự liên tục Q609 đến Q2408 (thiếu đúng Q639–Q648 có chủ đích), 0 nhóm trùng nguyên văn cả Hỏi lẫn Đáp, 0 giá trị Cách hỏi ngoại ngữ trong các trường câu hỏi.

## Danh sách tập tin đã ghi trong thư mục fixed

- batch-16.md (40), batch-17.md (50), batch-18.md (30), batch-19.md (50), batch-20.md (30), batch-21.md (50), batch-22.md (50), batch-23.md (40), batch-24.md (50), batch-25.md (50), batch-26.md (50), batch-27.md (30), batch-28.md (50), batch-29.md (50), batch-30.md (20), batch-31.md (50), batch-32.md (50), batch-33.md (50), batch-34.md (50), batch-35.md (50), batch-36.md (50), batch-37.md (50), batch-38.md (50), batch-39.md (50), batch-40.md (50), batch-41.md (50), batch-42.md (50), batch-43.md (50), batch-44.md (50), batch-45.md (50), batch-46.md (50), batch-47.md (50), batch-48.md (50), batch-49.md (30), batch-50.md (50), batch-51.md (40), batch-52.md (50), batch-53.md (50), batch-54.md (30).
- Thay đổi nội dung: batch-21 (Q853), batch-25 (Q1034), batch-26 (Q1076), batch-27 (Q1124 ghi chú, Q1128, Q1131, Q1132, Q1136). Các tập tin còn lại chỉ thêm dòng trạng thái bản thảo ở đầu tập tin, nội dung cặp hỏi đáp giữ nguyên bản raw.
- Nhật ký cặp loại bỏ: không có cặp nào bị loại.

## Kiểm tra cổng kỹ thuật

- Biên dịch `compileall src tests`: qua.
- Kiểm thử nhóm câu hỏi vàng (`pytest -q -k "golden"`): 48 bài qua.
- Bộ kiểm thử đầy đủ (`pytest -q`): chưa chạy hết trong vòng này (bộ đầy đủ rất lâu; thay đổi trong vòng này chỉ là tập tin tài liệu fixed + báo cáo nên không ảnh hưởng mã nguồn; đã chạy nhóm liên quan golden).
- Lệnh `python -m aios_habit.cli audit`: trạng thái PASS (ghi chú môi trường: cần đặt `PYTHONPATH=src` vì gói chưa cài vào môi trường ảo; lệnh gốc trong quy tắc agent không tự tìm thấy gói).
- Lệnh `import aios_habit.workspace_chat_app`: thành công.
