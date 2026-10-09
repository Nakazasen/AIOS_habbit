# VÉ: SYNTH-REMEASURE-STABLE-HOME (đo lặp hai lượt để có con số chất lượng quyết định)

- Mã vé: `SYNTH-REMEASURE-STABLE-HOME`
- Role gợi ý: DEFAULT (agy — thợ chính, máy nhà h410asrock)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-remeasure-stable-home.md`
- Điều kiện mở vé: vé `SYNTH-TERM-EXTRACT-FIX-HOME` đã hoàn tất (nếu vé đó không áp thay đổi nào thì ghi rõ trong báo cáo và vẫn đo ở cấu hình hiện hành).
- Bối cảnh: sau chuỗi sửa (trích dẫn dự phòng, chuẩn hoá thước đo, rà cổng kiểm chứng), con số chất lượng tham chiếu hiện tại của máy nhà là 72,33 trên 150 (điểm trung bình 1,447) — nhưng đó là điểm chấm lại ngoại tuyến trên đáp án của một lượt đo cũ. Dao động tự nhiên của mô hình miễn phí đã được đo thấy đủ lớn để nuốt hiệu quả cỡ vài điểm (một nhóm câu không đổi ngữ cảnh cũng lệch hơn 5 điểm giữa hai lượt), nên một lượt đo đơn lẻ không đủ căn cứ kết luận đạt hay chưa đạt ngưỡng go-live 1,5. Vé này tạo con số quyết định bằng đo lặp.

## Mục 0 — Việc đính chính và làm lại từ verdict vé trước (làm trước tiên, mỗi việc một commit riêng)

Vé `SYNTH-TERM-EXTRACT-FIX-HOME` đã được verdict **ĐẠT phần chính — CHƯA ĐẠT phần nghiệm thu dùng thật**. Phần chính (sửa khâu tách thuật ngữ, kiểm thử bảo vệ hai chiều, đo lại 50 câu đạt 69,84/150) đã được công nhận, không làm lại. Hai tồn đọng bắt buộc xử lý ở Mục 0 này:

0.1. **Đính chính kích thước tệp báo cáo cũ:** trong `docs/phieu-viec/ket-qua/synth-term-extract-fix-home.md`, con số kích thước của chính tệp báo cáo ghi 19.860 byte là sai — kích thước thật của blob đã nộp vào kho là **19.939 byte**. Sửa đúng con số này (chỉ sửa con số đó), commit riêng.

0.2. **Làm lại nghiệm thu dùng thật của vé cũ:** lượt nghiệm thu trước bị bác vì bằng chứng lỗi — đáp án ghi cho câu `Q0718` trùng nguyên văn đáp án của `Q0709` (không trả lời đúng câu hỏi DMT–PMT), mã phiên của câu 2 và 3 là phiên cũ `CONV-ENTITY-20958ED` của vé trước nữa, và các ảnh chụp không chứa thân đáp án trong khung hình. Làm lại đủ 3 câu (`Q0695`, `Q0718`, `Q0709`) trong **một phiên hội thoại hoàn toàn mới** tại commit hiện hành, cấu hình chỉ dùng bộ xử lý trung tâm: đáp án nguyên văn phải trích từ đúng phiên mới đó, ảnh chụp phải chứa trọn thân đáp án của từng câu trong khung hình (tự mở ảnh kiểm tra trước khi nộp). Nộp báo cáo bổ sung `docs/phieu-viec/ket-qua/ui-synth-term-extract-fix-redo.md` kèm ảnh và tệp chi tiết mới; kích thước tệp đo trên blob đã nộp như thường lệ.

## Việc phải làm

1. Chạy hai lượt đo độc lập, mỗi lượt đủ 50 câu, cùng một cấu hình tốt nhất hiện hành tại máy nhà: chuỗi mô hình đã chốt trong cấu hình go-live, cơ chế nới ngữ cảnh theo thực thể đang bật, chỉ dùng bộ xử lý trung tâm. Hai lượt chạy nối tiếp nhau, không thay đổi cấu hình hay mã nguồn giữa hai lượt.
2. Chấm cả hai lượt bằng thước đo đã chuẩn hoá (sau vé `EVAL-NORMALIZE-FIX-HOME`). Báo cáo: tổng điểm và điểm trung bình của từng lượt, điểm trung bình cộng của hai lượt, độ lệch giữa hai lượt, và so sánh từng câu giữa hai lượt (số câu ổn định, số câu dao động). Kết luận rõ: con số quyết định là trung bình hai lượt, và nó đứng ở đâu so với ngưỡng 1,5.
3. Nghiệm thu dùng thật kèm theo ở một trong hai lượt: mở ứng dụng, hỏi 3 câu qua giao diện, nộp đáp án nguyên văn và ảnh chứa đáp án trong khung hình. Ghi rõ mã commit đang chạy.

## Lưu ý thực tế về tài khoản mô hình

Đây là vé đốt mô hình nhiều nhất trong chuỗi (hai lượt nhân 50 câu). Tài khoản dùng chung đang ở gần trần tuần và trần tháng: chạy theo nhịp bền vững, lượt gọi bị từ chối tạm thời thì ghi mốc, chờ rồi chạy tiếp bằng điểm kiểm của trình đo — thà chậm mà đủ hai lượt, không chạy dồn dập để bị chặn cứng giữa chừng, không đổi sang mô hình ngoài chuỗi đã chốt.

## Rào cứng

- Chỉ đo và ghi: không sửa mã, không sửa thang chấm, không ghi vào chỉ mục production. Không merge `main`.
- Kích thước tệp trong báo cáo phải đo trên bản đã nộp vào kho sau khi commit.
- Mốc tiến độ tối thiểu 15 phút/lần, kèm điểm kiểm để ngắt giữa chừng vẫn chạy tiếp được.
