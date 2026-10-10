# VÉ: MISSING5-EMBED-COMPLETE-HOME (nhúng bổ sung 26.907 mảnh còn thiếu vector của 2 tệp lớn)

- Mã vé: `MISSING5-EMBED-COMPLETE-HOME`
- Role gợi ý: DEFAULT (agy — máy nhà `h410asrock`, việc bulk dài)
- Báo cáo: `docs/phieu-viec/ket-qua/missing5-embed-complete-home.md`
- Điều kiện bốc: sau khi `MISSING5-PARSER-FIX-HOME` khép (để mọi mảnh mới của 2 tệp nạp lại cũng được tính trong cùng một lần kiểm kê cuối).

## Căn cứ (vé chẩn đoán MISSING5-RETRIEVAL-DIAG-HOME, điều phối đã kiểm chứng từ dữ kiện thô)

Production hiện có 26.907 mảnh có thể truy hồi của `2026_08_Error_BowOverAdjust.csv` (22.054) và `2026_08_Spec.csv` (4.853) hoàn toàn không có vector dày/thưa (0/26.907), trong khi quy chuẩn của 889 tài liệu cũ là 100% mảnh có thể truy hồi có đủ vector. Hai tệp này vì thế bị loại khỏi kênh tìm kiếm ngữ nghĩa.

## Việc phải làm

1. Kiểm kê lại trước khi chạy (số mảnh thiếu vector theo từng tài liệu) và nộp kèm báo cáo; nếu con số khác 26.907 do vé nạp lại trước đó, dùng con số kiểm kê mới và giải thích.
2. Nhúng bổ sung toàn bộ số mảnh còn thiếu bằng đúng mô hình và cấu hình của production (BGE-M3, cùng fingerprint như chỉ mục hiện hành). Được dùng GPU của máy nhà cho khâu nhúng (đúng luật: GPU chỉ dùng cho embedding/index). Bắt buộc có điểm kiểm theo đợt để chạy tiếp được khi bị ngắt; không nhúng lại các mảnh đã có vector.
3. Sau khi xong: kiểm kê lại đạt 100% mảnh có thể truy hồi có đủ vector dày + thưa; toàn vẹn `ok`; ghi kích thước và SHA-256 của production trước/sau.
4. Đo lại 8 câu đích bằng đường đo hiện hành, nộp tệp rows đầy đủ để điều phối đối chiếu (không tự kết luận đạt/không đạt).

## Ràng buộc

- Không đổi ngưỡng, không đổi bộ đề/thang chấm, không sửa mã ứng dụng trong vé này.
- Đây là việc nặng: không chạy đồng thời với phiên ứng dụng của user hay các lượt đo thời gian trên cùng máy; ghi mốc tiến độ tối thiểu 15 phút/lần kèm số mảnh đã nhúng.
