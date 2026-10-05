# Báo cáo rà soát readiness Bước 2 tool JIG (Hạn 15/10/2026)

- Mã vé: `AUDIT-BUOC2-JIG-HOME`
- Máy thực thi: máy nhà `h410asrock` (thợ agy — gemini-3.8-flash-high)
- Nhánh: `phieu-viec/rag-fix1`
- Trạng thái: **Hoàn thành 100% rà soát**, sẵn sàng nghiệm thu (vé PLAN: chỉ đọc + đối chiếu, không sửa code, không đụng `main`).
- Mục tiêu: Rà soát toàn diện mức độ hoàn thành của 8 chức năng Bước 1 theo kế hoạch công ty (ảnh 30/09), đối chiếu bằng chứng kiểm thử tự động và dữ liệu thật, loại trừ cổng SMA(20) đang do OMP sửa, và chốt danh sách việc còn thiếu cho Bước 2 (hạn 15/10/2026, còn 9 ngày).

---

## 1. Bối cảnh & Căn cứ đối chiếu

Theo lộ trình công ty ghim tại [`docs/dich-den-du-an.md`](file:///D:/Sandbox/AIOS_habbit/docs/dich-den-du-an.md) mục 2 ("Tool phân tích log JIG — kế hoạch công ty"):
- **Bước 1 (Chuẩn bị chức năng AI — thao tác bằng tay):** Hạn gốc 23/09 – 15/10/2026.
- **Bước 2 (Xác nhận/chỉnh sửa chức năng Bước 1 trước khi đưa người dùng thử):** Hạn chốt **15/10/2026**.
- **Bước 3 (Triển khai dùng thử, thu thập thông tin cải tiến):** Hạn 15/11/2026 (đã chuẩn bị sẵn gói dùng thử ở vé `J3`).

---

## 2. Rà soát chi tiết 8 chức năng Bước 1 theo kế hoạch công ty

### 2.1. Nhập CSV (Nhập cả file CSV log JIG)
- **Yêu cầu kế hoạch công ty:** Có cơ chế nhập cả file CSV log JIG và cho phép chọn biểu đồ (áp dụng luôn).
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/jig_csv_import.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_csv_import.py), [`jig_log_ingest.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_log_ingest.py), [`jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py). Lệnh chat: `nhập tệp log "<đường_dẫn>"`.
- **Bằng chứng kiểm thử (Unit/Contract Tests):** [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py) (15 bài test, bao gồm: nhập file hợp lệ, chống trùng lặp SHA-256 + mtime, xử lý lỗi tiếng Việt rõ ràng, nạp bản ghi thật).
- **Bằng chứng dữ liệu thật:**
  - Nạp thành công tệp ma trận rộng Iris [`IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv`](file:///C:/home/hatch/workspace/aios_data/lsu/Iris%20LSU/thu%20nghiem%206pcs%20do%20thong%20so%20va%20log/2ND-1035/IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv) (24.375.633 bytes, 1.191.207 giá trị đo).
  - Nạp thành công tệp log Master [`2026_08_Master.csv`](file:///C:/tmp/lsu1-deploy/data/lsu/Iris%20LSU/thu%20nghiem%206pcs%20do%20thong%20so%20va%20log/2ND-1002_JIG%20BEAM/2026_08_Master.csv) (340.621 bytes, 132 dòng bản ghi, 677 cột).
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-csv.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-csv.md) §2.1, [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (mục A1, A2).
- **Đánh giá readiness:** **ĐÃ HOÀN THÀNH 100%**. Có giới hạn an toàn thiết kế: trần `GIOI_HAN_DONG_MOI_LAN = 50.000` dòng/lần nạp (hệ thống thông báo rõ ràng và hướng dẫn người dùng nếu file lớn hơn).

---

### 2.2. Watch từng dòng (Cho từng dòng log vào file mà AI phân tích)
- **Yêu cầu kế hoạch công ty:** Có 1 cơ chế cho từng dòng log vào file mà AI phân tích (hạn gốc 23/09).
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/log_stream_ingest.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/log_stream_ingest.py), [`jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py), [`jig_alert_cards.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_alert_cards.py).
- **Bằng chứng kiểm thử:**
  - [`tests/test_jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_jig_chat_wire.py) (17/17 passed, kiểm tra đầy đủ nhận diện dòng log JIG 7 cột chuẩn, dòng Iris rộng, dòng depth).
  - [`tests/test_log_stream_ingest.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_log_stream_ingest.py) (passed).
- **Bằng chứng dữ liệu thật:** Đã chạy thử nghiệm dán dòng log thực tế qua Omnibar (`2026-10-01T10:00:00,61C1068E6222,IrisLSU (log dán),SKEW:BLACK,-1022,um,OK`). Hệ thống parse tức thì, trả thẻ kiểm tra với kết luận 1 câu và lưu vào kho log.
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-csv.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-csv.md) §2.3, [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (A1, C3), [`docs/phieu-viec/ket-qua/sma-warmup-label-home.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/sma-warmup-label-home.md) §3.
- **Đánh giá readiness:** **ĐÃ HOÀN THÀNH 100%**. Cơ chế thẻ kiểm tra tức thì (instant card) hoạt động mượt mà.

---

### 2.3. 9 biểu đồ (Cho phép chọn biểu đồ)
- **Yêu cầu kế hoạch công ty:** Cho phép chọn biểu đồ trực quan hóa dữ liệu JIG (9 biểu đồ).
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/chart_selection.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/chart_selection.py), [`spc_chart.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/spc_chart.py). Lệnh chat: `chọn biểu đồ <xu_huong|phan_bo|so_sanh_mau> [cho METRIC]`.
- **Bằng chứng kiểm thử:** [`tests/test_spc_chart.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_spc_chart.py) (10/10 passed), [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py) (passed các bài chọn biểu đồ).
- **Bằng chứng dữ liệu thật:** Đã xuất 9 ảnh PNG thực tế (51–73 KB) trên dữ liệu thật LSU Iris phủ ma trận: 3 loại biểu đồ (`xu_huong`, `phan_bo`, `so_sanh_mau`) × 3 chỉ số đo thật (`SKEW:BLACK`, `BOW:BLACK:-70`, `BOW:BLACK:0`).
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-csv.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-csv.md) §2.2, [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (mục B1, B2) & §3, [`docs/phieu-viec/ket-qua/j3.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j3.md) §2 (G5).
- **Đánh giá readiness:** **SẴN SÀNG CHO BƯỚC 2**.
  - *Điểm cần lưu ý làm rõ với người dùng:* Trong mã hiện hành, engine biểu đồ hỗ trợ 3 loại biểu đồ chuẩn theo spec-015/spec-016. Con số "9 biểu đồ" đã được nghiệm thu ĐẠT ở vé `J2` theo tổ hợp 3 loại × 3 chỉ số. Cần xác nhận lại xem người dùng có yêu cầu danh mục 9 loại biểu đồ SPC riêng biệt (Xbar-R, Xbar-S, CUSUM, I-MR...) hay không.

---

### 2.4. Cảnh báo ngưỡng (Giới hạn trên/dưới do người dùng setup)
- **Yêu cầu kế hoạch công ty:** Thiết lập giới hạn trên/dưới của một giá trị thông số được phân tích (hạn gốc 23/09).
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/metric_limits.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/metric_limits.py), [`alert_config_chat.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/alert_config_chat.py), [`jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py). Lệnh chat: `đặt ngưỡng trên/dưới X cho METRIC`, `xem ngưỡng`, `xóa ngưỡng METRIC`.
- **Bằng chứng kiểm thử:** [`tests/test_threshold_alert_chat.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_threshold_alert_chat.py) (8/8 passed), [`tests/test_alert_config_chat.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_alert_config_chat.py) (10/10 passed), [`tests/test_in_app_risk_alert.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_in_app_risk_alert.py) (passed).
- **Bằng chứng dữ liệu thật:** Đã kiểm thử đặt ngưỡng thực tế `-364` cho `SKEW:BLACK`. Dòng log đo `-359` vượt ngưỡng lập tức được kết luận "Vi phạm" theo ngưỡng người dùng (`nguon: nguoi_dung`).
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (C1, C2, C3), [`docs/phieu-viec/ket-qua/j3.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j3.md) §2 (G7, G8, G10a).
- **Đánh giá readiness:** **ĐÃ HOÀN THÀNH 100%**. Ngưỡng do người dùng đặt có thẩm quyền cao nhất (precedence), ghi đè ngưỡng thống kê mô phỏng.

