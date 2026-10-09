# VÉ: SYNTH-TERM-EXTRACT-FIX-HOME (sửa khâu tách thuật ngữ tiếng Việt làm sai lệch độ phủ bằng chứng)

- Mã vé: `SYNTH-TERM-EXTRACT-FIX-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-term-extract-fix-home.md`
- Bối cảnh: vé rà cổng kiểm chứng `SYNTH-EVIDENCE-GATE-AUDIT-HOME` đã kết luận giữ nguyên ngưỡng độ phủ 0,60 (hạ ngưỡng ở mọi mức đều thả lọt 100% câu thiếu bằng chứng thật), nhưng đồng thời phát hiện một ca oan có thật với nguyên nhân khác hẳn: câu `Q0695` mất 3,0 điểm vì khâu tách thuật ngữ của câu hỏi (`extract_content_terms` trong gói `rag_v2`) tính cả các hư từ tiếng Việt như "ủng", "hộ", "chung", "riêng", "hay", "và" vào tập thuật ngữ dùng để tính độ phủ bằng chứng. Những từ này không bao giờ xuất hiện trong tài liệu kỹ thuật (chủ yếu tiếng Nhật và tiếng Anh), nên độ phủ bị kéo xuống giả tạo (ca Q0695: 8/14 = 0,5714, thiếu đúng 0,0286 so với ngưỡng) dù bằng chứng thực chất là đủ. Đây là lỗi ở cách đo độ phủ, không phải ở ngưỡng an toàn.

## Việc phải làm

1. Sửa khâu tách thuật ngữ để loại các hư từ và từ nối tiếng Việt khỏi tập thuật ngữ dùng tính độ phủ bằng chứng. Liệt kê đầy đủ danh sách từ bị loại vào báo cáo. Phạm vi an toàn bắt buộc: hàm tách thuật ngữ hiện được dùng ở nhiều điểm trong đường truy hồi (xem các điểm gọi trong `src/aios_habit/rag_v2/index.py`), nên thay đổi phải được khoanh đúng vào tập thuật ngữ phục vụ tính độ phủ — hoặc, nếu buộc phải đổi ở hàm dùng chung, phải chứng minh bằng số liệu rằng tập mảnh truy hồi của bộ 50 câu không thay đổi trước và sau sửa.
2. Kiểm thử bảo vệ hai chiều, cả hai đều bắt buộc đạt:
   - Ca oan phải được gỡ: tính lại ca `Q0695` cho thấy độ phủ sau sửa phản ánh đúng bằng chứng thực chất và câu được thông cổng.
   - Cổng vẫn chặn đúng: toàn bộ 7 câu chẩn đoán ngắn bị chặn có căn cứ ở vé trước (`Q0620`, `Q0668`, `Q0824`, `Q0843`, `Q0849`, `Q0850`, `Q1034`) phải vẫn bị chặn sau sửa, vì bằng chứng của chúng thiếu thật.
3. Đo lại đủ 50 câu tại máy nhà, chỉ dùng bộ xử lý trung tâm, chấm bằng thước đo đã chuẩn hoá (sau vé `EVAL-NORMALIZE-FIX-HOME`), so sánh từng câu với mốc 72,33 trên 150 (điểm trung bình 1,447): báo số câu tăng, giữ nguyên, giảm và tổng điểm mới.
4. Nghiệm thu dùng thật: mở ứng dụng ở chế độ chỉ dùng bộ xử lý trung tâm, hỏi 3 câu qua giao diện, nộp đáp án nguyên văn và ảnh chứa đáp án trong khung hình. Ghi rõ mã commit đang chạy.

## Lưu ý thực tế về tài khoản mô hình

Tài khoản dùng chung đang ở gần trần tuần và trần tháng. Lượt gọi mô hình bị từ chối tạm thời thì ghi mốc, chờ một nhịp rồi chạy tiếp bằng khả năng chạy tiếp của trình đo — không bỏ dở vé, không đổi sang mô hình ngoài chuỗi đã chốt.

## Rào cứng

- Không hạ ngưỡng độ phủ 0,60 trong `src/aios_habit/rag_v2/evidence.py` — vé này sửa cách tính độ phủ cho đúng, không nới cổng an toàn. Không ghi vào chỉ mục production. Không đổi bộ đề và thang chấm. Không merge `main`.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit (bài học kỷ luật đã nhắc nhiều lần trong ngày).
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để chạy tiếp được.
