# VÉ: CSV-STRUCTURED-LANE-HOME (xây làn truy vấn có cấu trúc cho câu hỏi thống kê toàn tệp CSV)

- Mã vé: `CSV-STRUCTURED-LANE-HOME`
- Role gợi ý: PLAN/DEFAULT (agy — máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/csv-structured-lane-home.md`
- Điều kiện bốc: sau khi `Q0668-BLOCK-FIX-HOME` khép. Đây là vé xây tính năng, không phải vé vá dữ liệu.

## Căn cứ (vé chẩn đoán MISSING5-RETRIEVAL-DIAG-HOME, điều phối đã kiểm chứng)

4 trên 7 câu đích (`Q0849`, `Q0850`, `Q1034`, `Q0843`) là câu hỏi thống kê toàn tệp: đếm bản ghi, phân bố theo màu, ngày nhiều lỗi nhất, cặp giới hạn phổ biến nhất. Truy hồi top-k mảnh văn bản rời rạc về mặt toán học không thể tính đúng các phép tổng hợp này trên 3.153–25.213 bản ghi, dù dữ liệu đã có đủ trong chỉ mục. Trong kho đã có hạ tầng truy vấn có cấu trúc (`src/aios_habit/rag_v2/structured_query.py`) để tận dụng.

## Việc phải làm

1. Khảo sát hạ tầng truy vấn có cấu trúc hiện có và thiết kế làn định tuyến: khi phân loại ý định nhận ra câu hỏi thống kê trên tệp CSV đã index (đếm/phân bố/giá trị cực trị), định tuyến sang thực thi truy vấn có cấu trúc trên dữ liệu nguồn/bảng đã nạp, trả đáp án kèm trích dẫn tệp và phạm vi dữ liệu. Chỉ cho phép truy vấn đọc (SELECT) trên bảng tạm/nội bộ, chống tiêm SQL.
2. Triển khai trong phạm vi đường hỏi đáp hiện hành (cả đường đo và giao diện dùng chung một làn), không đổi ngưỡng cổng bằng chứng cho các câu không thuộc nhóm thống kê.
3. Kiểm chứng: đo lại 4 câu thống kê — số liệu phải khớp 100% với đáp án chuẩn; đo lại toàn bộ 50 câu để xác nhận không thụt lùi ở nhóm câu khác; nghiệm thu giao diện ít nhất 2 câu thống kê trong phiên mới, ảnh chứa trọn thân đáp án.

## Ràng buộc

- Tuân thủ chuẩn sản phẩm: tính năng phải có điểm hứng phản hồi tại chỗ, metric đo được và vòng xem lại như mọi tính năng mới khác.
- Không đổi bộ đề/thang chấm. Mốc tiến độ tối thiểu 15 phút/lần kèm điểm kiểm; commit checkpoint theo mốc.
