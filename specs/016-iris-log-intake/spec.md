# Đặc tả tính năng: Nhận log JIG Iris, ngưỡng thật và gửi email cảnh báo

**Mã tính năng**: `016-iris-log-intake`

**Ngày tạo**: 24/09/2026

**Trạng thái**: Bản nháp — chờ thực thi

**Nguồn yêu cầu**: Sheet `các bước` của `AI_LSU_du_doan_loi.xlsx`, hạng mục kỳ hạn 23/09/2026 và 15/10/2026.

## Vì sao có tính năng này

Kỳ hạn 23/09/2026 **chưa đạt**. Ba hạng mục trong bảng yêu cầu đang có code nhưng không dùng được với dữ liệu thật tại xưởng:

| # | Hạng mục (Excel) | Kỳ hạn | Trạng thái kiểm chứng 24/09/2026 |
|---|---|---|---|
| 1 | Phân tích dữ liệu JIG người dùng đưa vào | 23/09/2026 | Có code, chạy sai với log Iris thật |
| 2 | Cảnh báo theo ngưỡng người dùng thiết lập (giới hạn trên/dưới) | 23/09/2026 | Không có ngưỡng thật |
| 3 | Thông báo: mail + đính kèm biểu đồ | (trống) | Có code, chưa nối vào giao diện |
| 4 | Thu thập dữ liệu, trích xuất nội dung | Hoàn thành | Đạt |
| 5 | Nhập tệp CSV log JIG và chọn biểu đồ | 15/10/2026 | Xong code, thiếu fixture trong Git |

## Bằng chứng hiện trạng

### Hạng mục 1 — bộ phân tích dòng log không khớp định dạng Iris

`jig_log_ingest.parse_jig_log_line` giả định thứ tự cột `timestamp, unit_serial, jig_id, metric, value, unit, status`. Log Iris thật (`Tài liệu của tất cả dòng máy/Iris LSU/log/2ND-1035-1_2026_07_UnitTest.csv`) có thứ tự `DATE, TIME, SERIAL NUMBER, RESULT, RESULT:BLACK, …` với 572 cột.

Chạy dòng log thật qua `decide_jig_action`:

```text
timestamp=None  unit_serial='2026.07.01'  jig_id='16:33:07'
metric='61C1066E2902'  value=None  unit='ok'  status='OK'
→ Thẻ chat: "Kết luận: Cần kiểm tra — 2026.07.01 — 61C1066E2902 (Thiếu dữ liệu)"
            "Giá trị: None ok | JIG: 16:33:07"
```

Dán kèm dòng tiêu đề (thao tác tự nhiên của người dùng) → `handled=False`, tin nhắn rơi về RAG.

Kiểm tra `grep -rl "SERIAL NUMBER|RESULT:BLACK|BOW:BLACK" src/ tests/ scripts/` cho kết quả rỗng: **không tồn tại bộ chuyển đổi nào** từ log Iris sang bản ghi chuẩn.

### Hạng mục 2 — ngưỡng người dùng thiết lập không tồn tại

`nguong_phan_tram` chỉ được lưu và hiển thị; `grep nguong_phan_tram src/` chỉ thấy đường đọc/ghi cấu hình, không có nơi nào dùng để quyết định cảnh báo.

`USL`/`LSL` trong `spc_chart.py` chỉ là tham số vẽ đường. `chart_selection.dung_du_lieu_bieu_do` đặt `ucl/cl/lcl = trung bình ± 3σ` và để `usl/lsl = None`. Thẻ log in câu "Đối chiếu dải dung sai tiêu chuẩn [USL, LSL]" nhưng không có giá trị nào phía sau.

**Phát hiện quan trọng cho thiết kế**: ngưỡng thật **đã có sẵn trong log của JIG**, không cần người dùng tự nhập tay:

