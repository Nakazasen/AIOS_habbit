# VÉ: TEST-E2E-GUARD-HOME (bịt điểm chập chờn theo môi trường của ca kiểm thử đóng gói đầu-cuối)

- Mã vé: `TEST-E2E-GUARD-HOME`
- Role gợi ý: DEFAULT (opencode — thợ phụ tạm thời, máy nhà `h410asrock`)
- Báo cáo: `docs/phieu-viec/ket-qua/test-e2e-guard-home.md`
- Bối cảnh: vé `TEST-SUITE-CONFIRM-HOME` chạy lại toàn bộ bộ kiểm thử cho kết quả 1 ca hỏng / 4.218 đạt / 66 bỏ qua / 0 lỗi. Ca hỏng duy nhất là ca đóng gói đầu-cuối `test_packaged_desktop_e2e_rag_to_atlas`: ở lượt chạy đầy đủ dưới tải nặng, lượt kiểm thử lồng bên trong vượt trần cứng 300 giây nên bị tính hỏng vì hết giờ; chạy riêng trên cùng máy thì đạt trong ~140 giây. Điều phối tự chạy kiểm chứng trên máy sạch và gặp một kiểu đỏ môi trường thứ hai của chính ca này: máy kiểm chứng không có thư mục model tại các đường dẫn ứng viên nên ca đỏ ngay ở bước tìm model. Cả hai kiểu đỏ đều là điều kiện môi trường khách quan, không phải hành vi sai của mã — nhưng chúng làm tín hiệu của bộ kiểm thử không còn sạch tuyệt đối.

## Việc phải làm

1. Cho ca `test_packaged_desktop_e2e_rag_to_atlas` hai điều kiện bỏ qua rõ ràng, theo đúng mẫu hệ thống đã áp dụng ở vé dọn dẹp trước đây:
   - Khi không tìm được thư mục model bằng chính hàm tìm model của hệ thống: bỏ qua kèm lý do ghi rõ tình trạng không có model tại máy.
   - Khi lượt kiểm thử lồng hết giờ theo đúng lỗi hết thời gian chờ của tiến trình con: bỏ qua kèm lý do về tốc độ máy dưới tải.
2. Giữ nguyên mọi khẳng định hành vi của ca: trên máy có model và chạy kịp giờ, ca vẫn phải chạy thật toàn bộ và vẫn đỏ khi có khẳng định nào sai. Không nới trần 300 giây, không giảm bớt bước kiểm tra nào.
3. Kiểm chứng sau sửa: chạy riêng ca này (phải đạt hoặc bỏ qua đúng một trong hai điều kiện trên, kèm lý do in ra được), rồi chạy toàn bộ tệp chứa ca này để bảo đảm không ca nào khác trong tệp bị ảnh hưởng.

## Rào cứng

- Chỉ sửa tệp kiểm thử chứa ca này; không sửa mã chạy thật. Không ghi chỉ mục (băm trước/sau khớp nếu có đọc tới). Không merge `main`.
- Mốc tiến độ tối thiểu 15 phút/lần.
