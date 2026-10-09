# VÉ: DATA-INGEST-MISSING5-HOME (nạp 5 tệp nguồn còn thiếu vào chỉ mục tại máy nhà)

- Mã vé: `DATA-INGEST-MISSING5-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/data-ingest-missing5-home.md`
- Điều kiện mở vé: điều phối thông báo trong `trang-thai.md` rằng gói nguồn đã sẵn sàng kèm mã băm của gói (điều phối đóng gói 5 tệp từ kho dữ liệu đã kéo về và chuyển qua kênh Drive như các đợt trước). Trước khi có thông báo đó, vé ở trạng thái chờ gói — thợ ghi mốc chờ, không tự đi tìm tệp ở nơi khác.
- Bối cảnh: vé chẩn đoán `SYNTH-RETRIEVAL-GAP-DIAG-HOME` xác nhận 7 trên 8 câu bị mất điểm vì cổng kiểm chứng thực ra thiếu dữ liệu thật: 5 tệp nguồn chưa từng được nạp vào chỉ mục production. Điều phối đã xác minh cả 5 tệp đều có sẵn trong kho dữ liệu nguồn đã kéo về từ Drive: `2026_08_Error_BowOverAdjust.csv`, `2026_08_Error.csv`, `2026_08_UnitTest.csv`, `2026_08_Spec.csv` và `AI cảnh báo lỗi LSU.pptx`. Giá trị kỳ vọng tối đa 21 điểm trên thang 150 (7 câu nhân 3 điểm) — đây là đòn bẩy lớn nhất còn lại để vượt ngưỡng go-live 1,5, với điều kiện sau nạp các câu đó truy hồi và trả lời được.

## Việc phải làm

1. Nhận gói nguồn, kiểm chứng mã băm của gói và của từng tệp khớp dữ kiện điều phối ghi trong `trang-thai.md`. Lưu ý đối chiếu nội dung: một số tệp trong kho nguồn mang tiền tố tên (ví dụ dạng `2ND-1035-1_2026_08_Error.csv`) — xác nhận đúng tệp chứa dữ kiện đích của các câu hỏi (đúng tháng, đúng loại bản ghi) trước khi nạp, và ghi rõ tên tệp thực tế đã nạp cho từng tệp đích.
2. Sao lưu mới toàn bộ chỉ mục production và kiểm tra toàn vẹn đạt trước khi đụng vào bất kỳ thao tác ghi nào. Ghi mã băm và kích thước của chỉ mục trước khi nạp.
3. Chạy thử không ghi trên cả 5 tệp: báo số tài liệu mới, số mảnh dự kiến sinh ra, và đối chiếu không trùng lặp với tài liệu sẵn có.
4. Nạp theo quy trình hiện hành của hệ thống (qua kho thử trước, theo đợt có điểm kiểm, được dùng card đồ hoạ cho khâu nhúng vì đây là việc lập chỉ mục), rồi mới hợp nhất vào chỉ mục production. Sau nạp: kiểm tra toàn vẹn đạt, ghi số tài liệu và số mảnh mới, mã băm và kích thước mới của chỉ mục.
5. Kiểm chứng sau nạp bằng chính 7 câu hỏi trước đây bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843`): chạy qua đường đo, chấm bằng thước đo đã chuẩn hoá, báo điểm từng câu trước và sau nạp.
6. Đo lại đủ 50 câu (chỉ dùng bộ xử lý trung tâm cho phần hỏi đáp) để có tổng điểm mới so với mốc trung bình 68,84.
7. Nghiệm thu dùng thật: mở ứng dụng, hỏi 3 câu thuộc nhóm vừa nạp qua giao diện, nộp đáp án nguyên văn và ảnh chứa trọn thân đáp án trong khung hình, cùng một phiên mới. Ghi rõ mã commit đang chạy.

## Rào cứng

- Ba rào bắt buộc cho mọi thao tác ghi chỉ mục: sao lưu mới toàn vẹn trước, chạy thử không ghi trước, nạp theo đợt có điểm kiểm để ngắt giữa chừng vẫn tiếp tục được. Thiếu một trong ba thì dừng và báo lại, không nạp tiếp.
- Không hạ ngưỡng cổng kiểm chứng. Không đổi bộ đề và thang chấm. Không merge `main`.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần.
