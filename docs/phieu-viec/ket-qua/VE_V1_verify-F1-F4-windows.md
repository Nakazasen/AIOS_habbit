# Báo cáo Vé V1 — xác minh F1–F4 trên Windows

Ngày kiểm tra: 2026-09-28, giờ +0700  
Máy: `h410asrock`  
Hệ điều hành: Microsoft Windows 10 Pro, phiên bản `10.0.18363`  
Python: `3.11.14`; `pytest 8.4.2`; `openpyxl 3.1.5`; `xlrd 2.0.2`  
Nhánh: `phieu-viec/rag-fix1`

## Mã nguồn được kiểm tra

- Mã nguồn của Vé V1: `c6aa0839a0f727c7edd6e507d1da423130936e7e`.
- Khi chạy bộ kiểm tra manifest, `HEAD` là `8b68109621c7651bce1f6cc31d2fb19cbb4c9b26`.
- Khi chạy bộ kiểm tra F1/F4, `HEAD` là `de11b64767b2f7da949c4b7e16fa0ec0eba4e4b0`.
- So với mã nguồn Vé V1, các commit tiến độ ở giữa chỉ sửa `docs/phieu-viec/mailbox/trang-thai.md`; không đổi mã hoặc tệp kiểm tra.

## Môi trường và cách chạy

Dùng môi trường ảo riêng trên ổ C, đặt thư mục tạm trên C. Không cài dự án vào môi trường và không sửa mã. Lần thu thập đầu của bộ kiểm tra F1/F4 dừng vì thiếu `openpyxl`; đã cài `openpyxl 3.1.5` vào môi trường ảo rồi chạy lại.

Bộ kiểm tra manifest:

```text
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp uv run --no-project --python C:/tmp/omp-ve-v1-py311/Scripts/python.exe pytest -p no:cacheprovider tests/test_rag_v2_ingest_manifest.py -q
```

Bộ kiểm tra F1/F4, dùng đúng hai tệp để kiểm tra 26 bài theo Vé V1:

```text
PYTHONDONTWRITEBYTECODE=1 TEMP=C:/tmp TMP=C:/tmp TMPDIR=C:/tmp uv run --no-project --python C:/tmp/omp-ve-v1-py311/Scripts/python.exe pytest -p no:cacheprovider tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q
```

## Kết quả

| Phần kiểm tra | Kết quả |
|---|---|
| Sổ chống trùng (`test_rag_v2_ingest_manifest.py`) | 6 đạt, 0 lỗi (`6 passed`, 0,83 giây) |
| F1 — lược đồ và ánh xạ (`test_error_cases_f1.py`) | 15 đạt / 15 |
| F4 — bảng mã (`test_error_cases_f4.py`) | 1 đạt / 11; 10 lỗi thiết lập |
| Hai tệp F1/F4 | 16 đạt, 10 lỗi (`16 passed, 10 errors`, 0,97 giây); không có bài kiểm tra báo `failed` |

Mười bài F4 lỗi ở bước chuẩn bị dữ liệu: biến `AIOS_DATA_DIR` chưa được đặt, và thư mục dữ liệu mặc định `/home/hatch/workspace/aios_data` không tồn tại trên máy. Bộ kiểm tra vì vậy không mở bất kỳ bảng tính nguồn nào. Một lỗi đại diện:

```text
> assert path.exists(), f"source file missing: {path}"
E AssertionError: source file missing: \home\hatch\workspace\aios_data\dieu_tra_loi\Điều chỉnh\Bang ma loi\02XC_自己診断表示一覧表-Iris2020 VN.xls
...
tests\test_error_cases_f4.py:41: AssertionError
```

## So sánh và giới hạn kết luận

Vé ghi kết quả trên máy ảo là 26/26 cho F1+F4. Trên Windows, cả 15 bài F1 đều đạt; trong F4, bài chuẩn hóa mã đạt nhưng 10 bài cần dữ liệu Excel thật không qua được bước chuẩn bị vì thiếu nguồn. Do đó chưa có bằng chứng Windows để xác nhận phần F4 trên dữ liệu thật, và tiêu chí 26/26 của Vé V1 **chưa đạt**.

Không chạy nhúng dữ liệu, áp dụng thay đổi hoặc di chuyển chỉ mục; không ghi chỉ mục. F1 chỉ ghi cơ sở SQLite tạm trong vùng thử của `pytest`; F4 dừng trước khi mở tệp nguồn. Không đưa bảng tính hoặc dữ liệu cục bộ vào Git.

Lệnh `git pull` ban đầu được chạy trong kho mã trên ổ D theo yêu cầu người dùng, trước khi đọc prompt Vé V1; Git đã ghi siêu dữ liệu và cập nhật tệp trong kho mã trên D. Chỉ mục SQLite không bị ghi. Sau đó mọi commit/báo cáo được tạo từ bản sao riêng trên C. Mười hai tệp mã nguồn đã sửa sẵn trong kho mã D được giữ nguyên và không đưa vào commit.

## Kết luận

Đã hoàn tất phần xác minh có thể thực hiện trên máy này. Kết quả chờ duyệt, không phải `PASS`; không tự mở Vé P1. Muốn kiểm tra đủ F4 cần có các bảng tính nguồn được phép dùng và đặt đúng biến môi trường `AIOS_DATA_DIR`, sau đó chạy lại bộ kiểm tra F1/F4.