- `thu nghiem 6pcs do thong so va log/2ND-1004/2026_08_Spec.csv` — 5.225 dòng, cột `Spec:Bow[um], Spec:Skew[um], Spec:LightPath[mm], Spec:BeamDiameterH[um], Spec:BeamDiameterV[um], Spec:Current:Lower[mA], Spec:Current:Upper[mA]` với giá trị mẫu `25, 25, 1.000, 75, 75, 370, 520`.
- `2ND-1004/2026_08_CamPos.csv` — `Spec:BeamPosX:Lower[um], Spec:BeamPosX:Upper[um], Spec:BeamPosY:Lower[um], Spec:BeamPosY:Upper[um]` với giá trị mẫu `2890, 3190, 3350, 3650`.

Đây chính là "giới hạn trên/dưới của một giá trị thông số" mà Excel yêu cầu.

### Hạng mục 3 — mailer chưa nối

`grep -rn "alert_mailer" src/` chỉ thấy khai báo tên trong `__init__.py`. `grep -n "email" workspace_chat_app.py workspace_chat_ui.py` cho kết quả rỗng. `send_via_smtp()` cần `host/port/ten_dang_nhap/mat_khau` nhưng không nơi nào cấu hình.

### Hạng mục 5 — fixture bị Git bỏ quên (đã sửa)

`.gitignore` dòng 80 có `*.csv`, dòng 78 có `*.xlsx`, nuốt luôn toàn bộ fixture dưới `tests/fixtures/`. `git ls-files tests/fixtures/lsu_iris/` từng trả về rỗng, nên mọi bản clone đều fail 12 test với `FileNotFoundError`. Spec 015 ghi `[x] T001 Tạo thư mục fixture` nhưng thực tế chưa từng vào Git.

## Hợp đồng dữ liệu log Iris

### Nhóm A — tệp kiểm tra đơn vị rộng (UnitTest)

Một dòng = một lần đo một Unit. Số cột 572 (2ND-1035) đến 1059 (2ND-1004).

```text
DATE, TIME, SERIAL NUMBER, RESULT, RESULT:BLACK, RESULT:MAGENTA, RESULT:CYAN, RESULT:YELLOW,
SKEW:BLACK[um], BOW:BLACK:-70[um], BOW:BLACK:0[um], BOW:BLACK:+70[um], … 480 cột BEAM_DIAMETER …
2026.07.01,16:33:07,61C1066E2902,OK,OK,OK,OK,OK,-320,52,-45,-21,…
```

Quy ước cột chỉ số: `<HỌ>:<MÀU>:<VỊ TRÍ>[<đơn vị>]`, họ gồm `BOW`, `SKEW`, `LIGHT_PATH`, `BEAM_DIAMETER`, `BEAMPITCH`, `RESULT`. Giá trị canh lỗi là `999`.

### Nhóm B — tệp giới hạn (Spec)

```text
DATE, TIME, S/N, Spec:Bow[um], Spec:Skew[um], Spec:LightPath[mm], Spec:BeamDiameterH[um], …
```

### Nhóm C — tệp đo sâu (Depth)

Nhiều khối, mỗi khối mở đầu bằng dòng `ngày,giờ,mã_sản_phẩm`, tiếp theo là các dòng `,,,,CamPos,…` và `,,,,imgHeight:<vị trí>,…`.

## Kế hoạch thực thi

### Giai đoạn 1 — Bộ chuyển đổi log Iris (hạng mục 1)

- **T016-01** Tạo `src/aios_habit/production_prediction/iris_log_adapter.py` (logic thuần, không import Streamlit):
  - `doc_log_iris(duong_dan)` → danh sách bản ghi chuẩn 13 cột của `lsu_iris`.
  - Tách ma trận rộng thành từng cặp (Unit, chỉ số, giá trị) theo quy ước `<HỌ>:<MÀU>:<VỊ TRÍ>[<đơn vị>]`.
  - Bỏ giá trị canh `999` và ghi nhận lý do, không âm thầm nuốt.
  - Giữ `RESULT:<MÀU>` làm `target_label` cho từng màu.
  - Đọc nhóm B (`Spec:`) và nhóm C (`Depth`) thành ngưỡng và chuỗi đo.
