# Báo cáo vé RT-JIGBEAM-ADAPTER-HOME — Bộ chuyển đổi log JIG BEAM cho rt_replay

- Ngày làm: 2026-10-06 (máy nhà h410asrock)
- Người làm: thợ opencode (model free muse-spark-1.3)
- File thật: `C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\2026_08_Master.csv` — 677 cột, 132 dòng
- Rào vé: không merge `main`; Python 3.11 (thực tế 3.11.14 qua `uv run`); không đụng `trend_alerts.py` (OMP đang sửa) và UI; heartbeat `trang-thai.md`; không fake PASS.

## 1. Phương án đã chọn: (a) viết adapter riêng

- Lý do chọn (a): file JIG BEAM là log đo thật (một dòng = một lần đo một Unit: có DATE/TIME/JigNumber/SN + TotalJudge OK117/NG15 + 664 ô số/dòng), chỉ khác họ chỉ số so với Iris. Đường POST trực tiếp của vé trước (tự tách TaktTime rồi POST) chạy được nhưng mỗi lần phát lại phải viết tay đoạn tách — dễ lệch, không tái dùng lọc canh lỗi/sắp xếp/chống trùng. Adapter khép khoảng trống một lần, `rt_replay` đọc được cả 2 họ log.
- Lý do loại (b): (b) để `rt_replay` mãi từ chối 677 cột, đẩy rủi ro sang máy công ty (vé `LSU-ALERT-REALTIME-PC0575` sẽ vấp lại đúng chỗ này). Chi phí (a) nhỏ (1 module mới + 1 hàm tự động có cờ, hàm Iris cũ giữ nguyên).

## 2. Nguyên nhân gốc (số đo khảo sát)

| Kiểm tra | Kết quả |
|---|---|
| Số cột / dòng file thật | 677 cột / 132 dòng dữ liệu |
| Cột Iris nhận ra (`tach_cot_do`) | 0/677 → `la_ma_tran_rong=False` → `doc_log_iris` từ chối đúng như vé trước mô tả |
| Cột đặc trưng JIG BEAM | `TaktTime` (cột 12, 132/132 dòng có số), `XyPosX_B`, `Ld1H_...` |
| Ô số / dòng 0 | 664 ô; ô trùng sentinel 999/999.9/9999.9: 0 |
| DATE / TIME / JigNumber / S/N | `2026/08/01…06`, `6:03:59…`, `#1`, 2 mã SN (`61C1047Z3311`, `61C1047Z3321`) |
| TotalJudge | OK 117 / NG 15 |

## 3. Code đã làm (không đụng file cấm)

- Mới: `src/aios_habit/production_prediction/jigbeam_log_adapter.py` — nhận diện (`la_log_jigbeam`: >=20 cột + DATE/TIME/SN + TaktTime/XyPos), đọc (`doc_log_jigbeam`: tái dùng `la_canh_loi` + `ghep_thoi_gian` của Iris, bỏ ô trống/chữ, bỏ canh lỗi có đếm), phát lại (`phat_lai_csv_jigbeam`: mặc định chỉ TaktTime = 1 tin/dòng, sắp xếp theo giờ đo, nhãn `SIMULATED_REALTIME`), cờ `AIOS_FEATURE_JIGBEAM_ADAPTER` mặc định TẮT.
- Sửa nhẹ: `src/aios_habit/production_prediction/rt_replay.py` — chỉ thêm import + hàm `phat_lai_csv_tu_dong` (cờ TẮT: chỉ Iris như cũ, JIG BEAM báo cần bật cờ; cờ BẬT: tự chọn Iris/JIG BEAM). Hàm `phat_lai_csv_iris` cũ giữ nguyên từng dòng.
- Không đụng: `trend_alerts.py`, `tests/test_trend_alerts.py` (đang có sửa local của OMP — để nguyên), UI.

## 4. Số đo trên dữ liệu thật (chạy thật, không bịa)

| Chỉ số | Giá trị |
|---|---|
| Đọc file thật | 132 dòng / 677 cột, `thieu_cot` rỗng |
| Phát lại mặc định (TaktTime) | 132/132 bản tin, nhãn `SIMULATED_REALTIME` 132/132, mốc giờ tăng dần |
| E2E qua HTTP (`StreamListener` + `gui_lo_len_server`, kho SQLite tạm) | máy chủ xác nhận 132, kho lưu 132, mất 0 dòng |
| Gửi lại trùng (file giả 3 dòng, cùng khóa idempotent của `stream_api`) | báo trùng 3/3, kho giữ nguyên 3 (chống trùng giữ nguyên) |
| Test mới `tests/test_jigbeam_adapter.py` | 8/8 đạt (6 giả lập luôn chạy + 2 file thật) |
| Hồi quy liên quan | `test_jigbeam_adapter + test_j1_rt + test_stream_api`: 36 passed, 3 skipped (3 skip là test Linux `/home/hatch` không có trên máy Windows — có sẵn từ trước) |
| `compileall src tests` | sạch |

Chỗ chưa kiểm được: cột đơn vị vật lý của từng chỉ số BEAM (header không có `[đơn vị]` như Iris) nên `unit` để trống — ghi rõ "chưa rõ", không bịa. Muốn phát lại toàn bộ ~664 chỉ số/dòng thì truyền `chi_so` tường minh (mặc định chỉ TaktTime để nhẹ và khớp cách đo vé trước).

## 5. Cách dùng cho máy công ty (vé realtime PC0575)

```python
from aios_habit.production_prediction.jigbeam_log_adapter import phat_lai_csv_jigbeam
ban_tin = list(phat_lai_csv_jigbeam("2026_08_Master.csv"))  # 132 tin TaktTime
# hoặc tự động (cần bật cờ): AIOS_FEATURE_JIGBEAM_ADAPTER=1
from aios_habit.production_prediction.rt_replay import phat_lai_csv_tu_dong
ban_tin = list(phat_lai_csv_tu_dong("2026_08_Master.csv"))
```

## 6. Cam kết rào vé

- Không merge `main`; không sửa `trend_alerts.py`/UI; Python 3.11, không syntax 3.12+.
- Tính năng mới sau cờ (mặc định tắt): đường tự động cần `AIOS_FEATURE_JIGBEAM_ADAPTER=1`; đường tường minh là gọi hàm mới (hàm cũ không đổi hành vi).
- Số đo từ chạy thật trên file thật; kho SQLite chỉ ở thư mục tạm của test, không ghi index thật.
