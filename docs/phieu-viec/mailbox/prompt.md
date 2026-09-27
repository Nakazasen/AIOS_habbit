# Vé V1.2 — chạy nốt 10 test F4 cần dữ liệu thật trên Windows máy nhà

Ngày viết: 2026-09-28 (Muse). Chế độ: Muse ra vé → OMP thực hiện độc lập trên Windows (luật "không vừa đá vừa thổi còi").
Branch: `phieu-viec/rag-fix1`. Không đụng `main`. Hostname: `h410asrock` (Win 10 Pro).

## Bối cảnh / verdict Vé V1

Vé V1 verdict: **CHƯA ĐẠT** (tiêu chí 26/26 error_cases trên Windows).
- Đã đạt: manifest 6/6; F1 15/15; F4 1/11.
- 10 test F4 còn lại ERROR ở fixture setup (`assert path.exists()`): `AIOS_DATA_DIR` chưa đặt và đường dẫn mặc định `/home/hatch/workspace/aios_data` không tồn tại trên máy Windows → chưa mở bất kỳ file nguồn nào. **0 test FAILED** — không phải lỗi code, báo cáo trung thực.
- Trên VM (Linux, có dữ liệu thật) F4 đã pass 11/11 — khoảng trống còn lại duy nhất là đọc file xls thật trên Windows.
- Đã đối chiếu diff độc lập c6aa083...4da41ae: 7 commit chỉ sửa mailbox/báo cáo, không đụng code.

## Mục tiêu

Chạy nốt 10 test F4 với 4 file nguồn thật trên Windows, đạt 26/26 (F1 15 + F4 11).

## 4 file nguồn cần thiết (giữ nguyên tên file, kể cả ký tự tiếng Nhật)

Dưới thư mục `AIOS_DATA_DIR/dieu_tra_loi/Điều chỉnh/`:
1. `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls` (~1,2 MB)
2. `UWCAシステムエラー(FXXX)概要.xls` (~296 KB)
3. `SCT自動調整エラーコード一覧_140221.xls` (~288 KB)
4. `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls` (~764 KB)

## Cách làm

1. Tìm 4 file trên trên máy nhà (chúng đã được upload từ máy này qua Drive ngày 2026-09-27 → nhiều khả năng còn bản gốc; được phép ĐỌC từ ổ D — cấm GHI D vĩnh viễn).
2. Copy 4 file sang ổ C vào thư mục tạm mới, GIỮ NGUYÊN cấu trúc thư mục con (`dieu_tra_loi/Điều chỉnh/Bang ma loi/...`).
3. Đặt biến môi trường `AIOS_DATA_DIR` trỏ tới thư mục CHA của `dieu_tra_loi` (ví dụ `C:\tmp\aios-data-v12`).
4. Dùng lại môi trường Python 3.11.14 + pytest 8.4.2 đã dựng ở Vé V1 (venv trên C, TMP/TEMP trên C; cài thêm openpyxl/xlrd nếu môi trường mới).
5. Chạy:
   - `pytest tests/test_rag_v2_ingest_manifest.py -q` → kỳ vọng 6/6 (đã đạt ở V1, chạy lại cho đủ bộ).
   - `pytest tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q` → kỳ vọng 26/26.
6. Nếu KHÔNG tìm thấy 4 file trên máy nhà: dừng, ghi rõ "không tìm thấy nguồn" trong báo cáo, KHÔNG bịa dữ liệu, không tải từ nguồn không rõ — chờ Muse lo đường khác.

## Cấm kỵ (fail-closed)

- CHỈ đọc + chạy test. Cấm ghi index, cấm embed/apply/ingest thật.
- Cấm vĩnh viễn GHI ổ D (chỉ đọc cứu dữ liệu cũ khi cần).
- Không `git pull` tạo merge — `git fetch` + checkout commit rõ ràng. Không đụng `main`.
- Không sửa code để "cho qua" — fail thì báo nguyên vẹn kèm traceback.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_V1_2_F4-voi-du-lieu-windows.md` gồm:
1. Commit checkout + ngày giờ, OS, Python.
2. Vị trí 4 file nguồn đã dùng (đường dẫn trên C).
3. Kết quả từng suite (6/6 manifest; 26/26 error_cases) với log tóm tắt; bất kỳ khác biệt nào so với kết quả trên VM.

Tiêu chí ĐẠT: 26/26 error_cases + 6/6 manifest pass 100% trên Windows, không ghi index, mọi thao tác trên branch riêng (không đụng main).

## Sau vé này

Vé V1.2 đạt → Muse phát hành Vé P1 "đóng dấu kho thử thành kho thật". Không tự mở P1 trước verdict.