- **T016-02** Nối vào Thẻ 1 (`prediction_shadow_ui.py`): nhận diện tệp log Iris và tự chuyển sang bản ghi chuẩn.
- **T016-03** Sửa `jig_log_ingest.parse_jig_log_line` để hiểu dòng Iris thật, gồm cả trường hợp dán kèm dòng tiêu đề.
- **T016-04** Ghi rõ cột nào thiếu khi tệp không hợp lệ, thay cho câu chung chung hiện tại.

### Giai đoạn 2 — Ngưỡng trên/dưới thật (hạng mục 2)

- **T016-05** Tạo `src/aios_habit/production_prediction/metric_limits.py`: lưu ngưỡng theo (JIG, chỉ số) với `gioi_han_tren`, `gioi_han_duoi`, `nguon` (từ tệp Spec, hoặc người dùng nhập), `nguong_phan_tram`.
- **T016-06** Đọc ngưỡng từ nhóm B/C khi có, để tự điền thay vì bắt nhập tay.
- **T016-07** Dùng ngưỡng thật trong `evaluate_single_log_ewma` để quyết định `Đạt / Cận biên / Vi phạm`; hiện chỉ dùng trung bình ± 3σ.
- **T016-08** Truyền `usl/lsl` thật vào `chart_selection.dung_du_lieu_bieu_do` để biểu đồ có đường giới hạn trên/dưới đúng nghĩa.
- **T016-09** Thêm đường nhập ngưỡng qua chat: "đặt ngưỡng trên 25 cho Bow", có xem lại và xóa.

### Giai đoạn 3 — Gửi email cảnh báo (hạng mục 3)

- **T016-10** Lưu cấu hình SMTP ngoài Git, không ghi mật khẩu vào mã nguồn.
- **T016-11** Nối `build_alert_email` + `send_via_smtp` vào giao diện: thẻ đề xuất có ảnh xem trước, nút gửi, mã duyệt.
- **T016-12** Dùng chung ảnh đang xem trước, không vẽ lại; áp dụng giãn cách chống spam.
- **T016-13** Lỗi gửi mail phải là câu tiếng Việt có bước xử lý.

### Giai đoạn 4 — Kiểm chứng và bàn giao

- **T016-14** Fixture mẫu cho cả ba nhóm tệp Iris, dựng từ dữ liệu tổng hợp `SYN_`, không dùng dữ liệu thật.
- **T016-15** Kiểm thử cho bộ chuyển đổi, ngưỡng và thư viện mail.
- **T016-16** Chạy `compileall`, `pytest -q`, `cli audit`, `import workspace_chat_app`.
- **T016-17** Kiểm toán độc lập trước khi kết luận đạt.

## Rủi ro

- **Dữ liệu thật không được vào Git hay prompt ngoài.** Fixture kiểm thử phải là dữ liệu tổng hợp. Thư mục `Tài liệu của tất cả dòng máy/` chứa tệp khách hàng, tuyệt đối không commit.
- **Tên miền chỉ số rất rộng** (480 cột `BEAM_DIAMETER`). Cần xác nhận với chủ sở hữu nhóm chỉ số nào cần hiện trước; spec 015 đã chọn độ lệch và độ nghiêng 4 màu.
- **Ngưỡng trong tệp Spec là ảnh chụp theo thời điểm**, có thể đổi giữa các lô. Phải ghi kèm nguồn và thời điểm, không coi là hằng số.
- **`nguong_phan_tram` hiện chưa nối vào quyết định cảnh báo.** Khi nối cần giữ tương thích với cấu hình đã lưu trong `local_cases/jig_alert_config.json`.
- Chưa xác nhận máy chủ SMTP nội bộ và tài khoản gửi mail; nếu chưa có, chỉ nên hoàn tất đến bước tạo thẻ đề xuất và dừng lại ở đó.