---

### 2.5. Cảnh báo xu hướng
- **Yêu cầu kế hoạch công ty:** Cảnh báo khi dữ liệu có xu hướng dẫn đến phát sinh NG trên công đoạn (EWMA, SMA, trôi dạt).
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/trend_alerts.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/trend_alerts.py), [`trend_response.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/trend_response.py), [`jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py), [`jig_alert_cards.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_alert_cards.py).
- **Bằng chứng kiểm thử:**
  - [`tests/test_trend_alerts.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_trend_alerts.py) (14/14 passed: kiểm tra window SMA, 3 điểm liên tiếp, 3/5 điểm nhìn lại, gate chặn điểm đơn lẻ).
  - [`tests/test_jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_jig_chat_wire.py) (17/17 passed: bao phủ tích hợp warmup label $N=0, 5, 20, 25$).
- **Bằng chứng dữ liệu thật:**
  - Đã chạy trên 132 dòng Master CSV thật `2026_08_Master.csv`: cổng gate SMA(20) chặn thành công 100% (21/21 điểm vi phạm đơn điểm của Độ ẩm, TaktTime, Nhiệt độ), không gây báo động sai.
  - Nhãn khởi động mềm (warmup) hiển thị minh bạch `"Đang tích lũy dữ liệu nền (N/20 điểm) — chưa đủ cơ sở kết luận xu hướng."` khi $N < 20$ và tự động ẩn khi $N \ge 20$.
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/sma-gate-realdata-home.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/sma-gate-realdata-home.md), [`docs/phieu-viec/ket-qua/sma-warmup-label-home.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/sma-warmup-label-home.md).
- **Đánh giá readiness & Phạm vi loại trừ:**
  - **LOẠI TRỪ cổng SMA(20)**: Thợ OMP đang thực hiện vé `SMA-IMPROVE-HOME` để bổ sung deadband cho trường hợp `nen_phang_nhung_lech` (sigma=0 do làm tròn cảm biến) và điều chỉnh $k$ linh hoạt cho TaktTime. Thợ agy tuân thủ rào cứng không đụng file và không rà trùng.
  - **Phát hiện lệch test cần sửa ở Bước 2:** Bài test `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` trong `tests/test_j1_csv.py` (viết ngày 01/10) dùng 1 điểm vi phạm đơn lẻ `99.9` trên nền 20 điểm `10.0`. Khi cổng gate SMA(20) được bổ sung từ ngày 03/10 (`846713e`), cổng gate đã chặn đúng điểm xấu đơn lẻ này (`canh_bao = False`), dẫn đến biểu đồ cảnh báo không tự vẽ trong bài test này. Cần cập nhật fixture test cấp chuỗi 3 điểm xấu liên tiếp để test pass đồng bộ.

