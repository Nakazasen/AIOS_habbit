# VÉ: RAG-REMEASURE-AFTER-SRC-PC0575 (đo lại đường hỏi đáp cục bộ tại máy công ty sau khi chỉ mục đã nạp đủ nguồn)

- Mã vé: `RAG-REMEASURE-AFTER-SRC-PC0575`
- Role gợi ý: DEFAULT (agy — thợ chính, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/rag-remeasure-after-src-pc0575.md`
- Điều kiện mở vé: vé `SRC-RECEIVE-2GOI-PC0575` đã hoàn tất và chỉ mục đã đứng yên (không còn làn ghi nào). Vé này nằm trong hàng chờ của hộp thư — chỉ bắt đầu khi điều phối phát hành sau khi vé nhận gói được duyệt.
- Bối cảnh: lượt đo chuẩn gần nhất tại máy công ty (vé rà soát đo lại ngày 09/10) cho điểm đường hỏi đáp cục bộ 0,957 trên thang 3 — dưới ngưỡng go-live 1,5 — trong khi chỉ mục khi đó còn thiếu nguồn: nhiều tài liệu chưa có thông tin nguồn và dấu vân tay gắn kèm. Vé nhận gói vừa nạp đủ phần còn thiếu và gắn lại thông tin nguồn cho hàng chục nghìn mảnh. Ước tính trước đây cho rằng lane này có thể lên khoảng 1,45–1,60 sau khi đủ nguồn — vé này kiểm chứng ước tính đó bằng số đo thật.

## Việc phải làm

1. Đo lại đủ 50 câu của lane hỏi đáp cục bộ bằng đúng bộ đề, đúng thang chấm và cùng trình đo như lượt đo chuẩn gần nhất, tại máy công ty, chỉ dùng bộ xử lý trung tâm. Ghi rõ mã commit đang chạy và dấu vân tay của chỉ mục tại thời điểm đo.
2. Đo lại lane dịch vụ trí tuệ nhân tạo của công ty trên cùng bộ đề để đối chiếu (mốc gần nhất 2,937) — lane này chỉ để tham chiếu, không thuộc phạm vi sửa.
3. So sánh từng câu với lượt đo chuẩn gần nhất: tổng điểm và điểm trung bình mới, số câu tăng, giữ nguyên, giảm; tách riêng nhóm câu thuộc phần tài liệu vừa được nạp và gắn nguồn để thấy hiệu quả thật của đợt nạp. Kết luận rõ ước tính 1,45–1,60 đúng hay sai, và khoảng cách tới ngưỡng 1,5 còn bao nhiêu.
4. Nghiệm thu dùng thật kèm theo: mở ứng dụng, hỏi 3 câu qua giao diện (ít nhất 1 câu thuộc phần tài liệu vừa nạp), nộp đáp án nguyên văn và ảnh chứa đáp án trong khung hình.

## Rào cứng

- Chỉ đo và ghi: không sửa mã, không sửa thang chấm, không ghi vào chỉ mục trong vé này. Không chạy việc nặng đồng thời với phiên ứng dụng của người dùng trên cùng máy. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để ngắt giữa chừng vẫn chạy tiếp được.
