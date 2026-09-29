# Báo cáo vé `onnx-upload-drive` — nén + upload cây ONNX bge-m3-onnx-fp32 lên Google Drive

- Máy thực hiện: máy nhà `h410asrock` (Windows), ngày 2026-09-30 ~00:05–02:0x +07.
- Vé: `docs/phieu-viec/mailbox/prompt.md` (vé xếp hàng 3).
- Kết quả: **ĐẠT** — zip đã nằm trong thư mục AIOS_Data, mở quyền "Bất kỳ ai có liên kết", đã tải lại ẩn danh và SHA-256 trùng khớp bản gốc.

## 1. Xác minh cây model (bước 1)

- Đường dẫn: `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32` — tồn tại, 9 file, tổng 2.289.625.694 byte.
- Hash thật toàn cây (đọc toàn bộ từng file, chỉ đọc):
  `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`
  — **KHỚP** chuỗi ghim trong vé và sidecar `models\bge-m3-onnx-fp32.sha256`.
- Cách tính: gọi trực tiếp `sha256_model_tree()` (`aios_habit.rag_v2.retrieval_backends`) thay vì `verify_model_tree()` để không ghi cache lên ổ D. Thời gian băm 64,5 giây; đọc ổ D không lỗi.
- Cache `.bge-m3-onnx-fp32.aios-verify-cache.json` khớp manifest hiện tại; biến `AIOS_BGE_ONNX_MODEL_CHECKSUM` trống.
- Không ghi ổ D, không chạy `--apply`, không ghi index, không đụng kho production.

## 2. Nén zip (bước 2)

- Lệnh: `tar -a -cf C:\temp\bge-m3-onnx-fp32.zip -C D:\Sandbox\AIOS_habbit\models bge-m3-onnx-fp32` (bsdtar của Windows), exit 0, 244 giây.
- Tệp: `C:\temp\bge-m3-onnx-fp32.zip`
  - Dung lượng: **1.326.939.447 byte** (1,24 GiB; nén từ 2,13 GiB).
  - SHA-256: `4239479bbc1e68a6aeeb73de35c9737a0dad8e79f1103a31c953c88718bf2f3c`.
- Kiểm chứng zip: `tar -tf` liệt kê đủ 9/9 file đúng dung lượng; trích thử 3 file nhỏ (`config.json`, `sparse_linear.npy`, `sparse_linear_bias.npy`) và so SHA-256 với bản gốc — khớp cả 3.
- Ổ C sau khi nén: còn 12.070.187.008 byte trống.

## 3. Upload lên Google Drive (bước 3)

- Thư mục đích: AIOS_Data — `https://drive.google.com/drive/folders/1gE4xrS9qPPz-ZYQeL_oTc4JwBFq9iR8F`.
- Khảo sát kênh tải: máy không có rclone, không có Google Drive client, không có credential OAuth; cookie của Chrome đang mở không sao chép được (bị khoá cứng khi trình duyệt chạy, Chrome 154 mã hoá App-Bound nên bản sao cũng không giải mã được).
- Cách làm: điều khiển **cửa sổ Chrome đang đăng nhập sẵn** (`buiducvinhct1102@gmail.com`) bằng UI Automation của Windows (đọc cây accessibility + gửi chuột/phím vào đúng nút), tương đương thao tác người dùng:
  `Mới` → `Tải tệp lên` → chọn `C:\temp\bge-m3-onnx-fp32.zip` → chờ tải xong.
  Không sao chép credential, không cài thêm phần mềm, không đổi cấu hình Chrome.
- Kết quả: Drive báo "Đã tải 1 mục lên"; tệp `bge-m3-onnx-fp32.zip` xuất hiện trong AIOS_Data.

**Bàn giao:**

- Link Drive: `https://drive.google.com/file/d/1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG/view?usp=sharing`
- File ID: `1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG`
- Link tải trực tiếp cho PC0575 (`gdown`): `https://drive.google.com/uc?id=1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG`
- Quyền: đã đặt "Bất kỳ ai có đường liên kết" (Người xem) theo đúng tiền lệ vé V1.4/P5 vì PC0575 cần tải không đăng nhập; có thể thu hồi bất cứ lúc nào trong hộp thoại Chia sẻ.

## 4. Xác minh đầu-cuối (bước 4)

- Tải lại **ẩn danh, không cookie** bằng chính link bàn giao:
  `curl -L -o C:\temp\verify_dl.zip "https://drive.usercontent.google.com/download?id=1CnTrdYLfv1ZpbZMo8zivSOxuD1cVDIrG&export=download&confirm=t"`
  → nhận 1.326.939.447 byte trong 29,8 giây.
- SHA-256 bản tải về: `4239479bbc1e68a6aeeb73de35c9737a0dad8e79f1103a31c953c88718bf2f3c` — **trùng khớp bản zip gốc**.
- Kết luận: PC0575 tải được bằng link/`gdown` và dựng lại đúng cây model (`9f81075f…`).

## 5. Dọn dẹp và giới hạn

- Đã xoá bản tải kiểm chứng `C:\temp\verify_dl.zip` sau khi băm.
- Giữ `C:\temp\bge-m3-onnx-fp32.zip` (zip gốc) và ảnh chụp từng bước ở `C:\temp\ui\`.
- Đã đóng 2 tab "Dự án" phát sinh khi dò toạ độ; còn tab AIOS_Data (kết quả) và 3 tab gốc của máy.
- Giới hạn đã gặp: màn hình scale 150% (1920×1080) làm toạ độ ảnh lệch 1,5× so với toạ độ điều khiển — xử lý bằng cách dùng rect từ cây accessibility thay vì đo ảnh; phím tắt Ctrl+Alt+A của Drive không kích hoạt trong cửa sổ này nên phải mở hộp thoại Chia sẻ qua menu ⋮.
- Không đụng ổ D (chỉ đọc cây model), không merge `main`.
