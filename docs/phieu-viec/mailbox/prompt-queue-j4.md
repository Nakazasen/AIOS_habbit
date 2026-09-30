# Vé J4 — JIG: chạy thử nghiệm (độ ổn định + chính xác cảnh báo)

LANE: [NHÀ] + [NGƯỜI DÙNG] — OMP theo dõi kỹ thuật, người dùng công ty đánh giá nghiệp vụ.

## Bối cảnh
Theo dõi độ ổn định và độ chính xác của kết quả cảnh báo trên dữ liệu thật.

## Việc cần làm
1. Chạy tool trên luồng dữ liệu thật một thời gian: ghi uptime, số cảnh báo bắn,
   số cảnh báo đúng/sai (đối chiếu thực tế sản xuất).
2. Đo: tỉ lệ cảnh báo đúng, cảnh báo nhầm, cảnh báo sót.
3. Vấn đề phát hiện → backlog sửa.

## Tiêu chí ĐẠT
- Báo cáo có số đo thật (uptime, đúng/sai/nhầm/sót). Đạt ngưỡng nào thì do user chốt
  sau khi thấy số — vé này chỉ đo trung thực, không tự đặt ngưỡng.
