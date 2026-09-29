# Ticket XẾP HÀNG (chạy sau E2v3): Nén + upload cây ONNX bge-m3-onnx-fp32 lên Google Drive

## Bối cảnh
PC0575 cần cây model ONNX đúng để hoàn thành P5 (app tìm kiếm được).
Cây đúng nằm trên máy nhà. Nhiệm vụ: xác minh → nén → upload lên Drive.
Vé này do user yêu cầu trực tiếp 2026-09-29 ~18:50 +07, ưu tiên ngay sau E2v3.

## Cây model chuẩn (đối chiếu)
- Đường dẫn: `models\bge-m3-onnx-fp32`
- Tree checksum: `9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`
- Sidecar: `models\bge-m3-onnx-fp32.sha256`

## Việc cần làm
1. Kiểm tra thư mục `models\bge-m3-onnx-fp32` tồn tại. Tính tree checksum
   (dùng `resolve_onnx_checksum` trong `aios_habit.rag_v2.bge_onnx_backend`),
   đối chiếu với chuỗi trên. KHÔNG KHỚP → dừng ngay, báo `cho-muse`.
2. Nén thành file zip duy nhất (tên: `bge-m3-onnx-fp32.zip`), đặt ở ổ C
   (VD: `C:\temp\`). CẤM ghi ổ D (ổ D hỏng vật lý).
3. Upload file zip lên Google Drive, thư mục AIOS_Data
   (https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F).
   Dùng cách nào máy có sẵn (Drive client / rclone / trình duyệt).
4. Báo cáo: link Drive + file ID + SHA-256 của file zip + dung lượng.
   Ghi vào `docs/phieu-viec/ket-qua/onnx-upload-drive.md`, commit lên
   branch `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.

## Cấm
- Không đụng index production. Không merge `main`.
- Không xóa cây model gốc sau khi nén.
- Không chạy `--apply` hay ghi index dưới mọi hình thức.
