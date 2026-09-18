# Nhiệm vụ: Chọn biểu đồ khi nhập tệp CSV LSU

**Đầu vào**: Tài liệu thiết kế từ `specs/015-csv-chart-selector/` (bắt buộc `plan.md`, `spec.md`; kèm `research.md`, `data-model.md`, `contracts/`, `quickstart.md`).

**Điều kiện**: `plan.md` và `spec.md` đã duyệt; dữ liệu thật gắn nhãn `local_only`, không vào Git hay prompt ngoài; kiểm thử chỉ dùng fixture mẫu.

**Kiểm thử**: Có viết kiểm thử trước, bảo đảm thất bại trước khi sửa và đạt sau khi sửa.

**Cách tổ chức**: Nhiệm vụ nhóm theo câu chuyện người dùng để triển khai và kiểm thử độc lập từng câu chuyện.

## Định dạng: `[ID] [P?] [Story] Mô tả`

- **[P]**: Chạy song song được (khác tệp, không phụ thuộc việc chưa xong)
- **[Story]**: Câu chuyện thuộc về (ví dụ US1, US2, US3)
- Mỗi mô tả ghi rõ đường dẫn tệp

## Quy ước đường dẫn

- Dự án đơn: `src/`, `tests/` tại gốc repo

---

## Giai đoạn 1: Chuẩn bị (Hạ tầng dùng chung)

**Mục đích**: Khởi tạo cấu trúc và đường cơ sở kiểm chứng

- [x] T001 Tạo thư mục fixture `tests/fixtures/lsu_iris/chart_selector/` kèm tệp mẫu hợp lệ, thiếu cột và tệp đo sâu không tiêu đề
- [x] T002 [P] Chạy đường cơ sở `compileall`, `pytest -q`, `cli audit`, `import workspace_chat_app` và ghi biên nhận vào `local_runs/`
- [x] T003 [P] Rà soát mặt chữ tiếng Việt hiện tại của `src/aios_habit/prediction_shadow_ui.py` bằng `scripts/check_user_facing_vietnamese.py`

---

## Giai đoạn 2: Nền tảng (Điều kiện chặn trước mọi câu chuyện)

**Mục đích**: Hàm dựng dữ liệu dùng chung và lõi vẽ 3 loại biểu đồ

**⚠️ QUAN TRỌNG**: Không làm việc câu chuyện nào khi chưa xong giai đoạn này

- [x] T004 Tạo module dựng dữ liệu dùng chung trong `src/aios_habit/production_prediction/chart_selection.py` (tìm JIG, tìm chỉ số, ưu tiên nhóm độ lệch và độ nghiêng 4 màu, nhận diện tệp đo sâu không tiêu đề theo vị trí cột)
- [x] T005 [P] Mở rộng 2 loại biểu đồ còn lại (phân bố giá trị, so sánh theo màu) trong `src/aios_habit/production_prediction/spc_chart.py`, tái dùng tem thông tin và xuất PNG 300 DPI cùng SVG
- [x] T006 [P] Tạo bảng tên tiếng Việt cho mã JIG và chỉ số trong `src/aios_habit/production_prediction/chart_selection.py` (kèm mã gốc để truy vết)
- [x] T007 Chuẩn hóa lỗi tệp trống, sai cấu trúc, vượt giới hạn thành câu tiếng Việt trong `src/aios_habit/production_prediction/chart_selection.py`

**Điểm dừng**: Nền tảng xong, các câu chuyện có thể làm tiếp

---

## Giai đoạn 3: Câu chuyện 1 — Ô chọn gọn ở Thẻ 1 (Ưu tiên: P1) 🎯 MVP

**Mục tiêu**: Người không chuyên chọn JIG, chỉ số và 1 trong 3 loại biểu đồ ngay sau khi dữ liệu báo hợp lệ, xem trước và tải về được

**Kiểm thử độc lập**: Chỉ với tệp mẫu hợp lệ, tải lên, chọn từ danh sách gợi ý và nhận ảnh đúng JIG, đúng chỉ số, đúng loại

### Kiểm thử cho câu chuyện 1 ⚠️

> **GHI NHỚ: Viết kiểm thử trước, bảo đảm THẤT BẠI trước khi cài đặt**

- [x] T008 [P] [US1] Kiểm thử hợp đồng chọn và vẽ 3 loại trong `tests/test_csv_chart_selector.py`
- [x] T009 [P] [US1] Kiểm thử giao diện các trạng thái trống, lỗi và thành công trong `tests/test_csv_chart_selector_ui.py`

### Cài đặt cho câu chuyện 1

- [x] T010 [US1] Thêm khối chọn JIG, chỉ số, loại biểu đồ và loại ảnh dưới kết quả cổng dữ liệu trong `src/aios_habit/prediction_shadow_ui.py` (phụ thuộc T004, T005)
- [x] T011 [US1] Hiện ảnh xem trước và nút tải về trong `src/aios_habit/prediction_shadow_ui.py`
- [x] T012 [US1] Chạy kịch bản 1 trong `specs/015-csv-chart-selector/quickstart.md` bằng fixture mẫu và sửa lỗi phát sinh

**Điểm dừng**: Câu chuyện 1 chạy độc lập được và sẵn sàng demo

---

## Giai đoạn 4: Câu chuyện 2 — Câu chat tự nhiên (Ưu tiên: P2)

**Mục tiêu**: Gõ câu tiếng Việt vào khung chat duy nhất để vẽ cùng ảnh như ô chọn; thiếu thông tin thì hỏi lại

**Kiểm thử độc lập**: Chỉ với câu chat và cùng gói dữ liệu mẫu, nhận ảnh đúng kèm câu giải thích tiếng Việt

