# Nhiệm vụ: Nhận log JIG Iris, ngưỡng thật và gửi email cảnh báo

**Đầu vào**: `specs/016-iris-log-intake/spec.md`.

**Điều kiện**: Dữ liệu thật gắn nhãn `local_only`, không vào Git hay prompt ngoài; kiểm thử chỉ dùng fixture tổng hợp.

**Kiểm thử**: Viết kiểm thử trước, bảo đảm thất bại trước khi sửa và đạt sau khi sửa.

## Giai đoạn 1: Bộ chuyển đổi log Iris (hạng mục 1 — kỳ hạn 23/09/2026)

- [x] T016-01 Tạo `src/aios_habit/production_prediction/iris_log_adapter.py`: `doc_log_iris()`, tách ma trận rộng `<HỌ>:<MÀU>:<VỊ TRÍ>[<đơn vị>]`, bỏ canh `999`, giữ `RESULT:<MÀU>` làm `target_label`
  - Tên chỉ số giữ **đúng thứ tự thành phần như tệp gốc** (bỏ phần `[đơn vị]`), ví dụ `APC:CURRENT`, `BEAM_DIAMETER:H:BLACK:-140:0:LD1`. Không ghép lại theo thứ tự khác vì tên này phải tra khớp được với tệp giới hạn của JIG. Lỗi đã gặp và đã sửa: cột hai thành phần từng sinh tên sai `APC::CURRENT`.
  - `chuyen_ban_ghi_iris_sang_snapshot()` chuyển kết quả thành `LsuDatasetSnapshot` chuẩn, nên cổng dữ liệu, nối chuỗi và vẽ biểu đồ dùng lại nguyên vẹn, không cần định dạng trung gian mới.
- [x] T016-02 Nối bộ chuyển đổi vào Thẻ 1 trong `src/aios_habit/prediction_shadow_ui.py`
  - Thẻ 1 có ô chọn kiểu tệp: **log JIG Iris (một tệp)** hoặc **ba tệp chuẩn**. Chế độ log Iris nhận nhiều tệp, tự tách, hiện số ô canh lỗi đã bỏ.
- [x] T016-03 Sửa `parse_jig_log_line` trong `jig_log_ingest.py` hiểu dòng Iris thật, kể cả khi dán kèm dòng tiêu đề
  - Dòng Iris thật (572–1.059 cột) được nhận diện trước heuristic 7 cột và **không** bị `parse_jig_log_line` băm nát thành `serial='2026.07.01'`, `metric='61C1066E2902'` như lỗi cũ.
  - Dán kèm tiêu đề + dòng dữ liệu → tách đúng hàng trăm giá trị đo. Dán dòng trần không tiêu đề → hỏi lại bằng tiếng Việt (không thể đoán 572 tên cột), thay vì bịa tên chỉ số.
- [x] T016-04 Liệt kê cột còn thiếu khi tệp không hợp lệ, bỏ câu thông báo chung chung
  - `thong_diep_thieu_cot()` nêu đúng tên cột thiếu (ví dụ `SERIAL NUMBER`) và tên tệp.

## Giai đoạn 2: Ngưỡng trên/dưới thật (hạng mục 2 — kỳ hạn 23/09/2026)

- [x] T016-05 Tạo `metric_limits.py`: ngưỡng theo (JIG, chỉ số) kèm `gioi_han_tren`, `gioi_han_duoi`, `nguon`, `nguong_phan_tram`
  - Khoá thực tế là `(jig_id, chi_so, unit_serial)` vì mỗi số sê-ri có dải dung sai riêng.
- [x] T016-06 Đọc ngưỡng từ tệp nhóm Spec/CamPos để tự điền
  - `doc_nguong_tu_tep_gioi_han()` tra **đúng S/N và đúng thời điểm đo**, chỉ lấy dòng có thời điểm ≤ lúc đo (chống rò rỉ tương lai). Thẻ 1 nhận tệp giới hạn kèm theo và nạp vào `local_cases/metric_limits.json`.
  - **Phát hiện quan trọng khi đo dữ liệu thật**: `2026_08_Spec.csv` có 5.224 dòng và một S/N lặp lại nhiều lần với ngưỡng khác nhau (một S/N có cặp 50/200 mA, một S/N khác có cặp 370/520 mA). Tra theo dòng mới nhất của cả tệp gây **1/5 Unit OK bị gắn cờ sai**; tra theo đúng S/N còn **0/5**. Vì vậy bắt buộc tra theo S/N.
