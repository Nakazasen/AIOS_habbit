# VÉ NHỎ: AUDIT-EMBED-GEMMA-HOME (kiểm lại độc lập báo cáo đánh giá EmbeddingGemma)

- Mã vé: `AUDIT-EMBED-GEMMA-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà, chỉ đọc)
- Báo cáo: `docs/phieu-viec/ket-qua/audit-embed-gemma-home.md`
- Căn cứ: vé `EMBED-GEMMA-EVAL-HOME` (agy, verdict ĐẠT ~10:05 08/10) kết luận KHÔNG thay BGE-M3 bằng EmbeddingGemma. Vé này kiểm lại độc lập các con số và lập luận trong báo cáo gốc `docs/phieu-viec/ket-qua/embed-gemma-eval-home.md` (và các file kết quả đính kèm của vé đó nếu có trong kho/thư mục runner tại máy nhà).

## Việc phải làm — đối chiếu từng điểm

1. Các số đo chính trong báo cáo gốc (tập câu dùng để đo, tỉ lệ tìm thấy đích của từng cấu hình, các ca trượt được nêu tên) có tái lập được từ file kết quả đính kèm không — đếm lại và nêu khớp/lệch.
2. Ba lý do loại được nêu trong kết luận: (a) chỉ dense nên trượt câu mã cứng — có bằng chứng ca cụ thể trong kết quả không; (b) đòi phiên bản thư viện mới làm gãy môi trường ghim — kiểm chứng từ khai báo phụ thuộc/log của lượt đo; (c) ước tính thời gian nhúng lại toàn kho bằng CPU ~122 giờ — kiểm lại phép tính từ tốc độ đo thật.
3. Kết luận một câu: báo cáo gốc đứng vững hay có điểm nào cần đính chính.

## Rào cứng

- Chỉ đọc; không chạy lại lượt đo, không cài/gỡ thư viện, không đụng chỉ mục hay cấu hình. Không merge `main`.
- Báo cáo ngắn dạng bảng đối chiếu.