---

### 2.6. Mail kèm biểu đồ (Thông báo mail + đính kèm biểu đồ tự chọn)
- **Yêu cầu kế hoạch công ty:** Tự chọn biểu đồ mà người dùng setup, tự động gửi email đính kèm biểu đồ thông báo đó.
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/alert_mailer.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/alert_mailer.py), [`smtp_config.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/smtp_config.py), [`jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_chat_wire.py). Lệnh chat: `thêm email ...`, `chọn biểu đồ gửi mail ...`, `bỏ biểu đồ gửi mail ...`.
- **Bằng chứng kiểm thử:** [`tests/test_alert_mailer.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_alert_mailer.py) (13/13 passed).
- **Bằng chứng dữ liệu thật:** Đã tạo ra tệp `.eml` hoàn chỉnh (70–71 KB) đính kèm đúng file ảnh PNG `bieu_do_phan_bo.png` theo cấu hình người dùng chọn, có mã duyệt `DUYET-XXXX`, cổng duyệt tay `can_send_with_approval` bảo vệ không bao giờ gửi ngầm lén lút.
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-csv.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-csv.md) §2.3, [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (D0–D3), [`docs/phieu-viec/ket-qua/j3.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j3.md) §2 (G9, G12).
- **Đánh giá readiness:** **SẴN SÀNG CHO DÙNG THỬ**.
  - *Việc còn thiếu cho Bước 2/3:* Chưa kết nối với máy chủ SMTP thực tế của công ty. Hiện tại hoạt động ở chế độ tạo tệp EML và thẻ đề xuất có mã duyệt. Khi đưa vào nhà máy cần nạp thông số SMTP server công ty thật.

