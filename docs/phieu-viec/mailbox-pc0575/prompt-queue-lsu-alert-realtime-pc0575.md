# Vé LSU-ALERT-REALTIME-PC0575 — Cảnh báo log LSU realtime

**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only).
**Xếp hàng:** sau `LSU-QUALITY-PC0575`.
**Role gợi ý:** PLAN trước (thiết kế đường log), rồi DEFAULT (làm).

## Bối cảnh

- Góp ý của Khiêm sau demo 02/10: ưu tiên cảnh báo từ log jig/server hơn chat mở;
  mục tiêu phản hồi trong 5 phút; tiết kiệm quota AI chung.
- Cổng cảnh báo xu hướng SMA(20) đã có sẵn trong code (`trend_alerts.py`:
  `danh_gia_xu_huong_sma` + `gate_canh_bao_theo_xu_huong`) — đã kiểm chứng 06/10.
- Vé này: nối đường log realtime của máy công ty vào cổng SMA(20) → cảnh báo.

## Việc cần làm (đúng thứ tự)

1. Khảo sát (chỉ đọc): log jig/LSU hiện vào máy công ty bằng đường nào
   (file CSV? API `stream_api.py`? consumer `rt_consumer.py`?). Ghi rõ vào báo cáo.
2. Nối consumer realtime → `danh_gia_xu_huong_sma` → `gate_canh_bao_theo_xu_huong`
   (tái dùng code có sẵn, không viết lại cổng SMA).
3. Khi có xu hướng: gửi mail kèm biểu đồ (tái dùng `alert_mailer.py`) + hiện thẻ chat
   ("Xu hướng SMA(20)" + "Phán đoán nguyên nhân" + "Đề xuất điều tra").
4. Đo độ trễ đầu-cuối (từ lúc log sinh ra đến lúc cảnh báo tới tay) — mục tiêu <5 phút.
5. Báo cáo `docs/phieu-viec/ket-qua/lsu-alert-realtime-pc0575.md`:
   sơ đồ đường log, độ trễ đo được, 3 tình huống test (bình thường / 1 điểm xấu / xu hướng xấu).

## Rào cứng

- 1 điểm xấu đơn lẻ KHÔNG được gửi cảnh báo (luật SMA(20) đã chốt).
- Không merge `main`. Python 3.11. Mọi ngưỡng cấu hình qua `thresholds.yaml`, không hardcode.
- Nếu hạ tầng server phía công ty chưa sẵn sàng (log chưa đẩy lên được) → báo rõ điểm nghẽn,
  làm phần demo với file log mẫu, không bịa kết quả realtime.
