# VÉ: RETRIEVAL-PERF-DIAG-PC0575 (chẩn đoán 225–255 giây tìm kiếm đi đâu — chỉ-đọc)

- Mã vé: `RETRIEVAL-PERF-DIAG-PC0575`
- Role gợi ý: PLAN/DEFAULT (đo phân rã + đề xuất, KHÔNG sửa code ở vé này)
- Máy: công ty KDTVN-PC0575
- Báo cáo: `docs/phieu-viec/ket-qua/retrieval-perf-diag-pc0575.md`
- Điều kiện chạy: **sau khi opencode ghi mốc "mẫu xong" của SRC-PROBE và TRƯỚC khi OMP khởi lane đo lại** (điều phối đã xếp lượt máy: probe → vé này → đo lại). Trần thời gian cho vé: ~45 phút đo thực tế.

## Bối cảnh

Vé `RETRIEVAL-ENTITY-PC0575` (ĐẠT) cho thấy trên máy công ty: tìm kiếm đúng tài liệu rồi nhưng **mỗi câu mất 225–255 giây ở khâu tìm kiếm** (tổng chờ 272–293 giây/câu). Trước khi phát vé sửa hiệu năng, cần biết 225 giây đó nằm ở chặng nào — cấm đoán mò.

## Việc phải làm (đo phân rã trên máy thật, 3 câu đại diện của nhóm A)

1. Chạy 3 câu qua pipeline thật (tiến trình nền tách phiên), ghi thời gian TỪNG chặng: nạp model/khởi động (mỗi câu hay dùng lại), tìm dày đặc (dense trên 149.800 vector), tìm từ khoá (sparse), hợp nhất hạng (fusion), chấm điểm ứng viên, đóng gói bằng chứng. Dùng log/hàm đo sẵn có của pipeline; thiếu điểm đo thì ghi rõ chặng nào chưa đo được thay vì ước lượng.
2. Kiểm các giả thuyết cụ thể bằng số: (a) model bị nạp lại mỗi câu; (b) quét tuyến tính toàn bộ vector bằng CPU; (c) vòng lặp chấm điểm ứng viên bằng Python thuần trên quá nhiều ứng viên; (d) I/O đọc SQLite từng mảnh; (e) tranh chấp tài nguyên (máy lúc đo có tiến trình nặng nào khác không — ghi rõ).
3. Xếp hạng các chặng theo thời gian chiếm giữ + đề xuất hướng sửa cho từng chặng lớn nhất: cách sửa dự kiến, mức cải thiện kỳ vọng (có căn cứ số), rủi ro đổi chất lượng tìm kiếm. Chỉ đề xuất — không sửa code ở vé này.

## Rào cứng

- Chỉ-đọc với code và index: không sửa `src/`, không ghi index, không đổi cấu hình. Chạy đo nền tách phiên, không chặn thợ khác ngoài cửa sổ đã xếp lượt.
- Mọi con số phải là số đo thật trên máy công ty; không ngoại suy từ máy khác.
