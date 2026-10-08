# VÉ NHỎ: AUDIT-CONTRACT-FREE-HOME (kiểm lại độc lập báo cáo hợp đồng tổng hợp model free)

- Mã vé: `AUDIT-CONTRACT-FREE-HOME`
- Role gợi ý: SMOL/TINY (OMP — thợ phụ, máy nhà, chỉ đọc)
- Báo cáo: `docs/phieu-viec/ket-qua/audit-contract-free-home.md`
- Căn cứ: vé `SYNTH-CONTRACT-FREE-HOME` (agy, verdict ĐẠT-kết quả-âm ~10:37 08/10) kết luận: ép các model free tuân "hợp đồng tổng hợp" khắt khe cho validated 0/50 → giữ cờ hợp đồng TẮT. Vé này kiểm lại độc lập các con số và lập luận trong báo cáo gốc `docs/phieu-viec/ket-qua/synth-contract-free-home.md` và file kết quả thô của lượt đo đó tại máy nhà (nếu còn).

## Việc phải làm — đối chiếu từng điểm

1. Số câu đo, phân rã chế độ (validated khai 0/50; các chế độ còn lại), tổng điểm/GPA của lượt đo — đếm lại từ file thô, nêu khớp/lệch. Nếu file thô không còn tồn tại, khai rõ "không tái lập được" thay vì suy đoán.
2. Các lý do trượt kiểm định được nêu trong báo cáo gốc (phân rã theo mã lý do) có khớp với dữ kiện thô không.
3. Việc "giữ cờ TẮT" sau lượt đo: kiểm cấu hình hiện tại của tuyến tổng hợp tại máy nhà CHỈ ở mức tên biến/cờ (tuyệt đối không chép giá trị khóa hay bí mật) — cờ hợp đồng đang tắt thật hay đã bị bật lại.
4. Kết luận một câu: báo cáo gốc đứng vững hay cần đính chính điểm nào.

## Rào cứng

- Chỉ đọc; không chạy lại lượt đo, không đổi cấu hình, không đụng chỉ mục. Không merge `main`.
- Báo cáo ngắn dạng bảng đối chiếu.