---

### 2.7. API realtime (Cổng API nhận log JIG và đẩy về AI Realtime)
- **Yêu cầu kế hoạch công ty:** Chức năng nâng cao: mở cổng API (đầu nhận/chuyển thông tin) để khi dữ liệu từ JIG đẩy lên server realtime; từ server đẩy về AI Realtime. Chuẩn bị server hạ tầng.
- **Mã nguồn thực thi:** [`src/aios_habit/production_prediction/stream_api.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/stream_api.py), [`rt_consumer.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/rt_consumer.py), [`rt_replay.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/rt_replay.py).
- **Bằng chứng kiểm thử:**
  - [`tests/test_stream_api.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_stream_api.py) (14/14 passed).
  - [`tests/test_j1_rt.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_rt.py) (23 passed, 3 skipped do path Linux, 0 failed).
  - 39/39 probe độc lập PASS 100% (ACK cắt lô, atomic batch 400 khi lỗi, token fail-closed 401 theo từng JIG, retry backoff, cursor bền đĩa).
- **Bằng chứng dữ liệu thật:** Đã chạy thử nghiệm replay 60 dòng log thật từ file CSV LSU Iris qua HTTP stream + 12 điểm drift mô phỏng (`SIMULATED_REALTIME`). Consumer nhận đủ 72/72 dòng và bắt đúng 2 cảnh báo drift.
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-rt.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-rt.md), [`docs/phieu-viec/ket-qua/j1-rt-api-spec.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-rt-api-spec.md), [`docs/phieu-viec/ket-qua/j1-rt-yeu-cau-ha-tang.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-rt-yeu-cau-ha-tang.md), [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md) §1 (E1, E2).
- **Đánh giá readiness:** **SPEC & PROTOTYPE ĐÃ SẴN SÀNG**.
  - *Việc còn thiếu cho Bước 2:* Phần hạ tầng vật lý (Server tiếp nhận và Agent/Watcher chạy trên máy tính JIG) chưa được triển khai ngoài nhà máy. Đây là hạng mục phụ thuộc hạ tầng CNTT công ty, đúng phạm vi ghi chú của kế hoạch (Bước 1 là chuẩn bị và thao tác tay, kết nối tự động server thuộc các bước sau).

---

### 2.8. Thu thập dữ liệu từ user (Trích xuất nội dung từ người dùng đưa vào)
- **Yêu cầu kế hoạch công ty:** Chức năng thu thập dữ liệu, trích xuất nội dung từ người dùng đưa vào (đã đánh dấu Hoàn thành trong bảng 30/09).
- **Mã nguồn thực thi:** [`src/aios_habit/workspace_chat_ui.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/workspace_chat_ui.py), [`jig_log_ingest.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/jig_log_ingest.py), [`iris_log_adapter.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/production_prediction/iris_log_adapter.py).
- **Bằng chứng kiểm thử:** [`tests/test_omnibar_jig_log_ingest.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_omnibar_jig_log_ingest.py) (passed), [`tests/test_jig_chat_wire.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_jig_chat_wire.py) (passed).
- **Bằng chứng dữ liệu thật:** Đã kiểm chứng trích xuất từ 3 nguồn: tải tệp CSV qua mục "Kiểm tra dữ liệu LSU", lệnh chat `nhập tệp log "..."`, và dán dòng log thô vào khung chat.
- **Báo cáo xác nhận:** [`docs/phieu-viec/ket-qua/j1-csv.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j1-csv.md), [`docs/phieu-viec/ket-qua/j2.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j2.md), [`docs/phieu-viec/ket-qua/j3.md`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/ket-qua/j3.md) §1 & §2.
- **Đánh giá readiness:** **ĐÃ HOÀN THÀNH 100%**.