- [x] T016-07 Dùng ngưỡng thật trong `evaluate_single_log_ewma` thay cho trung bình ± 3σ
  - Khi có ngưỡng hiệu lực thì ngưỡng thật quyết định kết luận; độ lệch chuẩn chỉ còn là đường tham khảo trên biểu đồ. Kết quả mang thêm `nguon_nguong` để thẻ chat nói rõ nguồn.
  - **Quy tắc an toàn**: chỉ cặp `:Lower`/`:Upper` tường minh mới tự động có hiệu lực. Dung sai một con số (`Spec:Bow[um] = 25`) vào trạng thái `cho_xac_nhan`, vì đo thật trên 2ND-1004 cho thấy `Bow:Black:0` nằm trong −225…+22 nhưng máy vẫn chấm `OK` — áp thẳng ±25 sẽ báo động giả hàng loạt.
- [x] T016-08 Truyền `usl/lsl` thật vào `dung_du_lieu_bieu_do` để biểu đồ có đường giới hạn trên/dưới
  - `chart_selection.ma_chi_so_chuan()` quy `BOW:BLACK:0` → `BOW`, `BEAM_POS:X:BLACK:-140:LD1` → `BEAM_POS:X`, để tra khớp khoá ngưỡng. Cả khối chọn biểu đồ ở Thẻ 1 và lệnh chat đều dùng chung đường này.
- [x] T016-09 Thêm đường nhập ngưỡng qua chat, có xem lại và xóa
  - Hỗ trợ `xem ngưỡng`, `đặt ngưỡng trên 25 cho Bow`, `đặt ngưỡng dưới 1.2 cho BeamPosX`, `xóa ngưỡng Bow`. Không giành lấy lệnh cấu hình cảnh báo chung (`đổi ngưỡng 90%`, `thêm email`, `đổi giãn cách`).
  - Lỗi thật đã gặp và đã sửa: cờ phát hiện thay đổi so với chính kho đã bị sửa nên luôn ra "không đổi", khiến ngưỡng **không được lưu**. Đã sửa bằng so trên bản sao, kèm kiểm thử.

## Giai đoạn 3: Gửi email cảnh báo (hạng mục 3)

- [x] T016-10 Lưu cấu hình SMTP ngoài Git, không ghi mật khẩu vào mã nguồn
  - `smtp_config.py` + `local_cases/smtp_config.json` (đã bị Git bỏ qua). `to_dict()` **không** trả mật khẩu.
- [x] T016-11 Nối `build_alert_email` và `send_via_smtp` vào giao diện qua thẻ đề xuất có mã duyệt
  - Thẻ đề xuất hiện ở Thẻ 1 (khối LSU) và ở thanh nhập chat. Gửi đi qua `can_send_with_approval` (cần mã duyệt và thao tác duyệt) rồi `gui_voi_cau_hinh`.
- [x] T016-12 Dùng lại ảnh đang xem trước, không vẽ lại; áp dụng giãn cách chống spam
  - Thẻ đọc thẳng `st.session_state["wsc_last_chart_png"]`, có kiểm thử khẳng định không gọi `render_chart_png`/`render_chart_svg`/`render_spc_png`. Giãn cách theo `AlertCooldownTracker` khoá `JIG|chỉ số`.
- [x] T016-13 Lỗi gửi mail là câu tiếng Việt kèm bước xử lý
  - `thong_bao_loi_gui()` trả câu tiếng Việt có bước tiếp theo, không lộ văn bản lỗi thô và không lộ mật khẩu. Thiếu cấu hình thì báo đúng câu hướng dẫn bổ sung máy chủ/cổng/tài khoản.

## Giai đoạn 4: Kiểm chứng và bàn giao

- [x] T016-14 Fixture tổng hợp cho ba nhóm tệp Iris
  - `tests/fixtures/lsu_iris/iris_log/`: `unit_test/` (log 572 cột, bản dán kèm tiêu đề, bản thiếu cột, bản đối chiếu ngưỡng), `spec/` (giới hạn có `:Lower`/`:Upper` và dung sai một con số), `depth/` (nhóm C nhiều khối). Toàn bộ là dữ liệu `SYN_` tổng hợp.
- [x] T016-15 Kiểm thử bộ chuyển đổi, ngưỡng và thư viện mail
  - `tests/test_iris_log_intake.py` **31 passed**; `tests/test_smtp_config_mail_ui.py` **11 passed**.
- [x] T016-16 Chạy `compileall`, `pytest -q`, `cli audit`, `import workspace_chat_app`
  - `compileall` sạch; `cli audit` `"status": "PASS"`; `import aios_habit.workspace_chat_app` thoát mã 0; bộ liên quan **121 passed**.
