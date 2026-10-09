# VÉ: SYNTH-CONTEXT-ENTITY-HOME (nới ngữ cảnh có điều kiện theo thực thể cho các mảnh hạng 9–12)

- Mã vé: `SYNTH-CONTEXT-ENTITY-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-context-entity-home.md`
- Bối cảnh: mặc định hiện tại của hệ thống là đưa 8 mảnh ngữ cảnh vào khâu tổng hợp (`DEFAULT_SYNTH_CONTEXT_TOPK = 8` trong `src/aios_habit/antigravity_bridge.py`, điểm cắt tại khoảng dòng 1415–1417). Thí nghiệm trước đây tại máy công ty (báo cáo `docs/phieu-viec/ket-qua/synth-context-topk-pc0575.md`) cho thấy nới vô điều kiện lên 12 mảnh gần như hòa vốn: 11 câu tăng tổng cộng +11,84 điểm (điển hình câu `Q0701` từ 0 lên 3 điểm tuyệt đối nhờ mảnh hạng 11 chứa đúng thực thể cần thiết), nhưng 15 câu giảm tổng cộng −11,50 điểm, trong đó một nhóm giảm vì nhiễu ngữ cảnh — thêm mảnh hạng thấp khiến mô hình thận trọng quá mức và trả lời "không đủ dữ kiện" ở các câu mang tính tổng quát. Kết luận rút ra: chỉ nên nới khi mảnh hạng 9–12 thực sự chứa thực thể cụ thể mà câu hỏi cần.

## Việc phải làm

1. Áp cơ chế nới có điều kiện trong đường tổng hợp: giữ nguyên 8 mảnh đầu; xét tiếp các mảnh hạng 9–12 và chỉ đưa thêm mảnh nào chứa ít nhất một thực thể cụ thể khớp với câu hỏi — ví dụ mã lỗi hoặc mã máy dạng chữ-số, tên riêng hoặc mã tài liệu xuất hiện trong câu hỏi, hoặc con số kèm đơn vị mà câu hỏi nhắc tới. Câu hỏi mang tính tổng quát không chứa thực thể cụ thể thì giữ nguyên 8 mảnh như hiện tại. Cơ chế phải có cờ tắt bằng biến môi trường để quay về hành vi cũ mà không sửa mã, và phải ghi vết trong dữ kiện đo mỗi câu có nới hay không, nới thêm mảnh nào.
2. Viết kiểm thử đơn vị cho cơ chế chọn lọc: mảnh hạng 9–12 có thực thể khớp thì được đưa vào; không khớp thì bị loại; cờ tắt hoạt động; thứ tự và đánh số trích dẫn của các mảnh gốc không đổi.
3. Đo lại đủ 50 câu bằng đúng bộ đề và thang chấm hiện hành, tại máy nhà, chỉ dùng bộ xử lý trung tâm, chuỗi mô hình đã chốt (mô hình miễn phí làm chính theo cấu hình go-live hiện tại của máy). So sánh từng câu với mốc gần nhất (tổng 65,33 trên 150, điểm trung bình 1,31 — dữ kiện ở `docs/phieu-viec/ket-qua/rows-synth-fallback-citation-fix.jsonl`): báo rõ số câu tăng, số câu giữ nguyên, số câu giảm và tổng điểm mới; tách riêng nhóm câu được nới ngữ cảnh để thấy hiệu quả thật của cơ chế.
4. Nghiệm thu dùng thật: mở ứng dụng ở chế độ chỉ dùng bộ xử lý trung tâm, hỏi 3 câu qua giao diện (ít nhất 1 câu thuộc nhóm từng được cứu nhờ mảnh hạng cao trong thí nghiệm trước), nộp đáp án nguyên văn và ảnh chứa đáp án trong khung hình. Ghi rõ mã commit đang chạy.

## Lưu ý thực tế về tài khoản mô hình

Tài khoản dùng chung hiện đang ở gần trần tuần và trần tháng. Các lượt gọi mô hình lẻ tẻ có thể bị từ chối tạm thời: khi gặp, ghi mốc vào trang trạng thái, chờ một nhịp rồi chạy tiếp phần còn lại bằng khả năng chạy tiếp của trình đo — không bỏ dở vé, không đổi sang mô hình trả phí ngoài chuỗi đã chốt.

## Rào cứng

- Không ghi vào chỉ mục production. Không đổi bộ đề và thang chấm. Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để ngắt giữa chừng vẫn chạy tiếp được.
