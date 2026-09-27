# Báo cáo Vé 0.3 — Chuyển index sang ổ C và tiếp tục migration GPU

Máy đo: `h410asrock`. Thời gian: 2026-09-27 19:15 đến 2026-09-28 03:01 +0700.

## 1. Dung lượng ổ C và dọn dẹp

- Lúc kiểm tra ban đầu, ổ C còn trống 5,43 GiB. Index 1,75 GB và một backup 1,75 GB cần khoảng 3,5 GB; chỗ đủ nên không dọn file nào.
- Sau các thao tác, ổ C còn trống 9,7 GB. Không có dữ liệu dự án, mã nguồn hay index bị xóa để lấy chỗ.

## 2. Bản index và backup

- Bản gốc: `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- Bản chạy: `C:\AIOS_habit_index_ve03\library.sqlite`.
- Khi sao chép, hai bản cùng kích thước 1.750.740.992 byte và cùng SHA-256 `31E80A9497B3C64F8BFD7EDE0233F6EAF0526F55C78D5D694BFCCDAF69452FDA`; `PRAGMA integrity_check` trên bản C trả `ok`.
- Backup sau mẫu: `C:\AIOS_habit_index_ve03\library.sqlite.bak-20260927-211949-ve03`, `integrity_check=ok`.
- Trước lần resume lại, kiểm tra bản C đạt `integrity_check=ok` và tạo backup mới `C:\AIOS_habit_index_ve03\library.sqlite.bak-20260927-223834-ve03-retry` (1.780.740.096 byte, `integrity_check=ok`). Dry-run xác nhận backup này được chọn; không ghi index.

## 3. Mẫu GPU theo quyết định 20:54

- Mẫu mới nhất: 100/100 khối trong 75,0 giây; nhịp 1,168 khối/giây, tính cả thời gian khởi tạo. Provider hoạt động: `CUDAExecutionProvider`; batch GPU 2, mẻ ghi ngoài 100.
- Sau mẫu, `integrity_check=ok`, dense và sparse cùng có 14.636 vector ONNX; còn 92.695 khối. Không có lỗi I/O. Backup sau mẫu đạt kiểm tra.
- Nhật ký mẫu 19:48 gồm 80 khối thuộc lần thử cũ; không dùng lần thử cũ làm căn cứ nghiệm thu quyết định 20:54.

## 4. Tiếp tục từ checkpoint

- Lần chạy trước đã ghi 3.300/92.695 khối; tiến trình không còn hoạt động khi kiểm tra lại. Nhật ký dừng sau một batch 100 khối và không có lỗi I/O hay traceback.
- Trước khi tiếp tục, dry-run trên bản C báo `pending=89.395`, `no changes written`; GPU CUDA hoạt động và backup retry đạt kiểm tra.
- Lượt resume mới bắt đầu 2026-09-27 22:47:26 +0700 với 107.331 khối truy xuất, 17.936 ONNX đã có, còn 89.395; mẻ ghi ngoài 100, batch GPU 2. ETA đầu lúc 22:46 là 2026-09-28 03:19 +0700; cập nhật lúc 02:54 thành 02:57.
- Hoàn tất 89.395/89.395 trong 15.017,2 giây; thời điểm kết thúc tính từ giờ bắt đầu và thời lượng là khoảng 2026-09-28 02:57:43 +0700. Tốc độ trung bình 5,9528 khối/giây; lượt resume mới có 894 batch, batch cuối ghi 95 khối. Không tìm thấy `I/O error`, `traceback`, `sqlite3.OperationalError` hay `OSError` trong `resume.log`.

## 5. Kết quả nghiệm thu

- Dry-run cuối: `pending=0`, `no changes written`.
- Index C: 2.552.659.968 byte; 107.331/107.331 khối truy xuất có ONNX dense và 107.331/107.331 có ONNX sparse; `PRAGMA integrity_check=ok`.
- Tổng tiến độ theo vé: 6.128 + 92.875 = 99.003/99.003 khối. 92.875 là phần tăng từ mốc dry-run 14.456 vector ONNX lên 107.331; gồm các lần ghi mẫu và resume đã nêu trên.
- Tất cả thao tác SQLite của lần resume này trỏ tới index và backup trên C. File index gốc trên D không bị migration ghi.

## 6. Ghi chú về giới hạn ghi ổ D

Repo làm việc ban đầu nằm trên D. Trước khi nhận ra lệnh cấm áp dụng cả repo, đã chạy `git pull` theo yêu cầu và commit tiến độ `6bbd75f` trong repo gốc; thao tác Git này đã ghi metadata trên D. Index SQLite gốc trên D không bị ghi. Sau khi phát hiện, mọi commit và push tiếp theo chạy từ worktree riêng trên C; các thay đổi mã nguồn có sẵn trong repo gốc được giữ nguyên, không đưa vào commit.

## 7. Kiểm tra phần mềm

- Python 3.11.14; `compileall src tests` thành công; `aios_habit.cli audit` trả `PASS`; import `aios_habit.workspace_chat_app` thành công.
- `pytest -q`: 3.194 đạt, 4 bỏ qua, 14 thất bại, 10 lỗi. Môi trường thử thiếu `xlrd`; đã dùng đúng bản khóa 2.0.2 trong thư mục tạm trên C để chạy hết suite, rồi xóa thư mục đó.
- Các nguyên nhân được in ra: `uv lock --check` báo `uv.lock` cần cập nhật; checksum của nguồn `src-quality-process` không khớp manifest; kiểm thử đóng gói thiếu `torch` và gói Graphify tương thích; 10 lỗi thiếu tệp Excel cục bộ ngoài repo (`/home/hatch/workspace/aios_data/...xls`).
- Không sửa mã nguồn, `uv.lock`, manifest hay dữ liệu kiểm thử để né các lỗi ngoài phạm vi Vé 0.3.
