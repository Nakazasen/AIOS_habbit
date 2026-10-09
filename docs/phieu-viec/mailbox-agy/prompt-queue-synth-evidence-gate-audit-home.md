# VÉ: SYNTH-EVIDENCE-GATE-AUDIT-HOME (rà ngưỡng độ phủ từ khoá của cổng kiểm chứng bằng chứng cho câu chẩn đoán ngắn)

- Mã vé: `SYNTH-EVIDENCE-GATE-AUDIT-HOME`
- Role gợi ý: PLAN (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-evidence-gate-audit-home.md`
- Bối cảnh: báo cáo điều tra `docs/phieu-viec/ket-qua/synth-intent-audit-home.md` đã xác định một nhóm câu không được gọi mô hình vì cổng kiểm chứng bằng chứng chặn trước (cơ chế chặn đóng kín tại `synthesis.py`, khoảng dòng 954–955). Cổng này là chủ đích an toàn — thà không trả lời còn hơn trả lời thiếu bằng chứng — nên không được nới bừa. Đề xuất thứ hai của báo cáo điều tra là rà lại ngưỡng độ phủ từ khoá của cổng đối với các câu chẩn đoán ngắn: câu hỏi chẩn đoán thường ngắn, ít từ khoá, nên có thể đang bị chặn oan dù bằng chứng truy hồi được là đủ dùng.

## Việc phải làm

1. Đo phân bố thực tế từ các tệp dữ kiện đo đã có: với mọi câu từng bị cổng chặn, trích độ phủ từ khoá đã tính, độ dài câu hỏi, và bằng chứng truy hồi được đi kèm. Phân nhóm: câu chẩn đoán ngắn và các nhóm còn lại.
2. Chấm lại bằng tay có căn cứ một mẫu đại diện trong nhóm bị chặn: với từng câu mẫu, đọc bằng chứng truy hồi được và kết luận bằng chứng đó đủ hay không đủ để trả lời có trích dẫn. Đây là căn cứ duy nhất để bàn về ngưỡng — không suy luận từ độ phủ một mình.
3. Mô phỏng trên dữ kiện có sẵn: nếu hạ ngưỡng độ phủ cho nhóm câu chẩn đoán ngắn xuống các mức ứng viên thì có bao nhiêu câu được thả, và trong số đó bao nhiêu câu thuộc nhóm "bằng chứng đủ" theo bước 2, bao nhiêu câu thuộc nhóm "bằng chứng không đủ". Chỉ đề xuất mức ngưỡng khi mô phỏng cho thấy không thả lọt câu thiếu bằng chứng trong mẫu đã rà.
4. Nếu và chỉ nếu bước 3 cho kết quả sạch: áp thay đổi ngưỡng cho đúng nhóm câu chẩn đoán ngắn, kèm kiểm thử bảo vệ (câu thiếu bằng chứng vẫn bị chặn; câu đủ bằng chứng được thả) và cờ hoàn lui bằng biến môi trường. Sau khi áp, đo lại đủ 50 câu tại máy nhà, chỉ dùng bộ xử lý trung tâm, và so sánh từng câu với mốc gần nhất tại thời điểm vé chạy. Nếu bước 3 không sạch: không áp gì cả, báo cáo kết luận giữ nguyên ngưỡng kèm dữ kiện.

## Lưu ý thực tế về tài khoản mô hình

Tài khoản dùng chung đang ở gần trần tuần và trần tháng. Nếu lượt đo ở bước 4 gặp lượt gọi bị từ chối tạm thời: ghi mốc, chờ một nhịp rồi chạy tiếp bằng khả năng chạy tiếp của trình đo, không bỏ dở vé và không đổi sang mô hình ngoài chuỗi đã chốt.

## Rào cứng

- Cổng kiểm chứng là cơ chế an toàn đóng kín: mọi thay đổi phải có dữ kiện mô phỏng chống lưng và khả năng hoàn lui, như mô tả ở trên. Không ghi vào chỉ mục production. Không đổi bộ đề và thang chấm. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để chạy tiếp được.
