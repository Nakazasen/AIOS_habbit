# Vé RT-ALERT-E2E-HOME — Đo đầu-cuối cảnh báo realtime (baseline cho vé PC0575)

**Máy thực hiện:** NHÀ h410asrock (thợ opencode).
**Role gợi ý:** DEFAULT (đo + báo cáo, không sửa logic).

## Bối cảnh

Vé `RT-JIGBEAM-ADAPTER-HOME` (vừa ĐẠT) đã khép khoảng trống `rt_replay` với log JIG BEAM:
adapter đọc 132/132 dòng file thật `2026_08_Master.csv` (677 cột), phát lại qua HTTP
không mất dòng, chống trùng giữ nguyên. Vé `LSU-ALERT-REALTIME-PC0575` ở máy công ty
cần con số baseline đo trên máy nhà: từ lúc 1 dòng log vào đến khi cảnh báo xuất hiện
mất bao lâu (mục tiêu <5 phút theo góp ý Khiêm).

## CỔNG GATE (bắt buộc)

Chỉ bắt đầu SAU KHI mailbox (OMP) có verdict Muse **ĐẠT** `SMA-IMPROVE-HOME` — cổng phát
hiện (`trend_alerts.py`) đang được OMP sửa (deadband + k theo nhóm chỉ số). Đo trên cổng
MỚI để baseline đúng với bản máy công ty sẽ dùng. Cổng chưa mở thì đặt `Trạng thái:
`dang-lam` + CHỜ, KHÔNG THOÁT (kiểm lại cổng gate mỗi ~10 phút, ghi heartbeat;
cổng mở thì làm tiếp ngay).

## Việc cần làm

1. Phát lại file JIG BEAM thật `2026_08_Master.csv` qua `phat_lai_csv_tu_dong`
   (bật cờ `AIOS_FEATURE_JIGBEAM_ADAPTER=1`) + `stream_api` chạy local.
2. Ép drift vào feed TaktTime (phương pháp vé VERIFY-RT-PIPELINE-HOME: 40+10 điểm),
   đo thời gian từ khi dòng drift đầu tiên vào đến khi cảnh báo được ghi/nhận qua cổng
   phát hiện hiện có trên nhánh — CHỈ GỌI, KHÔNG SỬA `trend_alerts.py`,
   `tests/test_trend_alerts.py`, `tests/test_j1_csv.py`, UI. Ghi rõ commit của cổng đã đo.
3. Báo cáo `docs/phieu-viec/ket-qua/rt-alert-e2e-home.md`: sơ đồ đường đi
   log → phát lại → phát hiện → cảnh báo; số đo (độ trễ từ dòng drift đến cảnh báo,
   mất dòng, cảnh báo đúng/thiếu/thừa); đạt hay chưa đạt mục tiêu <5 phút; điểm nghẽn
   (nếu có) + khuyến nghị cụ thể cho vé `LSU-ALERT-REALTIME-PC0575`.

## Rào cứng

- Không merge `main`. Python 3.11 (không dùng syntax 3.12+).
- 1 file 1 đứa: KHÔNG đụng `trend_alerts.py` (OMP), `tests/test_j1_csv.py` (agy sẽ sửa
  sau verdict OMP), không đụng UI.
- Chỉ đọc file log thật; SQLite chỉ trong thư mục tạm của test; không ghi index thật.
- Heartbeat: mốc tiến độ tối thiểu 15 phút/lần trong `trang-thai.md`.
- Không fake PASS: số đo phải từ chạy thật trên máy nhà; chỗ nào chưa kiểm được thì
  ghi "chưa rõ".