- [x] T013 [P] [US2] Kiểm thử hiểu câu chat vẽ biểu đồ trong `tests/test_csv_chart_selector.py`
- [x] T014 [US2] Nhận diện mã JIG và tên chỉ số từ câu chat, gọi đúng hàm dựng chung trong `src/aios_habit/workspace_chat_app.py` (phụ thuộc T004)
- [x] T015 [US2] Hỏi lại đúng phần thiếu bằng tiếng Việt trong `src/aios_habit/workspace_chat_app.py`
- [x] T016 [US2] Chạy kịch bản 2 trong `specs/015-csv-chart-selector/quickstart.md` và sửa lỗi phát sinh

**Điểm dừng**: Câu chuyện 1 và 2 đều chạy độc lập được

---

## Giai đoạn 5: Câu chuyện 3 — Xem trước, tải về và dùng cho email (Ưu tiên: P3)

**Mục tiêu**: Ảnh tải về mở được trên máy văn phòng, có tem truy vết và dùng chung được cho email cảnh báo

**Kiểm thử độc lập**: Từ ảnh đang xem, tải về một tệp mở được, tem đọc được đầy đủ

- [x] T017 [P] [US3] Kiểm thử tải về và tem truy vết trong `tests/test_csv_chart_selector_ui.py`
- [x] T018 [US3] Nối ảnh xem trước sang email cảnh báo trong `src/aios_habit/production_prediction/alert_mailer.py`, không vẽ lại (phụ thuộc T005)
- [x] T019 [US3] Chạy kịch bản 3 trong `specs/015-csv-chart-selector/quickstart.md` và sửa lỗi phát sinh

**Điểm dừng**: Mọi câu chuyện đều chạy độc lập được

---

## Giai đoạn cuối: Hoàn thiện và kiểm tra chéo

**Mục đích**: Quét ngôn ngữ, chạy cổng chất lượng và bàn giao

- [x] T020 [P] Quét mặt chữ tiếng Việt toàn bộ phần mới sửa bằng `scripts/check_user_facing_vietnamese.py` và `scripts/check_docs.py`
- [x] T021 Chạy đủ cổng `compileall`, `pytest -q`, `cli audit` đạt `PASS` và `import aios_habit.workspace_chat_app`
- [x] T022 Cập nhật trạng thái và rủi ro còn lại vào `PROJECT_HANDOVER.md` nếu hành vi thay đổi
- [x] T023 Dọn tệp tạm trong `C:\Users\TVN183660\AppData\Local\Temp\opencode\manifest_iris.py` và kiểm tra `git status --short` không dính dữ liệu thật

---

## Phụ thuộc và thứ tự chạy

### Phụ thuộc giai đoạn

- **Chuẩn bị (Giai đoạn 1)**: Không phụ thuộc, làm ngay được
- **Nền tảng (Giai đoạn 2)**: Phụ thuộc chuẩn bị xong, CHẶN mọi câu chuyện
- **Câu chuyện (Giai đoạn 3+)**: Phụ thuộc nền tảng xong
  - Làm lần lượt theo ưu tiên P1 → P2 → P3, hoặc song song nếu đủ người
- **Hoàn thiện (Giai đoạn cuối)**: Phụ thuộc các câu chuyện mong muốn xong

### Phụ thuộc câu chuyện

- **Câu chuyện 1 (P1)**: Làm sau nền tảng, không phụ thuộc câu chuyện khác
- **Câu chuyện 2 (P2)**: Làm sau nền tảng, kiểm thử độc lập được dù tái dùng hàm chung của US1
- **Câu chuyện 3 (P3)**: Làm sau nền tảng, nên làm sau US1 để tái dùng ảnh xem trước

### Trong từng câu chuyện

- Kiểm thử viết trước và THẤT BẠI trước khi cài đặt
- Hàm dựng chung trước, giao diện sau
- Cài đặt lõi trước, nối tích hợp sau
- Xong một câu chuyện mới sang ưu tiên tiếp theo

### Cơ hội chạy song song

- Mọi việc gắn [P] trong cùng giai đoạn chạy song song được
- Xong nền tảng thì US1, US2, US3 làm song song được nếu đủ người
- Hai tệp kiểm thử US1 chạy song song được

---

## Ví dụ chạy song song: Câu chuyện 1

```bash
# Chạy 2 kiểm thử của câu chuyện 1 cùng lúc:
Task: "Kiểm thử hợp đồng chọn và vẽ 3 loại trong tests/test_csv_chart_selector.py"
Task: "Kiểm thử giao diện các trạng thái trong tests/test_csv_chart_selector_ui.py"
```

---

## Chiến lược triển khai

### MVP trước (chỉ câu chuyện 1)

1. Xong chuẩn bị + nền tảng
2. Xong câu chuyện 1
3. **DỪNG và KIỂM CHỨNG**: Chạy độc lập câu chuyện 1 theo kịch bản 1
4. Demo ngày 23/09 nếu đạt

### Giao dần

1. Xong chuẩn bị + nền tảng là có móng
2. Thêm câu chuyện 1, kiểm thử độc lập, demo (MVP)
3. Thêm câu chuyện 2, kiểm thử độc lập, demo
4. Thêm câu chuyện 3, kiểm thử độc lập, demo
5. Mỗi câu chuyện thêm giá trị mà không làm hỏng câu chuyện trước

---

## Ghi chú

- Việc [P] là khác tệp, không phụ thuộc nhau
- Nhãn [US1], [US2], [US3] giúp truy vết đúng câu chuyện
- Mỗi câu chuyện hoàn thành và kiểm thử độc lập được
- Kiểm thử thất bại trước khi cài đặt
- Dừng ở mọi điểm dừng để kiểm chứng độc lập
- Tránh: việc mơ hồ, xung đột cùng tệp, phụ thuộc chéo làm mất độc lập
