# Vé RT-JIGBEAM-ADAPTER-HOME — Khép khoảng trống rt_replay với log JIG BEAM

**Máy thực hiện:** NHÀ h410asrock (thợ opencode).
**Role gợi ý:** DEFAULT (code + test).

## Bối cảnh

Vé `VERIFY-RT-PIPELINE-HOME` (vừa ĐẠT) kiểm chứng `stream_api.py` + `rt_consumer.py`
chạy tốt trên 132 dòng thật (132/132, mất 0 dòng, trễ p50 ~13,7 ms), nhưng phát hiện
1 khoảng trống: `rt_replay.py` + `iris_log_adapter.doc_log_iris` TỪ CHỐI file
`2026_08_Master.csv` (677 cột, log JIG BEAM) vì "không phải log Iris dạng ma trận rộng".
Trước khi máy công ty dùng feed realtime (vé `LSU-ALERT-REALTIME-PC0575`), cần khép
khoảng trống này — không để sang máy công ty mới phát hiện.

## Việc cần làm

1. Chọn 1 trong 2 phương án, ghi rõ lý do trong báo cáo:
   (a) Viết bộ chuyển đổi log JIG BEAM (677 cột) → dòng log chuẩn mà `stream_api` /
       `rt_replay` chấp nhận; hoặc
   (b) Chứng minh log JIG BEAM không cần qua `rt_replay` (đường POST trực tiếp đã
       đủ cho vé realtime) + tài liệu hóa quyết định.
2. Nếu chọn (a): code adapter + test trên file `2026_08_Master.csv` thật —
   132/132 dòng qua được, không mất dòng, chống trùng giữ nguyên; test mới xanh,
   hồi quy liên quan (`test_j1_rt.py`, `test_stream_api.py`) không đỏ thêm.
3. Báo cáo `docs/phieu-viec/ket-qua/rt-jigbeam-adapter-home.md`: phương án đã chọn
   + lý do + số đo trên dữ liệu thật.

## Rào cứng

- Không merge `main`. Python 3.11 (không dùng syntax 3.12+).
- 1 file 1 đứa: KHÔNG đụng `trend_alerts.py` (OMP đang sửa ở vé `SMA-IMPROVE-HOME`),
  không đụng UI (agy đã xong).
- Heartbeat: mốc tiến độ tối thiểu 15 phút/lần trong `trang-thai.md`.
- Không fake PASS: số đo phải từ chạy thật trên file thật; chỗ nào chưa kiểm được
  thì ghi "chưa rõ".
