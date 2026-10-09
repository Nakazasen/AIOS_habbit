# VÉ: AUDIT-REMEASURE-PC0575 (sửa 3 điểm trình bày báo cáo đo lại + kiểm toán độc lập các báo cáo truy hồi của thợ chính)

- Mã vé: `AUDIT-REMEASURE-PC0575`
- Role gợi ý: DEFAULT (OMP — thợ phụ, máy công ty KDTVN-PC0575)
- Báo cáo: `docs/phieu-viec/ket-qua/audit-remeasure-pc0575.md`
- Bối cảnh: vé này gộp các việc phụ đã xếp cho thợ phụ máy công ty từ ngày 08/10. Toàn bộ là việc nhẹ: đọc tệp kết quả và sửa tài liệu — phù hợp làm trong lúc thợ chính đang nghiệm thu dùng thật trên cùng máy và người dùng đang sử dụng máy.

## Việc phải làm

1. **Sửa 3 điểm trình bày trong báo cáo đo lại** (`docs/phieu-viec/ket-qua/rag-remeasure-pc0575.md`) theo đúng verdict của điều phối đã ghi: (a) phần tốc độ truy hồi ghi rõ cả hai con số — trung bình 26,1 giây và trung vị khoảng 11 giây — không ghi trung vị dưới nhãn trung bình; (b) phần phân loại câu: nhóm thiếu nguồn gồm 15 câu và bỏ mã Q0787 khỏi nhóm này, nhóm Khác gồm 6 câu và thêm mã Q2157 vào nhóm này; (c) dòng trạng thái ở đầu báo cáo bỏ cách ghi "đạt mục tiêu" (lane RAG 0,957 chưa đạt ngưỡng 1,5). Không sửa số đo gốc, chỉ sửa cách trình bày đúng ba điểm này.
2. **Kiểm toán độc lập báo cáo đo lại:** tính lại điểm trung bình của cả hai lane từ tệp kết quả gốc trên máy (nếu còn) hoặc từ bảng chi tiết trong báo cáo; đối chiếu tổng điểm và số câu đạt chuẩn với con số báo cáo công bố; ghi kết quả đối chiếu vào báo cáo của vé này.
3. **Kiểm toán độc lập hai báo cáo truy hồi** của thợ chính: báo cáo nạp dày bằng numpy và báo cáo từ khoá FTS — kiểm lại các con số chính (tính tương đương kết quả, hệ số tăng tốc) từ tệp kết quả gốc của từng vé, xác nhận chỉ mục không đổi trong cả hai vé. Mỗi báo cáo một phần kết luận riêng trong báo cáo của vé này: khớp hay lệch, lệch ở đâu.

## Rào cứng

- Chỉ đọc dữ liệu và sửa đúng tài liệu được chỉ định; không sửa mã chạy thật, không chạy ứng dụng, không chạy việc nặng trên máy trong thời gian thợ chính nghiệm thu và người dùng đang dùng máy. Không ghi chỉ mục. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
