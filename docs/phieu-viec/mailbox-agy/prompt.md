# VÉ: SYNTH-DEEPSEEK-AB-HOME (đo thử DeepSeek V4.1 Flash trên bộ 50 câu — đóng vòng quyết định model tổng hợp)

- Mã vé: `SYNTH-DEEPSEEK-AB-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính, CPU-only, không dùng GPU)
- Báo cáo: `docs/phieu-viec/ket-qua/synth-deepseek-ab-home.md`
- Căn cứ: user QUYẾT tại chat 2026-10-08 ~18:17 +07: "đo thử DeepSeek với máy nhà để close vòng đó đi". Bối cảnh: 3 thực nghiệm liên tiếp đã chốt trần của nhóm model miễn phí qua tuyến pool Command Code (GPA ~1,21–1,25; validated chỉ 0–2/50 mỗi model khi ép làm model chính). DeepSeek V4.1 Flash là phương án trả phí rẻ user đã duyệt làm dự phòng từ 07/10 (giá qua Command Code: $0,15 vào / $0,60 ra mỗi 1M token). Vé này đo nó trên ĐÚNG bộ đề + thang chấm + runner của các lane pool trước để so sánh ngang hàng và chốt cấu hình tổng hợp cho bản go-live.

## Việc phải làm

1. **Chuẩn bị tuyến:** qua tài khoản Command Code (gói GOAT của user), xác nhận model DeepSeek V4.1 Flash có mặt trong danh sách model của tuyến (tra trong cấu hình/hệ thống — không đoán theo nhãn). Nếu tuyến không có model này: DỪNG và báo cáo đúng điểm đó, không tự ý đổi sang tuyến/nhà cung cấp khác.
2. **Ép làm model chính:** cấu hình tạm thời để DeepSeek V4.1 Flash là model chính (primary) duy nhất cho lượt đo — theo đúng mẫu vé `SYNTH-MODEL-AB-HOME` (tắt luân chuyển/failover sang model free trong lượt đo để số đo thuần một model). Ghi rõ cấu hình trước khi đo và **khôi phục nguyên trạng cấu hình pool hiện tại ngay sau khi đo xong**.
3. **Đo đủ 50 câu** bằng đúng runner + bộ đề + rubric của lane pool (`ROUTER-POOL-COMMANDCODE-HOME`): đếm validated/fallback theo trường `che_do` từ các dòng kết quả (không dùng bộ đếm tổng hợp của runner — đã có bài học đếm sai). Ghi: GPA + tổng điểm /150, validated x/50, fallback x/50, tỉ lệ câu không trích dẫn (uncited), thời gian mỗi câu (ghi CẢ trung bình số học lẫn số giữa), số credits thực tế bị trừ cho lượt đo (đọc từ tài khoản/hệ thống — chỉ ghi con số tổng, không ghi bất kỳ ký tự nào của key), băm chỉ mục trước/sau phải khớp tuyệt đối.
4. **Bảng so sánh ngang hàng** với: pool free hiện tại (GPA 1,25; validated 1/50) và từng model free ở vé A/B trước (ling-3.1: 1,23/v2; sante: 1,21/v0; laguna: 1,21/v2). Kèm 3 đáp án mẫu nguyên văn của DeepSeek (1 câu đạt validated, 1 câu rơi fallback, 1 câu điểm thấp nhất) để điều phối đọc chất lượng thật.
5. **Kết luận dứt khoát theo số:** DeepSeek có vượt rõ rệt hay không (tham chiếu: đạt GPA ≥ 1,5 hoặc validated cải thiện có ý nghĩa so với 1/50), và đề xuất cấu hình cho bản go-live (DeepSeek làm chính / làm dự phòng mạnh sau free / không dùng).

## Rào cứng

- Trần chi phí cho lượt đo: **tối đa $2 credits** — chạm trần thì dừng đo, báo cáo phần đã có (ước tính lượt 50 câu chỉ tốn dưới $0,50; vượt xa con số đó là dấu hiệu cấu hình sai).
- Chỉ ghi cấu hình tạm thời phục vụ lượt đo; đo xong khôi phục cấu hình pool như cũ và xác nhận bằng mốc trong mailbox. Không ghi chỉ mục; không đụng bộ kiểm định/rubric; không merge `main`.
- Tuyệt đối không in bất kỳ ký tự nào của API key trong báo cáo/log/mailbox — chỉ ghi biến "key có mặt/không có mặt" nếu cần.
- Kỷ luật số liệu: mọi con số phải tái lập được từ file kết quả của lượt đo. Mốc tiến độ tối thiểu 15 phút/lần + checkpoint/resume.
