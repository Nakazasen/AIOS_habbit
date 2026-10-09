# VÉ: SYNTH-Q0668-FILTER-FIX-HOME (mở đường cho tài liệu bị lọc khối oan — ca Q0668)

- Mã vé: `SYNTH-Q0668-FILTER-FIX-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-q0668-filter-fix-home.md`
- Bối cảnh: vé chẩn đoán `SYNTH-RETRIEVAL-GAP-DIAG-HOME` xác nhận câu `Q0668` (hỏi nominal và giới hạn của g1/g2) có dữ kiện đầy đủ trong chỉ mục — tệp `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` có 82 mảnh, mảnh chứa đủ "13.81, dung sai +0.12/-0.05, giới hạn 13.93/13.76" — nhưng câu hỏi không với tới được vì hai lý do chồng nhau: (1) tài liệu bị gán nhãn khối `dieu_tra_loi` nên khâu lọc theo khối tri thức loại nó khỏi đường trả lời của câu hỏi; (2) tìm kiếm toàn văn trên toàn kho bị từ nhiễu đẩy mảnh đích xuống hạng khoảng #602/#658. Giá trị kỳ vọng của vé: lấy lại trọn 3,0 điểm của câu này và mở đường cho các câu cùng dạng (hỏi theo định danh cơ khí chính xác).

## Việc phải làm

1. Chọn và áp cơ chế sửa hẹp nhất xử lý được cả hai lý do, theo thứ tự ưu tiên: (a) cho phép tìm kiếm xuyên khối có kiểm soát đối với câu hỏi chứa định danh chính xác (mã bản vẽ, mã linh kiện, ký hiệu dạng g1/g2 kèm mã tài liệu) — tài liệu ở khối khác vẫn được xét khi định danh khớp chính xác; (b) tăng trọng số khớp định danh chính xác trong xếp hạng để mảnh chứa mã định danh nguyên văn không bị từ nhiễu đẩy xuống hạng sâu. Không gán lại nhãn khối của tài liệu nếu không chứng minh được nhãn hiện tại là sai.
2. Kiểm thử bảo vệ hai chiều, cả hai bắt buộc đạt:
   - Câu `Q0668` phải lấy lại được mảnh đích vào ngữ cảnh và trả lời đúng qua đường đo (đạt điểm theo thang chấm).
   - Khâu lọc khối không bị mở toang: chạy đối chứng trên bộ 50 câu — không câu nào khác bị thay đổi tập bằng chứng theo hướng xấu đi, và toàn bộ 7 câu bị chặn vì thiếu dữ liệu thật phải vẫn bị chặn nguyên.
3. Đo lại đủ 50 câu tại máy nhà, chỉ dùng bộ xử lý trung tâm, chấm bằng thước đo đã chuẩn hoá, so sánh từng câu với hai lượt đo lặp gần nhất (67,84 và 69,84): báo số câu tăng, giữ nguyên, giảm.
4. Nghiệm thu dùng thật: mở ứng dụng ở chế độ chỉ dùng bộ xử lý trung tâm, hỏi câu Q0668 qua giao diện cùng 2 câu đối chứng thuộc khối khác, nộp đáp án nguyên văn và ảnh chứa trọn thân đáp án trong khung hình, cùng một phiên mới. Ghi rõ mã commit đang chạy.

## Rào cứng

- Không hạ ngưỡng cổng kiểm chứng 0,60. Không ghi vào chỉ mục production (vé này chỉ sửa mã đường truy hồi). Không đổi bộ đề và thang chấm. Không merge `main`.
- Cơ chế sửa phải có đường hoàn lui rõ ràng (cờ tắt hoặc hoàn nguyên commit) và ghi vào báo cáo.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để chạy tiếp được.
