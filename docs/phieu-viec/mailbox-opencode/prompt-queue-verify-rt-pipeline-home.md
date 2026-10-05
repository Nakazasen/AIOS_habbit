# Vé VERIFY-RT-PIPELINE-HOME — Kiểm chứng đường log realtime trước khi nối cảnh báo

**Máy thực hiện:** NHÀ h410asrock (thợ opencode).
**Role gợi ý:** DEFAULT (chạy thử + đo).

## Bối cảnh

Vé `LSU-ALERT-REALTIME-PC0575` (máy công ty) sẽ nối đường log realtime vào cổng
SMA(20). Trước đó cần chắc các component realtime trong repo chạy được —
tránh sang máy công ty mới phát hiện hỏng.

## Việc cần làm

1. Rà soát `src/aios_habit/production_prediction/rt_consumer.py` và `stream_api.py`:
   còn chạy được không? (import, khởi tạo, đọc config).
2. Dùng `2026_08_Master.csv` (132 dòng thật) giả lập feed realtime
   (đọc từng dòng theo nhịp thời gian) → đẩy qua consumer → ghi nhận output.
3. Đo: consumer có mất dòng nào không? độ trễ mỗi dòng bao nhiêu?
4. Báo cáo `docs/phieu-viec/ket-qua/verify-rt-pipeline-home.md`:
   component nào OK / component nào hỏng / cần sửa gì trước khi PC0575 dùng.

## Rào cứng

- Chỉ chạy thử + đo, KHÔNG sửa code component trong vé này
  (hỏng thì liệt kê để vé sửa riêng).
- Không merge `main`. Python 3.11.
- 1 file 1 đứa: không đụng `trend_alerts.py` (OMP) và không đụng UI (agy đã xong).
