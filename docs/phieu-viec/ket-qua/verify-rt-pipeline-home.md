# Báo cáo vé VERIFY-RT-PIPELINE-HOME — Kiểm chứng đường log realtime tại máy nhà

- Ngày làm: 2026-10-06 (máy nhà h410asrock)
- Người làm: thợ opencode (model free muse-spark-1.3)
- Rào vé: chỉ chạy thử + đo, không sửa code component; không merge `main`; Python 3.11 (thực tế 3.11.14 qua `uv run`); không đụng `trend_alerts.py` và UI.

## 1. Rà soát component (bước 1 của vé)

| Component | Kết quả | Chi tiết |
|---|---|---|
| `src/aios_habit/production_prediction/rt_consumer.py` | Chạy được | Import thành công; khởi tạo `RtConsumer(base_url, token, timeout)` bình thường, cursor khởi đầu 0; lấy sự kiện có thử lại kèm chờ tăng dần; cursor chỉ tiến khi xử lý xong cả lô; thẻ cảnh báo tiếng Việt tạo đủ 6 trường (`loai_the`, `ma_jig`, `thong_so`, `chi_tiet`, `muc_do`, `huong_dan`), có gắn nhãn phát lại mô phỏng |
| `src/aios_habit/production_prediction/stream_api.py` | Chạy được | Import thành công; `StreamBuffer` tạo kho SQLite + tự nâng cấp cột cũ; kiểm tra bản ghi báo lỗi tiếng Việt; phát hiện trôi (`phat_hien_drift`: nền 40 điểm so với 10 điểm mới, ngưỡng 3 sigma) chạy đúng — dữ liệu phẳng báo chưa đủ/không cảnh báo, dữ liệu lệch báo cảnh báo; quy tắc im lặng (`decide_stream_event`) đúng — chỉ trôi mới thành cảnh báo; máy nghe `StreamListener` khởi động và nhận lô bình thường |
| Đọc cấu hình | Không có tệp cứng | Cả hai nhận cấu hình qua tham số gọi hàm (`base_url`, `auth_token`/`jig_tokens`, đường dẫn kho SQLite, cổng nghe). Máy công ty cần truyền đúng các tham số này khi nối cổng SMA(20) |

## 2. Cách giả lập feed realtime (bước 2 của vé)

- Nguồn thật: `C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log\2ND-1002_JIG BEAM\2026_08_Master.csv` — 132 dòng dữ liệu, 677 cột.
- Chọn 1 chỉ số mỗi dòng: `TaktTime` (cột 12) — cả 132/132 dòng đều có số (mẫu: 145, 89, …, 138, 200 giây). Mã máy lấy từ cột `S/N`, mã đồ gá lấy từ cột `JigNumber`.
- Đường chạy thật đầu-cuối: đọc từng dòng → gửi từng bản tin JSON qua `POST /api/v1/jig/stream-log` lên `StreamListener` thật (chạy trên máy, kho SQLite tạm) → nghỉ 0,01 giây giữa các dòng theo nhịp thời gian → опроса qua `RtConsumer.chay_mot_vong`. Mỗi bản tin gắn `nguon="SIMULATED_REALTIME"` và `event_id="row-000…131"` để phân biệt phát lại và thử gửi trùng.
- Kịch bản phụ: nền ổn định 40 điểm 140 giây + đợt trôi 10 điểm 400 giây để ép sinh cảnh báo; gửi lại đợt trôi để thử chống trùng.

## 3. Số đo (bước 3 của vé)

### 3.1. Feed 132 dòng thật

| Chỉ số | Giá trị |
|---|---|
| Bản tin gửi | 132 |
| Máy chủ xác nhận ghi | 132/132 |
| Dòng lưu trong kho | 132 |
| Dòng mất | 0 |
| Trễ mỗi dòng (đo từ lúc gửi đến khi máy chủ trả lời) | nhỏ nhất ~2,2 ms; giữa (p50) ~13,7 ms; p95 ~29,7 ms; lớn nhất ~41,5 ms |
| Tổng thời gian cả đợt (gồm nghỉ nhịp 0,01 giây mỗi dòng) | ~3,1 giây |
| Sự kiện trôi sinh ra từ dữ liệu thật | 0 (đúng — dữ liệu thật ổn định, quy tắc im lặng giữ yên lặng thay vì báo giả) |
| Consumer nhận từ dữ liệu thật | 0 sự kiện (nhất quán với 0 sự kiện trong kho) |

### 3.2. Ép trôi + gửi trùng (chứng minh đường cảnh báo sống)

| Chỉ số | Giá trị |
|---|---|
| Nền 40 điểm + trôi 10 điểm lưu trong kho | 50/50, không mất |
| Sự kiện trôi sinh ra | 1 |
| Consumer nhận | 1/1; опрос lần 2 trả về rỗng (cursor đã tiến, không đọc lại) |
| Gửi lại 10 bản tin đợt trôi | máy chủ báo trùng lặp 10/10, kho giữ nguyên 50 (chống trùng khi thử lại tốt) |
| Thẻ cảnh báo từ sự kiện | đủ 6 trường, có nhãn phát lại mô phỏng |

## 4. Kết luận cho máy công ty (bước 4 của vé)

### 4.1. Component nào dùng được ngay

- `stream_api.py`: dùng được — nhận lô, lưu kho, chống trùng bằng khóa sự kiện, phát hiện trôi, quy tắc im lặng đều chạy đúng trên dữ liệu thật.
- `rt_consumer.py`: dùng được — опрос theo cursor, thử lại khi lỗi mạng, không tiến cursor khi lỗi, thẻ cảnh báo tiếng Việt đầy đủ.

### 4.2. Component nào hỏng / chưa khớp — cần vé riêng trước khi PC0575 dùng

1. `rt_replay.py` + `iris_log_adapter.doc_log_iris` **không đọc được tệp này**: máy báo tệp 677 cột không phải log Iris dạng ma trận rộng nên từ chối. Vé này không sửa code theo rào, nên đợt đo trên dùng đường gửi trực tiếp thay cho `rt_replay`. Trước khi PC0575 dùng feed JIG BEAM thật, cần một vé riêng: hoặc thêm bộ chuyển đổi cho log JIG BEAM, hoặc lấy log đúng dạng Iris.
2. Không phát hiện hỏng nào khác trong hai component được giao. Cấu hình kết nối (địa chỉ máy chủ, mã truy cập từng đồ gá, đường dẫn kho) do máy công ty cấp khi nối cổng SMA(20) — vé này chưa đụng tới vì là tham số vận hành.

### 4.3. Cam kết rào vé

- Không sửa một dòng code component nào; chỉ đọc và chạy thử qua kịch bản đặt ở thư mục tạm (`C:\Users\Admin\AppData\Local\Temp\opencode\rt_verify.py`, `rt_verify2.py`).
- Không merge `main`; không đụng `trend_alerts.py` và UI; không ghi chỉ mục thật (kho SQLite chỉ nằm ở thư mục tạm, xóa sau khi duyệt).
- Python dùng đo: 3.11.14 qua `uv run --no-sync --group dev python`.
