# Vé LSU-QUALITY-PC0575 — Đo chất lượng trả lời LSU trên câu hỏi thật

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `DIGEST-CTY-RESUME`.
**Role gợi ý:** DEFAULT (chạy đo + phân tích).

## Bối cảnh

- Vé `WIRE-QA-CAGENT-PC0575` đã nối 3.392 cặp hỏi-đáp (1.790 LSU) vào lane C-Agent.
- Index chính đã được khôi phục (vé `RESTORE-INDEX-SPLIT-PC0575`) → lane RAG dùng được.
- Vé này đo chất lượng thật theo đúng nguyên tắc "mọi tính năng phải có metric".

## Việc cần làm (đúng thứ tự)

1. Lấy bộ câu hỏi từ `docs/phieu-viec/ket-qua/lsu-quality-set.md`
   (vé `PREP-LSU-QUALITY-PC0575` của agy chuẩn bị — nếu chưa có thì DỪNG và báo,
   không tự bịa bộ câu hỏi).
2. Dùng khung đo ở `src/aios_habit/quality_harness.py`
   (vé `BUILD-QUALITY-HARNESS-PC0575` của opencode — nếu chưa có thì đo tay 30 câu mẫu).
3. Chạy mỗi câu qua cả 2 lane (C-Agent và RAG), chấm theo rubric.
4. Báo cáo `docs/phieu-viec/ket-qua/lsu-quality-pc0575.md`:
   tỉ lệ đạt từng lane, 10 câu tệ nhất + phân loại lỗi (sai trọng tâm / thiếu trích dẫn / bịa),
   đề xuất cải thiện cụ thể cho vòng sau.

## Rào cứng

- Không nhập điểm đo vào kho tri thức. Không merge `main`. Python 3.11.
- Câu hỏi và đáp án mẫu là bản thảo — giữ nhãn "chưa qua chuyên gia duyệt" trong báo cáo.
