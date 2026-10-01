# Báo cáo vé `upload-errordb-drive` — chuyển DB ca lỗi lên Drive

- Trạng thái: **Đã upload và xác minh ẩn danh, byte/SHA-256 khớp.**
- Thư mục đích: `AIOS_Data` — `https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`.
- Tệp: `error_cases_dict.db`; file ID: `1ooa5RBApWuOW0L4Ubm5KOEkQwFn6ZEGy`.
- Link xem: `https://drive.google.com/file/d/1ooa5RBApWuOW0L4Ubm5KOEkQwFn6ZEGy/view?usp=sharing`.
- Link tải trực tiếp: `https://drive.usercontent.google.com/download?id=1ooa5RBApWuOW0L4Ubm5KOEkQwFn6ZEGy&export=download&confirm=t`.
- Quyền đang có: **Bất kỳ ai có đường liên kết — Người xem** (xác nhận trong giao diện Drive; không thay đổi quyền).
- Thời điểm ghi nhận hoàn tất: `2026-10-01 21:57 +07` (Drive hiển thị `Đã tải 1 mục lên`; thanh tải trước đó đạt `100/100`).

## Đối chiếu dữ liệu

| Bản | Đường dẫn | Dung lượng | SHA-256 |
|---|---|---:|---|
| Nguồn cục bộ | `C:/tmp/b0-dict/error_cases_dict.db` | 54.480.896 byte | `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` |
| Tải lại ẩn danh từ Drive | `C:/tmp/error_cases_recheck.db` | 54.480.896 byte | `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` |
| Fingerprint ghim trong báo cáo B5 | `docs/phieu-viec/ket-qua/b5.md` | — | `6bd41a8c…2369` |

- Lệnh tải dùng `curl.exe -q -L --silent --show-error --fail --max-time 300`; tùy chọn `-q` bỏ qua cấu hình người dùng, không gửi cookie hay thông tin xác thực. Kết quả: **HTTP 200**, `54.480.896` byte.
- SHA-256 bản nguồn trước và sau upload vẫn trùng fingerprint B5; thời điểm sửa của DB nguồn không đổi. So sánh SHA đầy đủ giữa nguồn, bản tải ẩn danh và fingerprint B5 đều khớp.
- DB và bản tải kiểm chứng ở ngoài repo; **không đưa dữ liệu DB vào Git**. Bản tải kiểm chứng được giữ ở `C:/tmp/error_cases_recheck.db` theo đường dẫn của vé.

## Tiếp theo

Theo chỉ dẫn mới nhất của Muse, sau vé upload này OMP chạy lại `tests/test_j1_rt.py` trên Python 3.11.14 và sáu probe hợp đồng J1-RT; báo cáo J1-RT sẽ cập nhật riêng sau khi có kết quả thực chạy.
