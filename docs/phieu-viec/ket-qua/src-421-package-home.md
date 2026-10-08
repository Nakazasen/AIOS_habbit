# Báo cáo vé `SRC-421-PACKAGE-HOME` — đóng gói 421 tệp hiện tại ở máy nhà + bản kê vân tay mới

- Vé: `SRC-421-PACKAGE-HOME` (máy nhà `h410asrock`, máy giữ chỉ mục gốc).
- Đầu vào: `docs/phieu-viec/ket-qua/src-package-511-lech.csv` (421 mã lệch băm) + `docs/phieu-viec/ket-qua/ban-ke-511.csv` + `docs/phieu-viec/ket-qua/src-421-provenance-home.md`.
- Nhánh: `phieu-viec/rag-fix1`, không merge `main`.
- Trạng thái vé: **Đóng gói & lập manifest XONG 100%**; bước tải Drive chờ kênh theo đúng chỉ đạo phát hành vé của Muse.

---

## 1. Kết quả định vị tệp hiện tại (Bước 1)

- Đọc danh sách 421 mã từ `docs/phieu-viec/ket-qua/src-package-511-lech.csv`.
- Kho đối chiếu: `local_runs/workspace_chat_rag_v2_canary/materialized_sources`.
- Kết quả kiểm tra sự tồn tại trên đĩa:
  - Số tệp tìm thấy: **421 / 421** (100%).
  - Số tệp thất lạc / không tìm thấy: **0**.
  - Toàn bộ 421 mã đều có tệp `{document_id}.txt` nguyên vẹn trong kho canary máy nhà.

---

## 2. Tính toán băm SHA-256 và lập `manifest-421.csv` (Bước 2)

- Băm SHA-256 byte thô theo đúng hàm `_file_fingerprint` của chương trình.
- Thống kê tệp nguồn:
  - Tổng số tệp: **421**.
  - Tổng dung lượng byte thô: **52.268.967 bytes** (~49,85 MB).
  - Tệp nhỏ nhất: 81 bytes.
  - Tệp lớn nhất: 21.706.319 bytes (`wsc-4fc7eb76bdc2e05c08b3f0f6.txt`, tương ứng bảng tính `Loi KDTPS.xlsx`).
  - Tệp lớn thứ hai: 17.036.873 bytes (`wsc-9c82b1ca2e1898a8d9d03e8b.txt`, tương ứng bảng tính `61C1065D8513_B4_Bow_Skew.xlsm`).
- Lập tệp `manifest-421.csv`:
  - Đã xuất ra: `docs/phieu-viec/ket-qua/manifest-421.csv` (được đưa vào Git để Muse và máy công ty PC0575 kiểm chứng) và đóng kèm ở gốc của gói zip.
  - Cấu trúc các cột:
    - `document_id`: mã tài liệu định danh (`wsc-...`).
    - `duong_dan_tuong_doi`: đường dẫn tương đối trong gói zip (`canary/{document_id}.txt`).
    - `duong_dan_tuong_doi_dich`: đường dẫn tương đối đích trong kho workspace (`local_runs/workspace_chat_rag_v2_canary/materialized_sources/{document_id}.txt`).
    - `kich_thuoc`: dung lượng byte thô của tệp.
    - `sha256`: mã băm SHA-256 byte thô hiện tại.

---

## 3. Đóng gói `src-421-current-home.zip` (Bước 3)

- Tệp gói: `local_runs/src-421-package/src-421-current-home.zip` (lưu tại `local_runs/`, không commit vào Git theo luật an toàn dữ liệu).
- Cấu trúc gói zip:
  - `manifest-421.csv` (nằm ở gốc gói zip).
  - Thư mục `canary/` chứa đầy đủ 421 tệp `{document_id}.txt`.
  - Tổng số mục trong zip: **422** (1 manifest + 421 tệp văn bản).
- Thống kê gói zip:
  - Dung lượng tệp zip: **9.153.022 bytes** (~8,73 MB).
  - Tỉ lệ nén: giảm từ 49,85 MB xuống 8,73 MB (~82,5% độ nén).
  - **Mã băm SHA-256 của tệp zip:** `ae4bdf170ba28b827fb9e899562559da6234b00fb851f76f0cc6c6ed3d1905d5`.
- Kiểm tra toàn vẹn độc lập:
  - Đã chạy script trích xuất đọc ngược từ tệp zip: 421/421 tệp trích xuất có kích thước và SHA-256 khớp 100% với `manifest-421.csv`, số lượng lệch = 0.

---

## 4. Tình trạng tải lên Drive (Bước 4)

- **Trạng thái: Chờ kênh Drive** (đúng như Muse chỉ đạo khi phát hành vé: *"đóng gói + manifest bình thường; phần tải Drive theo kênh user quyết"*).
- Bối cảnh:
  - Máy nhà không có ứng dụng Google Drive for Desktop (không có GoogleDriveFS, không có ổ đĩa mirror G:).
  - Trình duyệt Chrome có profile lưu đăng nhập nhưng user vắng nhà cả ngày, không ai tương tác cấp quyền OAuth cho rclone hay Drive for Desktop; rào cứng cấm mở màn hình chờ bấm và cấm can thiệp trình duyệt gây rủi ro an toàn dữ liệu.
  - Cả 2 gói: Gói 90 tệp (`src-package-511-home-match90.zip`, 430 KB) và Gói 421 tệp (`src-421-current-home.zip`, 8,73 MB) đều đã đóng gói hoàn chỉnh, kiểm băm đầy đủ và lưu sẵn tại máy nhà.
- Đề xuất tiếp nhận:
  - Khi user về nhà hoặc điều phối thiết lập kênh tải, gói 8,73 MB sẽ được đưa lên thư mục `AIOS_Data` ngay lập tức để PC0575 nhận vé `SRC-421-RECEIVE-PC0575`.

---

## 5. Rào cứng đã tuân thủ

- Chỉ đọc và sao chép tệp nguồn từ `local_runs/workspace_chat_rag_v2_canary/materialized_sources`.
- Tuyệt đối không chỉnh sửa tệp nguồn, không ghi hay đụng vào bất kỳ chỉ mục nào ở máy nhà.
- Hai gói 90 và 421 được tách bạch hoàn toàn: gói 90 nằm tại `local_runs/src-package-511/` với `manifest.csv` riêng; gói 421 nằm tại `local_runs/src-421-package/` với `manifest-421.csv` riêng.
- Không merge `main`.
- Tuân thủ quy định an toàn dữ liệu: không commit tệp zip nhị phân vào Git.

---

## 6. Cổng kiểm tra chất lượng (Quality Gates)

- `uv run --no-sync --group dev python -m compileall src tests`: **CLEAN** (0 lỗi cú pháp).
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: **PASS** (`{"errors": [], "status": "PASS", "warnings": []}`).
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: **IMPORT_OK**.