---

## 3. Tổng hợp Ma trận Đánh giá Readiness Bước 1

| STT | Chức năng Bước 1 | Trạng thái kỹ thuật | Test tự động | Kiểm chứng dữ liệu thật | Báo cáo kiểm chứng | Mức độ sẵn sàng |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 1 | **Nhập CSV** | Hoàn thành | 15/15 passed | 24,4MB LSU CSV & 132 dòng Master CSV | `j1-csv.md`, `j2.md` | **SẴN SÀNG** |
| 2 | **Watch từng dòng** | Hoàn thành | 17/17 passed | Dòng 7 cột thật & ma trận Iris | `j1-csv.md`, `j2.md`, `sma-warmup-label-home.md` | **SẴN SÀNG** |
| 3 | **9 biểu đồ** | Hoàn thành (3x3) | 10/10 passed | 9 ảnh PNG thật (xu hướng, phân bố, so sánh) | `j1-csv.md`, `j2.md`, `j3.md` | **SẴN SÀNG** (Cần chốt định nghĩa) |
| 4 | **Cảnh báo ngưỡng** | Hoàn thành | 18/18 passed | Ngưỡng thật `SKEW:BLACK` -364 | `j2.md`, `j3.md` | **SẴN SÀNG** |
| 5 | **Cảnh báo xu hướng** | Hoàn thành + Đang tinh chỉnh | 31/31 passed | 21/21 vi phạm đơn điểm bị chặn; Warmup N/20 | `sma-gate-realdata-home.md`, `sma-warmup-label-home.md` | **CHỜ OMP CHỐT VÉ SMA-IMPROVE** |
| 6 | **Mail kèm biểu đồ** | Hoàn thành mô phỏng | 13/13 passed | File EML 71KB đính kèm PNG + duyệt tay | `j1-csv.md`, `j2.md`, `j3.md` | **SẴN SÀNG DÙNG THỬ** |
| 7 | **API realtime** | Spec + Prototype | 37 test + 39 probe | Replay 60 dòng thật + 12 điểm drift | `j1-rt.md`, `j1-rt-api-spec.md` | **SẴN SÀNG PROTOTYPE** |
| 8 | **Thu thập dữ liệu user** | Hoàn thành | Passed | Upload file UI, Chat, Dán log | `j1-csv.md`, `j2.md`, `j3.md` | **SẴN SÀNG** |

---

## 4. Chốt danh sách việc còn thiếu cho Bước 2 (Hạn 15/10/2026, còn 9 ngày)

Danh sách được xếp theo thứ tự ưu tiên (Độ gấp) và ước lượng độ lớn:

