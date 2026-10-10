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

## Bổ sung phạm vi của điều phối (2026-10-11, từ verdict MISSING5-PARSER-FIX-HOME)

Hai việc chuyển tiếp bắt buộc, ngoài 4 câu thống kê gốc của vé:

1. **Ca Q0824 (so sánh phán định của một serial giữa hai ngày)**: bộ chia mảnh đã chữa xong (hai dòng đích vào hạng 2 và 3 của gói bằng chứng, đủ cột phán định) nhưng đáp án bị cổng độ phủ từ vựng đa ngữ chặn (câu hỏi tiếng Nhật, bằng chứng tiếng Anh, lý do `final_evidence_query_coverage_below_threshold`). Làn có cấu trúc phải trả lời được ca này từ chính bảng dữ liệu (tra dòng theo serial + so sánh hai ngày) mà không phụ thuộc độ phủ từ vựng của câu hỏi, và đáp án phải khớp sự thật của hai dòng (cả hai ngày đều OK ở mọi cột phán định → Pattern không đổi).
2. **Bằng chứng giao diện cho Q0620 và Q0824**: trong nghiệm thu của vé này, chạy cả hai câu trên giao diện thật và nộp ảnh chứa TRỌN thân đáp án đã hoàn tất (không chấp nhận ảnh chụp lúc còn đang xử lý) — đây là phần bằng chứng giao diện còn thiếu của vé PARSER-FIX.
