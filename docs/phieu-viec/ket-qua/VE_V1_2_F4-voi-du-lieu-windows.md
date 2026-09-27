# Báo cáo Vé V1.2 — chạy F4 với dữ liệu thật trên Windows

Ngày kiểm tra: 2026-09-28, giờ +0700
Máy: `h410asrock`
Hệ điều hành: Microsoft Windows 10 Pro, phiên bản `10.0.18363`
Python: `3.11.14`; `pytest 8.4.2`; `openpyxl 3.1.5`; `xlrd 2.0.2`
Nhánh: `phieu-viec/rag-fix1`

## Mã nguồn được kiểm tra

- Mã nguồn của Vé V1.2: `65f45b575814f54b5224d49c307f6e90751657ac`.
- Khi chạy các bộ kiểm tra dưới đây, `HEAD` là `e0b77d400a677ca2ec6d184c55f41d70e390853b`.
- Từ mã nguồn Vé V1.2 đến `HEAD` lúc chạy chỉ có 2 commit mailbox (`7dbcbbe`, `e0b77d4`, đều chỉ sửa `docs/phieu-viec/mailbox/trang-thai.md`); không đổi mã hoặc tệp kiểm tra.

## Tìm 4 file nguồn (bước 1–3 của vé)

Đã quét tên chính xác 4 file vé yêu cầu trên `C:/Users`, `D:/`, `C:/tmp` (bỏ `.git`/`.venv`/`Windows`/`Program Files`/`AppData`):

1. `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls`
2. `UWCAシステムエラー(FXXX)概要.xls`
3. `SCT自動調整エラーコード一覧_140221.xls`
4. `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls`

Kết quả: **không tìm thấy file nào**. Không thấy thư mục `aios_data` hay `dieu_tra_loi` ở bất kỳ đâu trên `C:/` và `D:/`.

File gần giống nhất (không dùng vì khác tên và kích thước, vé cấm bịa dữ liệu):

- `D:/Sandbox/AIOS_habbit/Tài liệu của tất cả dòng máy/Iris LSU/02XC_自己診断表示一覧表-VN.xls` (1.279.488 byte; vé cần `...-Iris2020 VN.xls` ~1,2 MB)
- `D:/1.laptopdata/3. kyocera_document/.../6.DP Unit/SCT自動調整エラーコード一覧.xls` (35.840 byte; vé cần `..._140221.xls` ~288 KB)

Vì không có nguồn nên **không đặt `AIOS_DATA_DIR`**, giữ đường dẫn mặc định của test (`/home/hatch/workspace/aios_data`, không tồn tại trên Windows) — đúng kịch bản "không tìm thấy nguồn thì dừng" của vé.

## Môi trường và cách chạy

Dùng lại môi trường Vé V1 trên ổ C (`C:/tmp/omp-ve-v1-py311`, Python 3.11.14), thư mục tạm trên C. Không cài dự án, không sửa mã.

```text
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp <venv-python> pytest -p no:cacheprovider tests/test_rag_v2_ingest_manifest.py -q
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp <venv-python> pytest -p no:cacheprovider tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp <venv-python> pytest -p no:cacheprovider tests/test_error_cases_f1.py -q
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp <venv-python> pytest -p no:cacheprovider tests/test_error_cases_f4.py -q
```

## Kết quả

| Phần kiểm tra | Kết quả |
|---|---|
| Sổ chống trùng (`test_rag_v2_ingest_manifest.py`) | 6 đạt, 0 lỗi (`6 passed`, 0,81 giây) |
| F1 (`test_error_cases_f1.py`) | 15 đạt / 15 |
| F4 (`test_error_cases_f4.py`) | 1 đạt / 11; 10 lỗi thiết lập |
| Hai tệp F1/F4 | 16 đạt, 10 lỗi (`16 passed, 10 errors`); không có bài nào `failed` |

Mười bài F4 lỗi ở fixture `conn` (`assert path.exists()`), chưa mở bất kỳ bảng tính nào. Một lỗi đại diện:

```text
> assert path.exists(), f"source file missing: {path}"
E AssertionError: source file missing: \home\hatch\workspace\aios_data\dieu_tra_loi\Điều chỉnh\Bang ma loi\02XC_自己診断表示一覧表-Iris2020 VN.xls
...
tests\test_error_cases_f4.py:41: AssertionError
```

## So sánh và giới hạn kết luận

- Giống hệt Vé V1 trên Windows (manifest 6/6, F1 15/15, F4 1/11 + 10 lỗi thiết lập). Tiêu chí Vé V1.2 (26/26 error_cases + 6/6 manifest) **chưa đạt**, nguyên nhân duy nhất là thiếu 4 file nguồn trên máy — 0 test `FAILED`, không phải lỗi code.
- Theo đúng bước 6 của vé: dừng, ghi rõ "không tìm thấy nguồn", không bịa dữ liệu, không tải từ nguồn không rõ.

Không chạy nhúng dữ liệu, áp dụng thay đổi hoặc di chuyển chỉ mục; không ghi chỉ mục. Không ghi ổ D (mọi commit từ bản sao trên C). Không đưa bảng tính hoặc dữ liệu cục bộ vào Git.

## Kết luận

Đã hoàn tất phần có thể làm trên máy này. Kết quả chờ duyệt, không phải `PASS`; không tự mở Vé P1. Muốn đạt V1.2 cần Muse cung cấp 4 file nguồn qua đường hợp lệ rồi chạy lại.