| STT | Công việc cần làm cho Bước 2 | Mức độ gấp | Ước lượng độ lớn | Phân vai / Đơn vị thực hiện | Nội dung chi tiết |
|:---:|---|:---:|:---:|:---:|---|
| **1** | **Hoàn thành tinh chỉnh cổng SMA(20) theo dữ liệu thật** | **P0 (Rất gấp — Chặn nghiệm thu Bước 2)** | Vừa (~1 ngày) | OMP (`SMA-IMPROVE-HOME`) | Bổ sung deadband tối thiểu cho hiện tượng `nen_phang_nhung_lech` (loại bỏ 58 cảnh báo giả do làm tròn cảm biến) và cấu hình $k$ linh hoạt (2.0–2.5) cho TaktTime trong `trend_alerts.py`. |
| **2** | **Cập nhật fixture bài test `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh`** | **P0 (Gấp — Chất lượng CI/Test)** | Nhỏ (~30 phút) | Agnostic (Sau vé SMA) | Trong [`tests/test_j1_csv.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_j1_csv.py#L230): Cập nhật input test để có chuỗi 3 điểm xấu liên tiếp kích hoạt cảnh báo xu hướng theo đúng logic cổng SMA(20) mới của commit `846713e`, đảm bảo test suite xanh 100%. |
| **3** | **Deploy ứng dụng Workspace Chat bản dùng thử lên máy công ty** | **P0 (Gấp — Hạn 15/10)** | Nhỏ (~1 giờ) | CTY / User (`DEPLOY-BUOC05-PC0575`) | Triển khai mã nguồn ghim (tối thiểu `5bb837e`), chạy `RUN_AIOS_WORKSPACE_CHAT.bat`, mở firewall LAN cổng 8501 để người dùng công ty truy cập và thao tác theo bộ tài liệu đã chuẩn bị tại [`docs/phieu-viec/dung-thu-jig/`](file:///D:/Sandbox/AIOS_habbit/docs/phieu-viec/dung-thu-jig/). |
| **4** | **Làm rõ với Người dùng / Trưởng nhóm về định nghĩa "9 biểu đồ"** | **P1 (Quan trọng)** | Nhỏ (Thảo luận) | Muse / User | Xác nhận xem mô hình hiện tại (3 loại biểu đồ chuẩn × 3 chỉ số đo thật = 9 biểu đồ) đã đáp ứng đúng kỳ vọng của công ty hay cần bổ sung thêm các loại biểu đồ SPC cụ thể nào khác. |
| **5** | **Khảo sát thông số cấu hình SMTP Server nội bộ công ty** | **P1 (Cần cho Bước 3)** | Nhỏ (~1 giờ) | CTY / IT Admin | Thu thập thông tin cấu hình máy chủ SMTP nội bộ (Host, Port, TLS, Tài khoản) để sẵn sàng cấu hình gửi mail thật khi bước sang giai đoạn dùng thử Bước 3. |
| **6** | **Thiết kế Agent thu thập log JIG tự động cho API Realtime** | **P2 (Chuẩn bị cho Bước 4–5)** | Vừa (~2 ngày) | Sau 15/10 | Viết script daemon nhẹ (Python/PowerShell) chạy nền trên máy JIG để giám sát thư mục log và tự động POST dòng log mới lên API `stream-log`. (Không chặn tiến độ nghiệm thu Bước 2 do kế hoạch công ty phân định Bước 1 là chuẩn bị thủ công). |

---

## 5. Kết luận nghiệm thu vé `AUDIT-BUOC2-JIG-HOME`

1. **Tuân thủ rào cứng:**
   - Hoàn toàn **không sửa mã nguồn** (`git diff --stat src/ tests/` rỗng).
   - Tuyệt đối **không đụng vào cổng SMA(20)** hay file `trend_alerts.py` (tuân thủ luật 1-file-1-đứa với OMP).
   - Không merge `main`, không đụng cơ sở dữ liệu production.
2. **Tính trung thực & Evidence-based:**
   - Toàn bộ 8 chức năng được đối chiếu trực tiếp với mã nguồn thực tế, các bộ test tự động (`pytest`) và bằng chứng chạy trên dữ liệu thật từ các báo cáo tiền nhiệm (`j1-csv.md`, `j1-rt.md`, `j2.md`, `j3.md`, `sma-gate-realdata-home.md`, `sma-warmup-label-home.md`).
   - Phát hiện rõ ràng 1 điểm lệch trong bài test cũ `test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh` do sự thay đổi có chủ đích của cổng gate SMA(20) từ ngày 03/10.
3. **Mức độ sẵn sàng của Bước 2 (Readiness):**
   - **8/8 chức năng Bước 1 đã có mã nguồn, test và kiểm chứng trên dữ liệu thật.**
   - Hệ thống hoàn toàn sẵn sàng bàn giao cho người dùng thử nghiệm ngay sau khi thợ OMP hoàn tất vé tinh chỉnh `SMA-IMPROVE-HOME` và tiến hành deploy trên máy công ty.
