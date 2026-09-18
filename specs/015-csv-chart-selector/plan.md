# Kế hoạch triển khai: Chọn biểu đồ khi nhập tệp CSV LSU

**Mã tính năng**: `015-csv-chart-selector` | **Ngày**: 18/09/2026 | **Đặc tả**: [spec.md](spec.md)

**Đầu vào**: Đặc tả từ `spec.md` trong cùng thư mục, gồm 3 câu chuyện P1–P3 và 5 ý làm rõ đã chốt ngày 18/09/2026.

## Tóm tắt

Nối lõi vẽ biểu đồ đã có (`spc_chart.py` từ T060) ra giao diện nhập tệp ở Thẻ 1 màn hình LSU và ra khung chat Omnibar, dùng chung một hàm dựng dữ liệu. Người dùng chọn 1 trong 3 loại (xu hướng, phân bố, so sánh theo màu), ưu tiên nhóm độ lệch và độ nghiêng 4 màu, hỗ trợ cả CSV và Excel, ảnh dùng chung cho xem trước và email. Tệp đo sâu không tiêu đề được tự nhận diện linh hoạt, chỉ hỏi bổ sung khi mơ hồ.

## Bối cảnh kỹ thuật

- **Ngôn ngữ và phiên bản**: Python 3.11, quản lý qua `uv` theo `pyproject.toml`.
- **Phụ thuộc chính**: Tái dùng Pillow đã có, giao diện Streamlit hiện có, gửi mail bằng thư viện chuẩn đã dùng ở cảnh báo. Không thêm thư viện, khung công tác hay cơ sở dữ liệu mới.
- **Lưu trữ**: Không thêm bảng mới. Đọc gói dữ liệu sẵn có trong phiên; ảnh vẽ ra tệp tạm rồi dọn, không lưu dữ liệu thô vào kho.
- **Kiểm thử**: `pytest` theo nhóm `dev`, chạy trên dữ liệu mẫu đã làm sạch tại `tests/fixtures/lsu_iris/` cộng thêm fixture mới cho 3 loại biểu đồ.
- **Nền tảng mục tiêu**: Máy tính xách tay Windows chạy Workspace Chat cục bộ.
- **Dạng dự án**: Dự án đơn, mã nguồn tại `src/`, kiểm thử tại `tests/`.
- **Mục tiêu hiệu năng**: Tải tệp mẫu và xem được ảnh đúng trong dưới 2 phút; mở danh sách chỉ số của tệp rộng 500–1100 cột trong dưới 5 giây; tệp lớn nhất quan sát khoảng 26 MB vẫn thao tác được.
- **Ràng buộc**: Giao diện 100% tiếng Việt dễ hiểu; dữ liệu thật gắn nhãn `local_only`, ở lại máy, không vào Git hay câu lệnh gửi ra ngoài; giữ giới hạn máy CSV 100 MB, XLSX 25 MB, 200.000 dòng mỗi bảng, lô 10.000 dòng; không khôi phục đường cũ `studio` hay `case_cockpit`.
- **Quy mô và phạm vi**: 49 tệp CSV thực tế thuộc 3 nhóm JIG đã khảo sát ở mức manifest; nhịp này chỉ làm chọn và xem 3 loại biểu đồ cho đích BOWSKEW 4 BEAM, các chỉ số khác mở dần sau.

## Kiểm tra hiến chương

- **I. Bằng chứng trước khẳng định**: Mọi nhiệm vụ phải có kiểm thử thất bại trước, đạt sau, kèm biên nhận lệnh. Không ghi `PASS` khi thiếu bằng chứng. Đạt.
- **II. Cục bộ trước và đồng ý**: Chỉ dùng manifest và fixture mẫu trong phát triển; tệp thật chỉ mở cục bộ để kiểm chứng, không đưa dòng dữ liệu, mã sản phẩm hay giá trị đo vào Git, báo cáo hay prompt ngoài. Đạt.
- **III. Tri thức gọn nhẹ, dùng lại được**: Tái dùng lõi vẽ và kho dự đoán hiện có; ảnh ra PNG và SVG mở. Không tạo định dạng độc quyền. Đạt.
- **IV. Tiếng Việt duy nhất trên bề mặt**: Mọi nhãn, hướng dẫn, lỗi và nhật ký người dùng đọc đều tiếng Việt; lỗi thư viện phải được chặn và dịch. Đạt.
- **V. Kỷ luật thay đổi và chất lượng kiểm chứng được**: Đi đúng `specify → clarify → plan → tasks → implement`; thay đổi hành vi cập nhật `PROJECT_HANDOVER.md`; trước khi đóng chạy đủ `compileall`, `pytest -q`, `cli audit` đạt `PASS`, `import workspace_chat_app` thành công. Đạt.

Không có vi phạm cần biện minh. Không thêm hàng theo dõi phức tạp.

## Cấu trúc dự án

### Tài liệu của tính năng này

```text
specs/015-csv-chart-selector/
├── plan.md              # Tệp này
├── research.md          # Kết quả nghiên cứu giai đoạn 0
├── data-model.md        # Mô hình dữ liệu giai đoạn 1
├── quickstart.md        # Hướng dẫn kiểm chứng nhanh
├── contracts/           # Hợp đồng giao diện
└── tasks.md             # Do bước speckit-tasks tạo, không tạo ở đây
```

### Mã nguồn (gốc repo)

```text
src/aios_habit/production_prediction/
├── spc_chart.py            # Tái dùng + mở rộng 2 loại còn lại
├── chart_selection.py      # Mới: hàm dựng dữ liệu biểu đồ dùng chung
├── alert_mailer.py         # Tái dùng ảnh cho email
└── lsu_iris.py             # Tái dùng đọc và chuẩn hóa

src/aios_habit/
├── prediction_shadow_ui.py  # Thêm khối chọn ở Thẻ 1
├── workspace_chat_ui.py     # Thẻ xem tức thì nếu cần
└── workspace_chat_app.py    # Lệnh chat tự nhiên + cô lập phiên

tests/
├── test_csv_chart_selector.py        # Hợp đồng chọn và vẽ 3 loại
├── test_csv_chart_selector_ui.py     # Trạng thái trống, lỗi, thành công
└── fixtures/lsu_iris/chart_selector/ # Dữ liệu mẫu mới
```

**Quyết định cấu trúc**: Giữ dự án đơn hiện có, chỉ thêm một module dựng dữ liệu dùng chung và kiểm thử đi kèm; không tách dịch vụ hay gói mới.

## Giai đoạn 0 — Nghiên cứu

Đã kết thúc trong [research.md](research.md). Mọi điểm chưa rõ kỹ thuật đã được chốt theo 5 ý làm rõ trong `spec.md`.

## Giai đoạn 1 — Thiết kế và hợp đồng

- Mô hình dữ liệu: [data-model.md](data-model.md).
- Hợp đồng chọn và vẽ biểu đồ: [contracts/chart-selection.md](contracts/chart-selection.md).
- Hướng dẫn kiểm chứng nhanh: [quickstart.md](quickstart.md).
- Kiểm tra lại hiến chương sau thiết kế: không phát sinh vi phạm mới; ảnh email tái dùng đúng ranh giới `local_only`.
