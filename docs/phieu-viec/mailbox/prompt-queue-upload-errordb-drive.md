# Vé: upload-errordb-drive — đưa DB error_cases lên Drive cho PC0575 demo 10:00 02/10

Lane: [NHÀ] — chạy trên máy nhà h410asrock.
Xếp hàng: chạy SAU vé J1-RT đang verify (tuyệt đối không chen ngang).

## Mục đích
Sáng 02/10 10:00, PC0575 demo tính năng: nhập CSV log jig → vẽ biểu đồ → cảnh báo vượt ngưỡng → mail.
Máy demo cần DB ca lỗi thật qua biến môi trường `AIOS_ERROR_CASES_DB`.
Đưa file lên Drive để máy công ty tải về, khỏi phụ thuộc USB.

## Đầu vào
- File nguồn: `C:/tmp/b0-dict/error_cases_dict.db` (DB B0-DICT, đã dùng verify B5)
- Fingerprint kỳ vọng: SHA-256 `6bd41a8c…2369` — đối chiếu đủ 64 ký tự với báo cáo `docs/phieu-viec/ket-qua/b5.md` TRƯỚC khi upload
- Đích: thư mục AIOS_Data https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F (giữ nguyên tên file `error_cases_dict.db`)

## Các bước
1. Tính SHA-256 file nguồn, đối chiếu fingerprint trong báo cáo B5. Lệch → DỪNG + đặt `cho-muse`, không upload file lạ.
2. Upload lên đúng thư mục Drive đích (dùng luồng đã làm ở vé `onnx-upload-drive`).
3. Tải lại file từ Drive về `C:/tmp/error_cases_dict_recheck.db`, tính SHA — phải khớp 100% mới coi upload thành công.
4. Viết báo cáo `docs/phieu-viec/ket-qua/upload-errordb-drive.md`: tên file, link/file ID trên Drive, SHA-256, dung lượng byte, thời gian upload. Đặt `xong-cho-duyet`.

## Cấm
- Không đụng ổ D, không đụng index production máy nhà.
- Không upload khi SHA không khớp.
