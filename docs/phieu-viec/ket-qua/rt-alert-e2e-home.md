# Báo cáo vé RT-ALERT-E2E-HOME — Đo đầu-cuối cảnh báo realtime tại máy nhà

- Ngày làm: 2026-10-06 (máy nhà h410asrock)
- Người làm: thợ opencode (model free muse-spark-1.3)
- Cổng đã đo: `src/aios_habit/production_prediction/trend_alerts.py` tại commit `3c7f2f3`
  (vé SMA-IMPROVE-HOME: deadband `nen_phang_nhung_lech` nhiệt 0.5 / ẩm 2.0 / Takt 10.0
  + k theo nhóm `chu_ky` 2.5 / còn lại 3.0). HEAD nhánh lúc đo: `0662cd2`.
- File thật: `C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\2026_08_Master.csv`
  — 677 cột, 132 dòng dữ liệu.
- Rào vé: không merge `main`; Python 3.11 (thực tế 3.11.14 qua `uv run`); CHỈ GỌI,
  KHÔNG SỬA `trend_alerts.py`, `tests/test_trend_alerts.py`, `tests/test_j1_csv.py`, UI;
  SQLite chỉ trong thư mục tạm; không ghi index thật.

## 1. Sơ đồ đường đi log → phát lại → phát hiện → cảnh báo

```text
2026_08_Master.csv (132 dòng, 677 cột)
  │  phat_lai_csv_tu_dong (cờ AIOS_FEATURE_JIGBEAM_ADAPTER=1)
  │  → adapter tự nhận JIG BEAM → 132 bản tin TaktTime, nhãn SIMULATED_REALTIME
  ▼
POST /api/v1/jig/stream-log → StreamListener local (kho SQLite tạm)
  │  lưu kho + chống trùng + phát hiện drift nền (40 điểm so 10 điểm mới)
  ▼
RtConsumer / chuyen_lo_thanh_the_da_qua_cong (gom theo JIG + chỉ số)
  │  → danh_gia_xu_huong_sma window=20, nhóm chu_ky (k=2.5), deadband Takt 10.0
  ▼
Thẻ cảnh báo realtime trong chat (đủ 6 trường tiếng Việt)
  / hoặc mục "Cần biến" khi chỉ có điểm xấu đơn lẻ (quy tắc im lặng)
```

## 2. Cách ép drift (theo vé VERIFY-RT-PIPELINE-HOME)

- Nền ổn định: 40 điểm TaktTime 140 giây.
- Đợt trôi: 10 điểm TaktTime 400 giây (≈ +186% so với nền, vượt xa deadband 10.0 giây).
- Chạy từng điểm qua cổng SMA mới (`danh_gia_xu_huong_sma`, `nhom_chi_so="chu_ky"`),
  ghi nhận mẫu đầu tiên bật `canh_bao=True`.
- Đối chứng báo giả: chạy nguyên 132 giá trị TaktTime thật (87–297 giây) qua cùng cổng.

## 3. Số đo (chạy thật, không bịa)

### 3.1. Phát lại + HTTP đầu-cuối (file thật)

| Chỉ số | Giá trị |
|---|---|
| Bản tin từ `phat_lai_csv_tu_dong` (cờ bật) | 132/132, toàn bộ `metric=TAKTTIME`, nhãn `SIMULATED_REALTIME` 132/132, mốc giờ tăng dần, đọc hết trong 0,84 giây |
| Máy chủ xác nhận / dòng lưu trong kho | 132 / 132 |
| Dòng mất | 0 |
| Trễ mỗi dòng (gửi → máy chủ trả lời) | nhỏ nhất ~1,9 ms; p50 ~6,0 ms; p95 ~27,7 ms; lớn nhất ~42,9 ms |
| Gửi trùng 3 tin đầu | máy chủ báo trùng 3/3, kho giữ nguyên 132 (chống trùng giữ nguyên) |

### 3.2. Độ trễ từ dòng drift đầu đến cảnh báo (cổng SMA mới)

| Chỉ số | Giá trị |
|---|---|
| Mẫu drift đầu tiên | mẫu thứ 41 của chuỗi (sau 40 nền) |
| Mẫu bật cảnh báo đầu tiên | mẫu thứ 43 = **mẫu drift thứ 3**, `trang_thai=Vi phạm` |
| Số mẫu trễ phát hiện | 3 mẫu |
| Tổng thời gian xử lý 50 mẫu qua cổng | 0,0031 giây; mỗi mẫu p50 ~0,053 ms |
| Qua cổng chat (`chuyen_lo_thanh_the_da_qua_cong`, chuỗi 40+10) | 1 thẻ cảnh báo, 0 cận biên; latency 0,0002 giây |
| **Đạt mục tiêu <5 phút** | **ĐẠT** (0,0031 giây << 300 giây, dư địa ~5 bậc độ lớn) |

### 3.3. Cảnh báo đúng / thiếu / thừa

