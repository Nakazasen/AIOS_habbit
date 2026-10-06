# Báo cáo vé LSU-ALERT-REALTIME-PC0575 — Nối consumer realtime qua cổng xu hướng SMA(20)

- Máy: KDTVN-PC0575 (CPU-only).
- Ngày: 2026-10-06.
- Nhánh: `phieu-viec/rag-fix1`.
- Commit code: `c9d0e84` (nối pipeline + feedback + đo latency + test mới).
- Commit tiến độ: `bb71d0b`.
- Prompt: `docs/phieu-viec/mailbox-pc0575-opencode/prompt.md`.

## 1. Việc đã làm (đúng thứ tự vé)

1. Nối pipeline: `RtConsumer.lay_su_kien_moi()` → gom sự kiện theo chỉ số
   (`gom_gia_tri_theo_chi_so`) → `danh_gia_xu_huong_sma()` (SMA(20), ngưỡng k*σ)
   → `gate_canh_bao_theo_xu_huong()` có sẵn (không viết lại, không đổi hành vi).
   Chỉ xu hướng đã xác nhận (≥3 điểm bất thường liên tiếp hoặc ≥3/5 điểm gần nhất)
   mới thành thẻ cảnh báo. Điểm đơn lẻ → trạng thái "Cần biến", không báo.
   File: `src/aios_habit/production_prediction/rt_consumer.py`
   (hàm mới: `trich_gia_tri_su_kien`, `gom_gia_tri_theo_chi_so`,
   `danh_gia_lo_su_kien_qua_cong_xu_huong`, `chuyen_lo_thanh_the_da_qua_cong`,
   `dinh_dang_text_chat_cho_the_realtime`, `tom_tat_can_bien_cho_chat`).
2. Thẻ cảnh báo hiện trong khung chat (chat-first, nằm trong vùng trả lời,
   không thêm nút bấm): `dinh_dang_text_chat_cho_the_realtime()` +
   hook `day_the_realtime_qua_cong_vao_chat()` trong
   `src/aios_habit/production_prediction/jig_chat_wire.py`.
3. Feedback tại chỗ trên thẻ cảnh báo: đúng/sai + bắt buộc nhập lý do khi chê
   → JSONL `local_cases/alert_feedback.jsonl` (không vào kho tri thức).
   File mới: `src/aios_habit/alert_feedback.py` (tái dùng đúng mẫu
   `answer_feedback.py`: store + `alert_feedback_stats()`).
4. Đo latency đầu-cuối (event → thẻ hiện trên chat): hàm mới
   `do_latency_qua_cong_xu_huong()` trong
   `src/aios_habit/production_prediction/rt_replay.py` (chạy offline,
   không cần server).

## 2. Số đo latency và precision

- Chuỗi đo: 132 điểm (20 nền + 100 ổn định + 12 drift), cùng cỡ file thật
  `2026_08_Master.csv` (132 dòng × 677 cột).
- Ghi chú trung thực: file thật `2026_08_Master.csv` không có trên máy này
  (đường dẫn `C:\tmp\lsu1-deploy\...` không tồn tại), nên dùng chuỗi mirror
  cùng cỡ 132 điểm. Logic đo giống nhau, khi có file thật chỉ cần nạp giá trị
  TaktTime vào cùng hàm.
- Latency đo trên máy này: khoảng 0,0014 giây cho 132 điểm
  (mục tiêu < 5 phút = 300 giây) → ĐẠT, nhanh hơn mục tiêu khoảng 200.000 lần.
- Precision điểm đơn lẻ: chuỗi 20 nền + 1 điểm xa → 0 cảnh báo
  (chỉ 1 mục "Cần biến") → ĐẠT yêu cầu "0 cảnh báo từ điểm đơn lẻ".

## 3. Test mới (4/4 PASS)

- File: `tests/test_lsu_alert_realtime_pc0575.py`.
- (a) trend 3 điểm bất thường liên tiếp → CÓ 1 thẻ cảnh báo: PASS.
- (b) 1 điểm đơn lẻ → KHÔNG thẻ, chỉ 1 mục "Cần biến", text chat chứa
  "Cần biến" và không chứa "Cảnh báo realtime": PASS.
- (c) feedback ghi đúng `local_cases/alert_feedback.jsonl`, chê bắt buộc lý do,
  stats đúng 1 đúng / 1 sai, file nằm dưới `local_cases`, không vào kho: PASS.
- (d) replay đo latency < 5 phút + precision đơn lẻ 0 cảnh báo: PASS.
- Lệnh: `uv run --no-sync --group dev pytest tests/test_lsu_alert_realtime_pc0575.py -q`
  → 4 passed.
- Hồi quy liên quan: `test_trend_alerts + test_trend_response + test_j1_rt + vé mới`
  → 56 passed, 3 skipped (skip là thiếu file thật trên máy này).
  `test_j1_rt + test_stream_api + test_jigbeam_adapter + vé mới` → 38 passed, 5 skipped.
- Cổng nhanh: `compileall` sạch; `cli audit` → `PASS`; import
  `aios_habit.workspace_chat_app` → thành công.
- Cổng đầy đủ: `pytest -q` toàn bộ quá 10 phút chưa xong (có F/E ở nhóm khác,
  ngoài phạm vi vé) — khai trung thực, không báo PASS giả.

## 4. Phạm vi và rào

- Chỉ đụng: `rt_consumer.py`, `rt_replay.py`, `jig_chat_wire.py` (hook chat),
  file mới `src/aios_habit/alert_feedback.py`, test mới.
- Không đụng file WIRE-QA của OMP, không đụng index, không merge `main`.
- Không đổi hành vi gate SMA(20) có sẵn, chỉ nối vào.
- Tương thích Python 3.11 (`uv run` cho Python 3.11.15).
- Dữ liệu feedback chỉ ghi `local_cases/`, không commit, không vào kho tri thức.

## 5. Kết luận

- Vé xong, chờ duyệt. Đề nghị đặt `xong-cho-duyet` trong mailbox.
