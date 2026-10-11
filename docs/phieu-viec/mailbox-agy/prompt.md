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


## Bổ sung phạm vi của điều phối (2026-10-11, từ verdict Q0668-BLOCK-FIX-HOME — ĐẠT MỘT PHẦN)

Vé `Q0668-BLOCK-FIX-HOME` đã khép phần ống nước khối (tệp đích + 5 tệp missing5 đã vào bộ sưu tập khối `lsu`, truy hồi trên khối `lsu` xếp tệp đích hạng 1 có trích dẫn) nhưng đáp án Q0668 qua giao diện vẫn **chưa chứa bộ số nominal/giới hạn** (rows tự nộp: `chinh_xac` 0.0, tổng 1.0/3.0; đáp án giao diện là mẫu "No grounded evidence" kèm trích dẫn công thức `=G3-G2`/`=G2-G4` chưa tính giá trị, bị gắn `incomplete_query_term_coverage`). Phần tồn này thuộc đúng bản chất làn cấu trúc — trả lời từ **giá trị ô đã tính trong bảng** thay vì từ mảnh văn bản chứa công thức — nên chuyển vào vé này làm ca bắt buộc thêm:

- **Ca Q0668 (bảng tính XLSX)**: hỏi lại `g1 và g2 có nominal và giới hạn nào?` qua khối `lsu` trên giao diện thật; đáp án hoàn tất phải nêu đúng bộ số: nominal **13.81**, dung sai **+0.12 / -0.05**, giới hạn **13.93 / 13.76**, trích đúng tệp `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx`. Ảnh chứa trọn thân đáp án.
- Ghi chú bằng chứng đã có: bằng chứng giao diện của Q0620 (câu PPTX qua khối `lsu`, đủ 49,49%/25,42%) đã được vé BLOCK-FIX nộp và điều phối kiểm chứng — phần nợ bằng chứng giao diện của vé này chỉ còn **Q0824** (theo bổ sung trước) **+ ca Q0668 ở trên**.
- Nhắc luật báo cáo (lần thứ ba điều phối phải nhắc): số liệu trong báo cáo phải khớp tệp rows tự nộp; "bằng chứng truy hồi được" không đồng nghĩa "đáp án đúng" — báo cáo của BLOCK-FIX đã bị ghi điểm trừ vì lỗi này.