| Kịch bản | Thẻ cảnh báo | Mục cận biên | Nhận xét |
|---|---|---|---|
| 132 dòng thật (không ép drift) | 0 | 1 | đúng — dữ liệu thật ổn định, quy tắc im lặng không báo giả |
| 132 thật + 10 drift 400 giây | 1 | 0 | đúng — bắt được drift, không thiếu |
| 40 nền + 10 drift (chuẩn VERIFY) | 1 | 0 | đúng — không thừa (chỉ 1 thẻ cho 1 đợt trôi) |

Kết luận: đúng 2/2 kịch bản có drift (không thiếu), thừa 0 (không báo giả trên dữ liệu thật).

## 4. Đạt hay chưa đạt mục tiêu <5 phút

**ĐẠT.** Từ dòng drift đầu tiên vào đến khi thẻ cảnh báo xuất hiện qua cổng SMA mới
chỉ tốn ~mili-giây xử lý (báo ở mẫu drift thứ 3, tổng <0,01 giây cho cả chuỗi 50 mẫu
kể cả HTTP từng dòng p95 ~28 ms). Với nhịp feed thực tế (1 mẫu/giây trở lên),
độ trễ đầu-cuối vẫn ở mức giây — dưới mục tiêu 5 phút rất xa.

Lưu ý trung thực: con số trên là latency xử lý trên máy nhà (CPU local, feed mô phỏng
gửi liên tiếp, không nghỉ nhịp thời gian thực). Nếu feed thật thưa (ví dụ 1 mẫu/giờ),
thời gian "đủ 3 mẫu drift để kết luận xu hướng" sẽ do nhịp feed quyết định, không phải
do cổng xử lý — máy công ty cần cộng thêm `(3 × nhịp feed)` vào baseline này.

## 5. Điểm nghẽn (nếu có) + khuyến nghị cho vé LSU-ALERT-REALTIME-PC0575

1. **Không có nghẽn xử lý.** p95 HTTP ~28 ms, SMA ~0,05 ms/mẫu — cổng nhẹ, chạy realtime tốt.
2. **Ngưỡng phát hiện drift TaktTime hợp lý:** drift +186% báo ở mẫu thứ 3; deadband
   10.0 giây không nuốt drift lớn, dữ liệu thật 87–297 giây không báo giả. PC0575 giữ
   nguyên `k=2.5` + deadband Takt 10.0 của commit `3c7f2f3`, không cần chỉnh thêm
   trước khi đo trên máy công ty.
3. **Nhịp feed quyết định độ trễ thực tế:** cổng cần 3 mẫu bất thường để kết luận xu hướng
   (đúng thiết kế chống báo giả 1 điểm). PC0575 nên ghi rõ nhịp feed (mẫu/phút) để quy
   "3 mẫu" ra phút — với feed 1 mẫu/phút thì trễ phát hiện ≈ 3 phút, vẫn đạt <5 phút;
   với feed thưa hơn cần nới lỏng `diem_lien_tiep` hoặc chấp nhận trễ lớn hơn.
4. **Đơn vị `unit` của BEAM để trống** (header JIG BEAM không có đơn vị như Iris —
   đã ghi "chưa rõ" ở vé adapter). Thẻ cảnh báo TaktTime vẫn đủ nghĩa (giây, theo cột
   gốc), PC0575 không bị chặn.

## 6. Cam kết rào vé

- CHỈ GỌI, KHÔNG SỬA: vé này không sửa bất kỳ file `src/` hay `tests/` nào.
  Ghi trung thực: lúc chốt báo cáo, cây local có sửa chưa commit ở
  `tests/test_j1_csv.py` (+23/-2) thuộc vé song song của agy
  (`FIX-J1CSV-FIXTURE-HOME`, đã nhận việc ở commit `8044af0`) — không phải của vé này,
  không commit ké.
- Không merge `main`; Python 3.11.14 qua `uv run`; SQLite chỉ trong thư mục tạm
  (`rt_alert_e2e_*`, tự dọn sau duyệt); không ghi index thật; không secret.
- Script đo đặt ở thư mục tạm ngoài repo
  (`C:\Users\Admin\AppData\Local\Temp\opencode\rt_alert_e2e.py` + `ket_qua.json`
  trong thư mục tạm của lần chạy), không commit script.
- Số đo từ chạy thật trên máy nhà; chỗ nhịp feed thực tế đã ghi rõ cách cộng thêm ở §4.

## 7. Cổng kiểm tra repo (chạy thật 2026-10-06 ~23:50 +07)

- `uv run --no-sync --group dev python -m compileall src tests`: sạch.
- `pytest tests/test_jigbeam_adapter.py tests/test_j1_rt.py tests/test_stream_api.py tests/test_trend_alerts.py -q`:
  **58 passed, 3 skipped** trong 13,78 giây (3 skip là test Linux đường `/home/hatch`
  không có trên máy Windows — có sẵn từ trước, khớp vé adapter cũ).
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: `{"status": "PASS"}`.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: OK.
- Vé này không sửa `src/`/`tests/` (xác nhận ở §6).
