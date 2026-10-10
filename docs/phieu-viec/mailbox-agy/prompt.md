# VÉ: DATA-INGEST-MISSING5-HOME (nạp 5 tệp nguồn còn thiếu vào chỉ mục tại máy nhà)

- Mã vé: `DATA-INGEST-MISSING5-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/data-ingest-missing5-home.md`
- Bối cảnh: vé chẩn đoán `SYNTH-RETRIEVAL-GAP-DIAG-HOME` xác nhận 7 trên 8 câu bị mất điểm là do kho thiếu dữ liệu thật: 5 tệp nguồn chưa từng được nạp vào chỉ mục production. Giá trị kỳ vọng tối đa 21 điểm trên thang 150 (7 câu nhân 3 điểm) — đòn bẩy lớn nhất còn lại để vượt ngưỡng go-live 1,5, với điều kiện sau nạp các câu đó truy hồi và trả lời được.
- Gói nguồn (chỉ dùng bản này): `goi-nguon-missing5-v2.zip`, 8.834.546 byte, mã băm SHA-256 toàn gói `ae27c98489cfda121fee864f83ac8b50b1cd3d96b8829689e22fdaddb7bd3b3f`. Liên kết tải trực tiếp: https://drive.usercontent.google.com/download?id=1MYW4emjPn7PF39YWOf9USYHZGnl6y0vX&export=download&confirm=t (mã tệp Drive `1MYW4emjPn7PF39YWOf9USYHZGnl6y0vX`). Mã băm SHA-256 từng tệp trong gói: `2026_08_Error.csv` = `07d3bec518e00ffa30fcbb39641a835a66979372f83f22372b46a15757c82894`; `2026_08_Error_BowOverAdjust.csv` = `8fc50693fdc5c932d69974092a7b470b56cb35b481c261981ea72940f23f5139`; `2026_08_Spec.csv` = `cab93531f3142e9e02e19a41f1177c434f131a0aeda0c50247719c3c42ca64d2`; `2026_08_UnitTest.csv` = `9fbe87e8270586182b3faf9bf87fc517ec31eabfa45dc36a33d6f15830b58ad7`; `AI cảnh báo lỗi LSU.pptx` = `6883f03ea0c9e533a45ff6573de4b28fe657671e5f6ee31af48ad0cc3e5316ff`. Trên Drive còn bản đầu `goi-nguon-missing5.zip` — KHÔNG dùng (2 tệp chọn sai biến thể).

## Mục 0 — Xử lý tồn đọng của vé Q0668 (làm trước mọi thao tác ghi chỉ mục)

### 0.1 Chốt lại đường chấm và đính chính câu Q0824

- Dùng đúng một đường chấm đã đóng dấu trong kho: bộ câu hỏi `tests/fixtures/eval/lsu_quality_50_questions.json` và hàm chấm `src/aios_habit/quality_harness.py` tại commit đang chạy. Ghi rõ commit đó vào báo cáo. Không sửa bộ đề, không sửa hàm chấm trong vé này.
- Chấm lại cả ba tệp dữ kiện đã có (`rows-synth-remeasure-round1-home.jsonl`, `rows-synth-remeasure-round2-home.jsonl`, `rows-synth-q0668-filter-fix-home.jsonl`) bằng đúng đường chấm trên và nộp bảng đối chiếu trong báo cáo. Số điều phối đã chấm độc lập để đối chiếu: lượt 1 = 67,50; lượt 2 = 68,50; lượt Q0668 = 74,50. Nếu số của bạn lệch, dừng Mục 0.1, ghi rõ nguyên nhân lệch, không tự chọn số khác.
- Đính chính câu `Q0824`: đáp án "không đủ bằng chứng" giống hệt ở cả ba lượt; điểm 1,0 mà scorer cho ở lượt Q0668 là điểm giả (từ khoá `NG` khớp chuỗi con "ng" trong chữ "không"; từ khoá `OK` không khớp). Về nội dung, câu này bị chặn đúng ở cả ba lượt và không phải cải thiện do bản vá Q0668. Mọi so sánh điểm từ vé này trở đi phải dùng bộ số đã chấm lại nhất quán ở mục này, không trộn với tổng đã ghi sẵn trong các tệp dữ kiện cũ.

### 0.2 Chẩn đoán và chạy lại đường giao diện cho câu Q0668

