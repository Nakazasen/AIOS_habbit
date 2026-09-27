# Báo cáo Vé V1.4 — tải zip Drive đường mới và chạy nốt 10 test F4 trên Windows

## Kết quả

**ĐẠT.** Đủ 6/6 manifest + 26/26 error_cases (F1 15/15, F4 11/11) trên Windows, 4/4 file khớp kích thước + sha256, không ghi index, mọi thao tác trên ổ C.

## Mã nguồn, máy và môi trường

- Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`.
- Mã nguồn lúc chạy test: `7ea524cc5ae6193c9b173f6570287168043bc4bf`.
- Thời điểm: 2026-09-28 khoảng 04:42–04:47 giờ `+07`.
- Máy: `h410asrock`.
- Hệ điều hành: Microsoft Windows 10 Pro, phiên bản `10.0.18363`, 64-bit.
- Môi trường test trên ổ C: Python `3.11.14`, `pytest 8.4.2`, `openpyxl 3.1.5`, `xlrd 2.0.2` tại `C:/tmp/omp-ve-v1-py311`. Biến tạm `TMP=TEMP=C:/tmp`.
- Công cụ tải riêng trên ổ C: `gdown 6.4.0` tại `C:/tmp/omp-ve-v14-gdown` (venv mới, vì gdown cũ trên máy không có `--fuzzy`; bản 6.4.0 cũng bỏ `--fuzzy` nên tải bằng ID trực tiếp).

## Cách tải zip

- Link trong vé: `https://drive.google.com/uc?id=1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP`.
- Lệnh: `C:/tmp/omp-ve-v14-gdown/Scripts/python.exe -m gdown "https://drive.google.com/uc?id=1jJpYPMgyPPRt2tPmuOuKEb8rWtwxB1eP" -O C:/tmp/aios-data-v14.zip`.
- Kết quả: thành công ngay lần 1, khoảng 14 giây, file `C:/tmp/aios-data-v14.zip` dài `858.190.286` byte. Không cần lần 2, 3.
- Không đổi quyền share của file Drive. Không thử cookie trình duyệt (không cần).
- Giải nén bằng `Expand-Archive` ra `C:/tmp/aios-data-v14`, toàn bộ trên ổ C.
- Lưu ý cấu trúc thật: trong zip gốc chỉ có thư mục `Điều chỉnh`, không có lớp `dieu_tra_loi` như mô tả vé. Để khớp contract của test (`AIOS_DATA_DIR/dieu_tra_loi/Điều chỉnh/...`), đã copy nguyên vẹn sang `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh` (chỉ thêm lớp vỏ thư mục, không đổi nội dung file). Đặt `AIOS_DATA_DIR=C:/tmp/aios-v14-data`.

## Đối chiếu 4 file nguồn

| File | Kích thước (byte) | SHA-256 đo trên máy | Kết quả |
|---|---:|---|---|
| `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls` | 1.278.976 | `031bbe3e447de2f2d5367a8f10fb875df7a3b7ecd5a9d3330860d15b38b20cc4` | Khớp |
| `UWCAシステムエラー(FXXX)概要.xls` | 303.104 | `81c43cd46496d8f0069f7f40806ff6d6a3e9e5d14af26a5cf2d477709b94a458` | Khớp |
| `SCT自動調整エラーコード一覧_140221.xls` | 294.400 | `6fe738d0d7ef00a45f881f9deb2354798aec0f840a2ce60948544164801f7749` | Khớp |
| `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls` | 782.336 | `6c40012e780dbf83caaaeef5d50e9fbfdc5c387136c5b262a84edf2159088195` | Khớp |

Tên file giữ nguyên kể cả ký tự Nhật. Lệch 0 file nên tiếp tục chạy test theo vé.

## Bộ kiểm thử

Chạy với `AIOS_DATA_DIR=C:/tmp/aios-v14-data`, `TMP=TEMP=C:/tmp`, `-p no:cacheprovider`:

| Bộ kiểm thử | Lệnh | Kết quả |
|---|---|---|
| Sổ chống trùng | `pytest tests/test_rag_v2_ingest_manifest.py -q` | 6 đạt, 0 lỗi (`6 passed`, 1,64 giây) |
| F1 + F4 | `pytest tests/test_error_cases_f1.py tests/test_error_cases_f4.py -q` | 26 đạt, 0 lỗi (`26 passed`, 6,87 giây) |
| F1 riêng | `pytest tests/test_error_cases_f1.py -q` | 15 đạt (`15 passed`, 0,62 giây) |
| F4 riêng | `pytest tests/test_error_cases_f4.py -q` | 11 đạt (`11 passed`, 0,43 giây) |

So với VM (F4 11/11 pass trên Linux): Windows nay cũng 11/11, hết 10 lỗi `source file missing` của Vé V1.2 và hết cảnh "không tải được nguồn" của Vé V1.3. Không có test `FAILED`, không sửa code/test để cho qua.

## Cam kết cấm kỵ

- Chỉ đọc + chạy test. Không ghi index, không embed/apply/ingest thật.
- Mọi tải, giải nén, test trên ổ C. Không ghi ổ D.
- Không `git pull` tạo merge, không đụng `main`.
- Không sửa code/test để cho qua; các thay đổi mã có sẵn trong cây làm việc được giữ nguyên, lượt này chỉ thêm báo cáo + trạng thái mailbox.
- Không đưa 4 file xls vào Git (báo cáo chỉ ghi đường dẫn + sha256).
- Không đổi quyền share Drive.

## Kết luận

Vé V1.4 **ĐẠT** tiêu chí: 26/26 error_cases + 6/6 manifest trên Windows, 4 sha256 khớp, không ghi index, làm trên branch riêng. Đủ căn cứ để Muse mở Vé P1 sau verdict. Muse thu hồi quyền anyone-with-link sau khi đọc báo cáo này.
