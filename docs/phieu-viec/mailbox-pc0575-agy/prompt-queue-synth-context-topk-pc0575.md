# VÉ: SYNTH-CONTEXT-TOPK-PC0575 (nâng ngưỡng ngữ cảnh đưa vào tổng hợp từ 8 lên 12 — đo lại lane RAG)

- Mã vé: `SYNTH-CONTEXT-TOPK-PC0575`
- Role gợi ý: DEFAULT
- Máy: công ty KDTVN-PC0575 (agy — thợ chính, CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-context-topk-pc0575.md`
- Căn cứ: kết quả đo `RAG-REMEASURE-PC0575` (điều phối đã verdict): lane RAG GPA 0,957 — trong 5 câu nhóm A (truy hồi trượt), câu Q0701 mất trắng 0 điểm chỉ vì tài liệu đích đứng hạng 11 trong danh sách ngữ cảnh cuối trong khi khâu tổng hợp chỉ lấy top 8; các câu đích hạng 9–12 khác cùng chịu rủi ro bị cắt. Vé này thử nghiệm nâng ngưỡng ngữ cảnh để cứu đúng nhóm đó, đo lại bằng đúng bộ đề + rubric của REMEASURE.

## Việc phải làm

1. Xác định trong code đường đo RAG (pipeline + bridge tổng hợp) tham số số mảnh ngữ cảnh đưa vào prompt tổng hợp hiện là 8 ở đâu (file:hàm), biến nó thành cấu hình (biến môi trường hoặc tham số có mặc định tường minh) — không hardcode rải rác.
2. Đặt ngưỡng thử nghiệm = **12** và đo lại **lane RAG đủ 50 câu** bằng đúng runner + rubric của vé REMEASURE (đếm theo `che_do` như đã cảnh báo ở các vé trước), trên cùng chỉ mục PC0575 (chỉ đọc — kiểm MD5 trước/sau phải khớp tuyệt đối).
3. So sánh trực tiếp với kết quả REMEASURE: GPA tổng, số câu ≥2,0, và RIÊNG nhóm A (Q0704, Q0701, Q0688, Q0707, Q0696) từng câu trước/sau; ghi cả thời gian tổng hợp trung bình trước/sau (ngữ cảnh dài hơn có thể chậm hơn — phải đo, không đoán).
4. Nếu GPA cải thiện mà không có câu nào đang đạt chuẩn bị tụt xuống dưới chuẩn vì thay đổi này: đề xuất giữ 12 làm mặc định trong báo cáo (điều phối quyết bằng ghi_chu). Nếu có câu tụt: liệt kê và đề xuất hướng (giữ 8 / chọn 10 / cơ chế khác).

## Rào cứng

- Chỉ thay đổi đúng tham số ngưỡng ngữ cảnh + điểm cấu hình của nó; không sửa logic truy hồi, không sửa rubric/bộ đề.
- Chỉ mục chỉ đọc tuyệt đối; không ingest; không merge `main`. Tương thích Python 3.11.
- Kỷ luật số liệu: thời gian phải ghi CẢ trung bình số học lẫn số giữa (median), ghi rõ đơn vị và số câu — không trình bày median như trung bình.
- Vé dài: mốc tối thiểu 15 phút/lần + checkpoint/resume như vé REMEASURE.
