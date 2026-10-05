# Vé SMA-WARMUP-LABEL-HOME — Nhãn "đang tích lũy dữ liệu nền" khi chuỗi < 20 điểm

**Máy thực hiện:** NHÀ h410asrock (thợ agy).
**Role gợi ý:** DEFAULT (UI + test).
**Nguồn yêu cầu:** `docs/phieu-viec/ket-qua/sma-gate-realdata-home.md` §5.2 mục 3
(đề xuất "cơ chế khởi động mềm / Warmup window").

## Bối cảnh

Cổng SMA(20) cần 20 điểm nền mới kết luận xu hướng. Với lô đo ngắn (<20 điểm),
người vận hành không hiểu vì sao chưa có cảnh báo xu hướng.
Vé này thêm nhãn giải thích rõ ràng trên giao diện.

## Việc cần làm

1. Khi chuỗi dữ liệu có N < 20 điểm: thẻ kiểm tra (instant card trong
   `jig_chat_wire.py` / `jig_alert_cards.py`) hiện thêm dòng:
   `"Đang tích lũy dữ liệu nền (N/20 điểm) — chưa đủ cơ sở kết luận xu hướng."`
2. Khi N >= 20: không hiện dòng này (giữ giao diện gọn).
3. Test: N=5 → có nhãn đúng số; N=20 → không nhãn; N=0 → nhãn "0/20".
   Chạy lại test card cũ phải xanh.
4. Báo cáo `docs/phieu-viec/ket-qua/sma-warmup-label-home.md` + ảnh chụp thẻ mẫu
   (nếu chạy được UI) hoặc text render mẫu.

## Rào cứng

- 1 file 1 đứa: chỉ sửa file UI/card. Không đụng `trend_alerts.py`
  (vé `SMA-IMPROVE-HOME` của OMP đang sửa file đó song song).
- Chuỗi nhãn qua i18n nếu file UI đang dùng `t()`. Python 3.11. Không merge `main`.