- [x] T016-17 Kiểm toán độc lập trước khi kết luận đạt
  - 2026-09-24, kiểm toán viên độc lập (vai `reviewer`, phiên riêng, không dùng báo cáo của người thực thi). Lượt đầu kết luận **A chỉ đúng phần số liệu đếm được, B/D chưa đủ, C/E đạt** và nêu **7 lỗi thật**:
    1. **Rò rỉ tương lai**: đo trước mọi dòng Spec của một S/N thì hàm rơi về dòng muộn nhất (một dòng ở tương lai). Đã sửa: trả rỗng.
    2. **Khoá ngưỡng chỉ theo S/N**: nạp ngưỡng chỉ giữ dải của lần đo đầu, nên dải mới bị áp ngược cho lần đo cũ. Đã sửa: khoá thêm mốc `hieu_luc_tu`, tra theo thời điểm đo.
    3. **Biểu đồ vẽ dải của S/N đầu danh sách chưa lọc**. Đã sửa: chỉ lấy S/N của đúng dòng đang vẽ; nhiều S/N thì **không** vẽ đường giới hạn.
    4. **Dung sai chờ xác nhận che mất ngưỡng dùng chung đã hiệu lực**, đổi kết luận Đạt thành Vi phạm. Đã sửa: ưu tiên bản ghi đã hiệu lực.
    5. **Canh lỗi chỉ so bằng đúng 999** nên `999.9` lọt vào dữ liệu dùng được. Đã sửa thành vùng `999 ≤ |v| < 1000`; lượt hai phát hiện thêm biến thể `9999.9` nên vùng canh lỗi nay gồm cả `9999 ≤ |v| < 10000`. **Không** dùng ngưỡng `≥ 999` vì sẽ nuốt giá trị thật `BeamPosX` ≈ 2890–3190 µm.
    6. **Cột `Current[mA]`/`Voltage[V]` và `BeamPosX/Y` không được nhận diện**, nên ngưỡng thật không bao giờ gặp giá trị đo. Đã sửa cả ba họ cột, thêm quy đổi `Current` → `APC:CURRENT`, `BeamPosX` → `BEAM_POS:X`, và bỏ đơn vị nằm giữa tên cột (`BeamPosX:Black:-140:LD1_1[um]:6face`).
    7. **`đổi ngưỡng 90` bị giành khỏi đường cấu hình cảnh báo**. Đã sửa, đồng thời giữ `đổi ngưỡng trên 25 cho Bow` đi đúng đường ngưỡng chỉ số.
  - Bảy lỗi đều đã sửa kèm **kiểm thử chống tái phát**; lượt kiểm toán thứ hai xác nhận các lỗi 1, 4, 5, 7 đã hết và nêu tiếp 5 lỗi còn sót (thứ tự tra ngưỡng, mốc thời gian của biểu đồ, cột BeamPos, dòng Spec thiếu thời điểm, lệnh `đổi ngưỡng trên` bị chặn oan). Lượt thứ ba xác nhận 6/6 điểm đã hết và nêu 3 lỗi còn sót (tiêu đề không đơn vị làm ném lỗi, ngưỡng chat bị ngưỡng Spec của JIG đè, biểu đồ nhiều S/N vẫn vẽ dải dùng chung) — đã sửa hết.
  - **Lượt thứ tư: kiểm toán viên ký xác nhận cả A–E, `findings` rỗng.** Số liệu trên dữ liệu thật giữ nguyên: tệp 572 cột `usable=18833, skipped=535`; tệp 1.059 cột `usable=8351, skipped=739` (gồm cả `9999.9`), `BeamPos` 3.945 bản ghi `max=3554.2`, không giá trị nào nằm trong vùng canh lỗi lọt vào dữ liệu dùng được.

## Phụ thuộc

- Giai đoạn 2 cần T016-01 xong để biết tên chỉ số chuẩn.
- Giai đoạn 3 cần T016-08 để có ảnh biểu đồ mang ngưỡng thật.
- T016-17 chạy sau cùng, độc lập với người thực thi.

## Ghi chú

- Đã xong trước khi lập kế hoạch: `.gitignore` cho phép fixture vào Git, gỡ 12 kiểm thử thất bại (`commit 71d9f26`).
- Chưa có máy chủ SMTP nội bộ: chưa xác nhận được, nên dừng ở thẻ đề xuất, **không gửi thật**. Đã kiểm chứng bằng kiểm thử với `smtplib.SMTP` giả, không mở kết nối thật.
- Chi tiết các phát hiện dữ liệu thật (S/N trùng, Bow ngoài ±25 vẫn OK) ghi ở `specs/016-iris-log-intake/spec.md` phần rủi ro.
