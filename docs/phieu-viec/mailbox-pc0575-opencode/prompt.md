# Vé LSU-ALERT-REALTIME-PC0575 — Nối consumer realtime JIG qua cổng xu hướng SMA(20), cảnh báo trong chat

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Thợ:** opencode.
**Role gợi ý:** DEFAULT (code + test).

## Bối cảnh

- Hạ tầng đã có, KHÔNG làm lại:
  - `src/aios_habit/production_prediction/trend_alerts.py`: `sma()`, `detect_abnormal_sma()`,
    `danh_gia_xu_huong_sma()`, `gate_canh_bao_theo_xu_huong()` (commit `846713e`, 03/10).
  - `src/aios_habit/production_prediction/rt_consumer.py`: poll `GET /api/v1/jig/events`
    theo cursor, dựng `build_realtime_alert_card`.
  - `rt_replay.py`, `jig_chat_wire.py` (đã gate 3 đường log depth/IRIS/dòng JIG).
- Lỗ hổng đã xác minh trên code: `rt_consumer.py` KHÔNG đi qua cổng xu hướng —
  thẻ cảnh báo dựng từ event thô → có thể báo từ 1 điểm xấu đơn lẻ, vi phạm quy tắc
  user chốt: "không cảnh báo từ một điểm xấu; bất thường = lệch xa SMA(20) quá k*σ;
  chỉ cảnh báo khi có xu hướng (nhiều điểm bất thường liên tiếp)".
- Chưa có feedback cho thẻ cảnh báo (`answer_feedback.py` mới chỉ cho câu trả lời chat),
  chưa có số đo latency đầu-cuối.
- Mục tiêu (góp ý Khiêm, user chốt 06/10): cảnh báo realtime log LSU, phản hồi < 5 phút.

## Việc cần làm (đúng thứ tự)

1. Nối pipeline: `RtConsumer.lay_su_kien_moi()` → gom sự kiện theo chỉ số →
   `gate_canh_bao_theo_xu_huong()` (SMA(20), ngưỡng k*σ) → CHỈ xu hướng đã xác nhận
   (≥3 điểm bất thường liên tiếp hoặc ≥3/5 điểm gần nhất) mới thành thẻ cảnh báo.
   Điểm đơn lẻ → trạng thái "Cần biến", KHÔNG báo.
2. Thẻ cảnh báo hiện trong khung chat (chat-first: nằm trong vùng trả lời, không thêm
   nút bấm linh tinh).
3. Feedback tại chỗ trên thẻ cảnh báo: đúng/sai + BẮT BUỘC nhập lý do khi chê →
   JSONL `local_cases/alert_feedback.jsonl` (KHÔNG vào kho tri thức); hàm thống kê
   metric vòng lặp (tái dùng pattern `answer_feedback.py`: store + stats).
4. Đo latency đầu-cuối (event → thẻ hiện trên chat) bằng `rt_replay` với dữ liệu thật
   (`2026_08_Master.csv`, 132 dòng × 677 cột): mục tiêu < 5 phút. Đo precision:
   0 cảnh báo phát ra từ điểm bất thường đơn lẻ.
5. Test mới (tất cả PASS):
   - (a) trend ≥3 điểm bất thường liên tiếp → CÓ cảnh báo;
   - (b) 1 điểm bất thường đơn lẻ → KHÔNG cảnh báo (chỉ "Cần biến");
   - (c) feedback store ghi đúng `local_cases/alert_feedback.jsonl`, không lọt vào kho;
   - (d) replay dữ liệu thật đo latency < 5 phút.

## Rào (bắt buộc)

- Phạm vi file: `src/aios_habit/production_prediction/rt_consumer.py`, `rt_replay.py`,
  file feedback mới, hook UI chat cho thẻ cảnh báo. KHÔNG đụng file WIRE-QA của OMP,
  KHÔNG đụng index, KHÔNG merge `main`.
- KHÔNG tự ý đổi hành vi gate SMA(20) hiện có — chỉ nối vào, không viết lại.
- Code tương thích Python 3.11 (máy đích). Commit riêng trên nhánh `phieu-viec/rag-fix1`.
- Vé dài: heartbeat mốc mỗi 15 phút + checkpoint/resume trong mailbox.
- OMP đang chạy WIRE-QA trên cùng máy — chỉ commit file thuộc phạm vi vé này.

## Cổng nghiệm thu

- 4 nhóm test trên PASS (ghi rõ số lượng).
- Latency replay < 5 phút; 0 cảnh báo từ điểm đơn lẻ.
- Báo cáo `docs/phieu-viec/ket-qua/lsu-alert-realtime-pc0575.md`: số đo latency,
  precision, commit SHA, hostname, số test pass/fail.
- Xong báo `xong-cho-duyet` trong mailbox, kèm đường dẫn báo cáo.
