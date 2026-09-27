# Báo cáo Vé V1.3 — tải 4 file nguồn từ Drive và chạy kiểm thử F4 trên Windows

## Kết quả

**CHƯA ĐẠT — không tải được nguồn.** Đã dừng theo bước 6 của vé sau ba lần gọi tải không thành công. Không thể đối chiếu bốn tệp và không chạy các bộ kiểm thử của vé; đây không phải kết quả kiểm thử lỗi mã nguồn.

## Mã nguồn, máy và môi trường

- Nhánh: `phieu-viec/rag-fix1`.
- Mã nguồn tại thời điểm thử tải: `57b904359555aa7823b0b36705bf50095975247d`.
- Thời điểm: 2026-09-28, khoảng 04:19–04:24 giờ `+07`.
- Máy: `h410asrock`.
- Hệ điều hành: Microsoft Windows 10 Pro, phiên bản `10.0.18363`, 64-bit.
- Môi trường kiểm thử có sẵn trên ổ C: Python `3.11.14`, `pytest 8.4.2`, `openpyxl 3.1.5`, `xlrd 2.0.2` tại `C:/tmp/omp-ve-v1-py311`.
- Thư mục tạm: `C:/tmp`; ổ C còn khoảng 4,7 GB tại thời điểm kiểm tra.

## Kết quả lấy gói từ Drive

Liên kết trong vé trỏ tới gói nén dung lượng khoảng 858 MB. Không có lần nào tạo được tệp `C:/tmp/aios-data-v13.zip`.

| Lần gọi | Cách thử | Kết quả |
|---|---|---|
| 1/3 | `gdown` với tùy chọn `--fuzzy` | Phiên bản `gdown` đang dùng không nhận tùy chọn này; lệnh dừng trước khi tải. |
| 2/3 | `gdown` với liên kết Drive trực tiếp | Không lấy được liên kết công khai; `gdown` báo tệp không cho phép truy cập công khai. |
| 3/3 | `gdown` dùng cookie Chrome cục bộ | Windows chặn ứng dụng khác đọc cơ sở dữ liệu cookie Chrome; không tải được. |

Thử mở liên kết trong trình duyệt điều khiển cũng không thực hiện được vì tiện ích nối phiên Chrome chưa kết nối. Không đổi quyền chia sẻ, không dùng nguồn thay thế, không tạo thư mục giải nén.

## Đối chiếu bốn tệp nguồn

Không tải được gói nên không có tệp thực tế để so kích thước hoặc SHA-256. Các giá trị dưới đây là giá trị yêu cầu trong vé, không phải kết quả đo trên máy.

| Tệp nguồn | Kích thước yêu cầu (byte) | SHA-256 yêu cầu | Kết quả trên máy |
|---|---:|---|---|
| `Bang ma loi/02XC_自己診断表示一覧表-Iris2020 VN.xls` | 1.278.976 | `031bbe3e447de2f2d5367a8f10fb875df7a3b7ecd5a9d3330860d15b38b20cc4` | Không có tệp; chưa đối chiếu. |
| `UWCAシステムエラー(FXXX)概要.xls` | 303.104 | `81c43cd46496d8f0069f7f40806ff6d6a3e9e5d14af26a5cf2d477709b94a458` | Không có tệp; chưa đối chiếu. |
| `SCT自動調整エラーコード一覧_140221.xls` | 294.400 | `6fe738d0d7ef00a45f881f9deb2354798aec0f840a2ce60948544164801f7749` | Không có tệp; chưa đối chiếu. |
| `Bang ma loi/02XC_機能定義書_JAM一覧 (1).xls` | 782.336 | `6c40012e780dbf83caaaeef5d50e9fbfdc5c387136c5b262a84edf2159088195` | Không có tệp; chưa đối chiếu. |

## Bộ kiểm thử

| Bộ kiểm thử | Kết quả |
|---|---|
| `tests/test_rag_v2_ingest_manifest.py` | Không chạy. Vé yêu cầu dừng khi không tải được gói sau ba lần thử. |
| `tests/test_error_cases_f1.py` và `tests/test_error_cases_f4.py` | Không chạy. Thiếu bốn tệp nguồn; không thể xác nhận tiêu chí 26/26. |

Không ghi chỉ mục, không nhúng hoặc nhập dữ liệu thật. Không ghi dữ liệu nguồn lên ổ D và không đưa bảng tính vào Git. Các thay đổi mã và kiểm thử đã có sẵn trước khi bắt đầu được giữ nguyên; lượt này không sửa mã hoặc kiểm thử.

## Kết luận

Vé V1.3 **chưa đạt do không tải được nguồn**, không phải do test báo lỗi. Dừng tại đây theo vé và chờ đường tải có quyền truy cập hoặc phiên trình duyệt đã đăng nhập hoạt động. Chưa đủ căn cứ mở Vé P1.