- Hiện tượng phải xử lý: ở đường đo, câu Q0668 lấy lại được mảnh đích của tệp `3V2ND19040-MOUNT LD BLOCK LOT 18.8.2026.xlsx` và qua cổng kiểm chứng; nhưng ở phiên giao diện `CONV-Q0668-6AC99DD7` cùng câu hỏi lại đi qua làn `nakazasen_router`, không lấy được mảnh đích và kết luận chưa đủ bằng chứng theo cách hiểu nhãn chân tín hiệu. Truy vết đường đi thật của giao diện (chế độ tìm, làn định tuyến, khối tri thức được chọn, hàm truy hồi được gọi) so với đường đo, chỉ rõ khâu khác nhau làm mất mảnh đích.
- Nếu gốc rễ nằm ở mã trong cùng chuỗi truy hồi/định tuyến thì sửa hẹp nhất, commit riêng cho Mục 0.2, chạy lại các tệp kiểm thử liên quan. Nếu gốc rễ nằm ở cấu hình hoặc phiên chạy sai thì chứng minh bằng nhật ký và chạy lại đúng cấu hình. Không chấp nhận chỉ chụp lại ảnh mà không có kết luận gốc rễ.
- Chạy lại nghiệm thu giao diện trong một phiên mới, chỉ dùng bộ xử lý trung tâm, đủ 3 câu: Q0668, Q0718, Q0709. Câu Q0668 phải trả lời đúng: nominal 13.81, dung sai +0.12/-0.05, giới hạn trên 13.93, giới hạn dưới 13.76, nguồn là tệp bảng tính đích nêu trên. Ảnh phải chứa trọn thân đáp án trong khung hình (ảnh dài hoặc nhiều ảnh liên tiếp cho cùng một câu đều được, miễn là đọc được toàn bộ đáp án). Tệp dữ kiện ghi mã commit đang chạy là mã đã có thật trên kho sau khi đẩy, không ghi mã local chưa đẩy.
- Nếu chẩn đoán cho thấy gốc rễ nằm ngoài chuỗi truy hồi/định tuyến và không sửa hẹp được trong vé này: ghi đúng điểm gãy và bằng chứng truy vết vào báo cáo, chuyển sang Mục 1, không để toàn vé đứng chờ; báo cáo cuối không được ghi Mục 0.2 là đạt.

## Việc phải làm (sau Mục 0)

1. Nhận gói nguồn, kiểm chứng mã băm của gói và của từng tệp khớp dữ kiện ở đầu vé này. Lưu ý đối chiếu nội dung: xác nhận đúng tệp chứa dữ kiện đích của các câu hỏi (đúng tháng, đúng loại bản ghi) trước khi nạp, và ghi rõ tên tệp thực tế đã nạp cho từng tệp đích.
2. Sao lưu mới toàn bộ chỉ mục production và kiểm tra toàn vẹn đạt trước khi đụng vào bất kỳ thao tác ghi nào. Ghi mã băm và kích thước của chỉ mục trước khi nạp.
3. Chạy thử không ghi trên cả 5 tệp: báo số tài liệu mới, số mảnh dự kiến sinh ra, và đối chiếu không trùng lặp với tài liệu sẵn có.
4. Nạp theo quy trình hiện hành của hệ thống (qua kho thử trước, theo đợt có điểm kiểm, được dùng card đồ hoạ cho khâu nhúng vì đây là việc lập chỉ mục), rồi mới hợp nhất vào chỉ mục production. Sau nạp: kiểm tra toàn vẹn đạt, ghi số tài liệu và số mảnh mới, mã băm và kích thước mới của chỉ mục.
5. Kiểm chứng sau nạp bằng chính 7 câu hỏi trước đây bị chặn (`Q0849`, `Q0850`, `Q1034`, `Q0620`, `Q0824`, `Q0828`, `Q0843`): chạy qua đường đo, chấm bằng đường chấm đã chốt ở Mục 0.1, báo điểm từng câu trước và sau nạp. Riêng `Q0824`: điểm trước nạp ghi theo nội dung thật là bị chặn (scorer cho 1,0 điểm giả — xem Mục 0.1), không ghi là 1,0 điểm nội dung. Kiểm tra thêm câu `Q0668` sau nạp để chắc chắn không thụt lùi.
6. Đo lại đủ 50 câu (chỉ dùng bộ xử lý trung tâm cho phần hỏi đáp) để có tổng điểm mới, so với mốc đã chấm lại nhất quán ở Mục 0.1 (trung bình hai lượt cũ 68,00; lượt Q0668 là 74,50).
7. Nghiệm thu dùng thật: mở ứng dụng, hỏi 3 câu thuộc nhóm vừa nạp qua giao diện, nộp đáp án nguyên văn và ảnh chứa trọn thân đáp án trong khung hình, cùng một phiên mới. Ghi rõ mã commit đang chạy.

## Rào cứng

- Ba rào bắt buộc cho mọi thao tác ghi chỉ mục: sao lưu mới toàn vẹn trước, chạy thử không ghi trước, nạp theo đợt có điểm kiểm để ngắt giữa chừng vẫn tiếp tục được. Thiếu một trong ba thì dừng và báo lại, không nạp tiếp.
- Không hạ ngưỡng cổng kiểm chứng 0,60. Không đổi bộ đề và thang chấm. Không merge `main`.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để chạy tiếp được.
