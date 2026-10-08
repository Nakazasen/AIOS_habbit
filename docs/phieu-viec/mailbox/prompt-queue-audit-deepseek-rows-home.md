# VÉ NHỎ: AUDIT-DEEPSEEK-ROWS-HOME (đếm lại độc lập file kết quả thô của lượt đo DeepSeek)

- Mã vé: `AUDIT-DEEPSEEK-ROWS-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà, chỉ đọc)
- Báo cáo: `docs/phieu-viec/ket-qua/audit-deepseek-rows-home.md`
- Căn cứ: báo cáo vé `SYNTH-DEEPSEEK-AB-HOME` (agy) khai các số tổng hợp từ file kết quả thô `rows-synth-deepseek.jsonl` nằm ngoài kho (thư mục runner trên máy nhà) nên điều phối chưa tự đếm lại được. Vé này đếm lại độc lập từ chính file đó.

## Việc phải làm — đếm và đối chiếu từng số sau với báo cáo gốc

1. Tổng số dòng/câu; tổng điểm và GPA (khai: 63,18/150 — GPA 1,26).
2. Đếm theo trường `che_do`: validated (khai 3 — Q0851, Q0620, Q2157), fallback (43), not-called (4 — Q0824, Q0704, Q0718, Q0668).
3. Số câu không trích dẫn (khai 10); số câu đạt 3,0 điểm (khai 6); số câu ≥ 2,0 (khai 7).
4. Thời gian toàn câu và thời gian tổng hợp: trung bình số học + số giữa (khai 25,19/22,42 giây và 19,37/16,96 giây).
5. Tổng token vào/ra và chi phí nếu file có ghi (khai 304.964 token; $0,092991).
6. Nêu rõ mọi lệch (nếu có) giữa số đếm lại và báo cáo gốc; nếu khớp toàn bộ thì kết luận một câu.

## Rào cứng

- Chỉ đọc; không sửa file kết quả, không chạy lại lượt đo, không đụng cấu hình/key. Không ghi chỉ mục.
- Báo cáo ngắn, dạng bảng đối chiếu khai vs đếm lại.
