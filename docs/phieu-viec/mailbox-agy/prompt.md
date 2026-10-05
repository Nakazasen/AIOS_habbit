# VÉ: SMA-GATE-REALDATA-HOME (kiểm chứng cổng SMA(20) trên log JIG thật)

- Mã vé: `SMA-GATE-REALDATA-HOME`
- Role OMP gợi ý: DEFAULT (chẩn đoán + chạy phân tích trên dữ liệu thật)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md`

## Bối cảnh

Cổng cảnh báo xu hướng SMA(20) (`trend_alerts.py`: điểm bất thường = |x − SMA20| > k·σ,
chỉ báo khi ≥3 điểm bất thường liên tiếp hoặc ≥3/5 điểm gần nhất) đã có từ 03/10
(commit 846713e), gate cả 3 đường log trong `jig_chat_wire.py`, test 35/35 xanh.
Nhưng mới chỉ kiểm trên dữ liệu tổng hợp — chưa chạy trên log JIG thật.
Bước 2 lộ trình tool JIG (hạn 15/10): xác nhận/chỉnh sửa chức năng Bước 1.
Vé này đo chất lượng cổng SMA trên dữ liệu thật để Bước 2 có số liệu.

## Việc cần làm

1. Nạp file CSV log JIG thật đã dùng ở vé J2 (`2026_08_Master.csv`, 132 dòng —
   nếu không tìm thấy đường dẫn, ghi rõ vào báo cáo và dừng, không bịa dữ liệu).
2. Với 3 chỉ số đã biết có vi phạm ngưỡng (J2 đã đo):
   - Độ ẩm: 11 điểm dưới 40% (thấp nhất 33,9%)
   - TaktTime: 8 điểm vượt 200s (cao nhất 297s)
   - Nhiệt độ: 2 điểm dưới 20°C (thấp nhất 19,2%)
   chạy `danh_gia_xu_huong_sma` trên chuỗi giá trị từng chỉ số, ghi lại:
   số điểm bất thường SMA phát hiện + số cảnh báo xu hướng sau
   `gate_canh_bao_theo_xu_huong`.
3. Đối chiếu với 21 vi phạm ngưỡng đơn điểm: bao nhiêu cái bị gate chặn
   (đúng luật "không báo từ một điểm xấu đơn lẻ"), bao nhiêu cái thành
   cảnh báo xu hướng thật. Liệt kê cụ thể từng chỉ số.
4. Đánh giá tham số k=3.0 hiện tại trên dữ liệu thật: hợp lý hay quá chặt/quá lỏng?
   Đề xuất giữ nguyên hoặc chỉnh (kèm số liệu, không đoán).
5. Viết báo cáo `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md` đủ 4 mục trên
   + kết luận "đạt / cần chỉnh gì cho Bước 2".

## Cấm

- Không sửa code `src/` trong vé này (chỉ đọc + chạy phân tích).
- Không merge `main`. Không ghi/xóa dữ liệu gốc.

## Cổng nghiệm thu

- Script phân tích chạy được, tái lập được (ghi rõ câu lệnh + đường dẫn file).
- Báo cáo đủ 4 mục + kết luận rõ ràng.
- `py_compile` sạch cho mọi file mới (tương thích Python 3.11).

## Quy ước

- Heartbeat: mốc tiến độ tối thiểu 15 phút/lần vào `trang-thai.md`.
- Checkpoint/resume: lưu kết quả trung gian để chạy lại không mất.
