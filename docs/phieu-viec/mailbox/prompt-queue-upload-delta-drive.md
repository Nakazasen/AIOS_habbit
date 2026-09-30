# Vé UPLOAD-DELTA-DRIVE — Đẩy 2 gói delta lên Drive cho PC0575 tải về merge

## Bối cảnh
2 gói delta đang nằm trên ổ C máy nhà; PC0575 (máy công ty) không lấy qua LAN/USB được.
User đang ở máy công ty, yêu cầu bridge qua Google Drive. Đẩy 2 file zip lên thư mục
AIOS_Data trên Drive (nơi đã có file JSONL Điều chỉnh), đặt quyền xem cho ai có link.

## Việc cần làm
1. Verify SHA-256 2 file local khớp ghim dưới đây. Lệch → DỪNG, mailbox `cho-muse`.
2. Upload lên thư mục AIOS_Data trên Drive:
   - `C:\AIOS_staging_262b\gpu-262b-delta-20261001.zip` — 20.867.536 byte,
     SHA-256 `5bd7c56d93b50d8415320ce37295d7be503ace99b912e375055025b844099a85`
   - `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` — 74.065.213 byte,
     SHA-256 `31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3`
3. Đặt quyền chia sẻ: bất kỳ ai có link = Người xem (như tiền lệ file JSONL Điều chỉnh).
4. Verify độc lập: tải ẩn danh (không cookie) qua
   `https://drive.usercontent.google.com/download?id=<FILE_ID>&export=download&confirm=t`,
   kiểm tra đủ byte + SHA-256 khớp ghim. Lệch → upload lại, không báo xong.
5. KHÔNG xóa bản local trên ổ C.

## Tiêu chí ĐẠT
- Báo cáo `docs/phieu-viec/ket-qua/upload-delta-drive.md`: 2 link Drive + xác nhận
  verify ẩn danh (đủ byte, SHA khớp từng file).
- 2 file local còn nguyên.

## Cấm
- Không đụng production, staging, ổ D. Không merge `main`.
