# VÉ: MISSING5-RETRIEVAL-DIAG-HOME (chẩn đoán vì sao 5 tệp đã nạp mà nhóm câu đích vẫn bị chặn)

- Mã vé: `MISSING5-RETRIEVAL-DIAG-HOME`
- Role gợi ý: DEFAULT (agy — thợ farm/phân tích, máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/missing5-retrieval-diag-home.md`
- Loại vé: CHẨN ĐOÁN CHỈ ĐỌC. Không ghi chỉ mục, không sửa mã, không đổi ngưỡng, không đổi bộ đề/thang chấm trong vé này.

## Bối cảnh đã được điều phối kiểm chứng độc lập

Vé `DATA-INGEST-MISSING5-HOME` bị verdict KHÔNG ĐẠT. Phần vật lý được công nhận: gói nguồn và từng tệp khớp mã băm; có sao lưu toàn vẹn trước nạp; có chạy thử không ghi; chỉ mục production hiện là 894 tài liệu / 181.033 mảnh, kích thước 3.308.937.216 byte, SHA-256 `c5a9d524a88031c9d49c9710f998f1efed8a08bbd1ba0578df64507e88bb5d96`, toàn vẹn `ok`; tổng đo lại 50 câu là 71,0/150 (điều phối tự cộng và tự chấm lại khớp tuyệt đối).

Nhưng mục tiêu chất lượng không đạt: trong tệp `rows-target8-check.jsonl` do chính vé nạp nộp, 7 câu đích chỉ đạt tổng 1,0/21 — sáu câu 0,0 và `Q0824` đạt 1,0 do artefact của hàm chấm trên đáp án từ chối chung, không có trích dẫn hợp lệ; `Q0668` giữ 1,5. So với lượt Q0668 trước nạp, tổng của đúng 7 câu đích không đổi (1,0 -> 1,0). Cả 7 câu đích ở chế độ `local_extractive_provider_not_called`, `lexical_passed=false`, `semantic_passed=false`. Báo cáo của vé nạp ghi các câu này đều đạt 1,0 và có trích dẫn hợp lệ — kết luận đó không được công nhận.

Các dấu hiệu phải truy tận gốc:
- Chạy thử dự kiến 31.233 mảnh; danh sách mảnh theo tệp trong báo cáo cộng lại là 27.529 (đúng phần có thể truy hồi mà báo cáo nêu), còn 3.704 mảnh không được liệt kê riêng.
- Chỉ có +622 vector được ghi cho 3 tệp (PPTX 8, UnitTest 97, Error 517). Chưa rõ 26.907 mảnh có thể truy hồi còn lại của hai tệp lớn (Spec và Error_BowOverAdjust) có vector dày/ thưa hay không, và quy trình nạp hiện hành có yêu cầu đủ vector cho mọi mảnh có thể truy hồi hay không.
- Nhiều câu đích là câu tổng hợp trên toàn bộ tệp CSV (đếm bản ghi, phân bố theo màu, ngày nhiều nhất, cặp giới hạn phổ biến nhất) — truy hồi một số mảnh rời rạc có thể không bao giờ đủ để tính đúng, dù tệp đã có trong chỉ mục.
- Đường đo và đường giao diện cho kết quả khác nhau: đường đo trả mẫu từ chối ngắn; giao diện trả đáp án dài qua `external_api` nhưng vẫn kết luận chưa đủ bằng chứng và trích các nguồn không phải tệp đích.

## Việc phải làm

1. Kiểm kê chỉ đọc trên production (mở ở chế độ chỉ đọc, ghi rõ cách mở): với từng tài liệu trong 5 tệp mới, thống kê số mảnh tổng, số mảnh có thể truy hồi, số vector dày, số vector thưa, số mục FTS khớp các định danh/giá trị đích. Đối chiếu với tài liệu cũ tương tự để biết quy trình nạp hiện hành thực sự yêu cầu gì. Không suy luận từ tên bảng — nộp truy vấn và kết quả thô.
2. Truy vết từng câu trong 8 câu (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843`, `Q0668`) trên đường đo: thuật ngữ truy vấn, danh sách mảnh trả về (mã tài liệu, tên tệp, hạng, điểm), tệp đích có xuất hiện trong top-k hay không, độ phủ bằng chứng được tính từ đâu, vì sao cổng từ vựng/ngữ nghĩa không qua, vì sao mô hình không được gọi. Phân biệt rõ bốn khả năng: (a) mảnh đích không có trong chỉ mục; (b) có mảnh nhưng không có vector/FTS nên không truy hồi được; (c) truy hồi được nhưng cổng bằng chứng loại; (d) bản chất câu hỏi cần tổng hợp toàn tệp, không thể trả lời từ top-k mảnh.
3. Truy vết riêng `Q0620` và `Q0824`: giá trị kỳ vọng nằm ở đâu trong tệp nguồn gốc (slide/dòng cụ thể), tệp đó được chia mảnh ra sao, mảnh chứa giá trị có tồn tại trong production không, và vì sao cả đường đo lẫn giao diện không dùng nó. Với `Q0824`, tách bạch điểm artefact của hàm chấm khỏi kết quả truy hồi thật.
4. Truy vết đường giao diện cho `Q0668` (Mục 0.2 còn treo): so sánh khối tri thức, làn định tuyến, hàm truy hồi và chỉ mục đang hoạt động giữa đường đo và giao diện. Bằng chứng đã nộp ở commit `8e8bd3b` tự mâu thuẫn (tệp dữ kiện ghi phiên `CONV-Q0668-6AC9BA1F` và đáp án kết luận chưa đủ bằng chứng, trong khi báo cáo vé nạp nhắc một mã phiên khác không có trong bằng chứng đã commit) — chỉ dùng bằng chứng truy được trong kho hoặc nhật ký tại máy có thể nộp lên kho; không kết luận từ mã phiên không có bằng chứng.
5. Kết luận xếp hạng nguyên nhân theo mức đóng góp, kèm phương án sửa tương ứng cho từng nguyên nhân: việc nào chỉ cần nạp bổ sung vector, việc nào cần thay đổi cách chia mảnh, việc nào cần đường tổng hợp có cấu trúc cho câu hỏi thống kê trên CSV, việc nào là lỗi cổng/định tuyến. Mỗi phương án ghi phạm vi, rủi ro, cách kiểm chứng sau sửa. Không tự triển khai phương án trong vé này.

## Ràng buộc

- Chỉ đọc production; giữ nguyên bản sao lưu `library.sqlite.bak-20261010-pre-missing5` và thư mục staging cho tới khi có verdict của vé này.
- Không hạ ngưỡng cổng kiểm chứng 0,60. Không sửa hàm chấm để che artefact `Q0824`.
- Mốc tiến độ tối thiểu 15 phút/lần kèm điểm kiểm. Mọi con số trong báo cáo phải đo từ dữ kiện đã commit hoặc truy vấn có thể chạy lại; ghi rõ mã commit đang chạy cho mọi lượt truy vết giao diện.
- Báo cáo nộp tại đường dẫn ở đầu vé, kèm các tệp truy vấn/kết quả thô cần thiết để điều phối kiểm chứng lại.
