# Báo cáo Vé 0 — Điều tra nhịp rơi

## 1. Nghi phạm chính và loại trừ

**Nghi phạm chính cho nhịp rơi: chi phí SQLite lặp lại ở mỗi mẻ 2 khối, tăng dần khi ghi lên chỉ mục lớn.** Trong `scripts/migrate_vectors_to_onnx.py`, mỗi mẻ mở một kết nối để kiểm tra từng hàng (`apply_migration`, dòng 212–222), rồi `_upsert_batch` mở kết nối thứ hai và ghi dense+sparse trong một giao dịch (dòng 286–323). Đồng hồ thời gian của mẻ chỉ bắt đầu ở dòng 226, nên không tính kết nối và truy vấn kiểm tra trước đó. Với 99.003 khối đang chờ và `batch_size=2`, cấu hình này tương đương khoảng 49.502 giao dịch ghi nếu chạy hết.

| Mốc quan sát | Khối tăng | Nhịp | Trung vị thời gian/mẻ |
|---|---:|---:|---:|
| 16:04–16:14 | 2.400 | 4,000 khối/giây | 0,5 giây |
| 16:14–16:24 | 1.838 | 3,063 khối/giây | 0,6 giây |
| 16:24–16:34 | 1.128 | 1,880 khối/giây | 0,8 giây |
| 16:34–16:44 | 568 | 0,947 khối/giây | 2,1 giây |
| Mốc 16:44:40 đến lần ghi cuối 16:48:24 | 162 | 0,723 khối/giây | 2,2 giây |

So giữa hai khoảng 10 phút đủ mốc (16:04–16:14 và 16:34–16:44), nhịp giảm khoảng **4,2 lần**, trong khi trung vị thời gian/mẻ tăng **4,2 lần**; cỡ mẻ vẫn là 2. Nhật ký ghi 3.064 mẻ thành công, tức 6.128 khối; mẻ kế tiếp gặp lỗi khi mở kết nối ghi ở `_upsert_batch`: `sqlite3.OperationalError: disk I/O error`. Chỉ mục dừng ở 1.750.740.992 byte, so với 1.698.164.736 byte trước khi chạy, tăng 52.576.256 byte (**3,10%**). Mức tăng kích thước tệp không đủ để tự nó giải thích mức giảm nhịp 4,2 lần; không có mẫu theo giờ để tách hiệu ứng kích thước khỏi chi phí truy vấn/ghi lặp lại.

Đối chiếu nghi phạm khác:

- **Thiếu dung lượng đĩa:** không phù hợp với số đo hiện có. Sau lỗi, lúc 16:57 còn 7.995.224.064 byte trống (khoảng 7,45 GiB); lúc 17:05 còn 8.005.554.176 byte. Lỗi I/O vẫn cần điều tra riêng, nhưng không có bằng chứng đĩa đầy.
- **GPU OOM:** không khớp lỗi kết thúc. Vé B ghi nhận tại 16:52 VRAM 2.822/3.072 MiB, còn khoảng 250 MiB; lỗi cuối là lúc mở kết nối SQLite, không phải lỗi CUDA. Kiểm tra GPU trước đó trên 20 khối đạt 2,171 giây ở batch 2, tương đương 25,14 lần nhanh hơn CPU 54,586 giây; các batch đến 20 đều chạy không OOM, với đỉnh 2.833/3.072 MiB. VRAM khi chạy khá sát giới hạn, nhưng không có lỗi OOM trong nhật ký.
- **Quá nhiệt:** chưa có chuỗi cảm biến liên tục trong lúc nhịp giảm nên không thể loại trừ tuyệt đối. Điểm đang chạy được báo lúc 16:52 là 60°C và 1.911 MHz, không cho thấy hạ xung do nhiệt tại thời điểm đó. Sau khi tiến trình dừng, sáu mẫu từ 17:03:06 đến 17:03:56 đều khoảng 50°C, 607 MHz đồ họa, 405 MHz bộ nhớ, 447 MiB VRAM, tải GPU 2% và 11 W; đây là trạng thái rỗi, không đại diện cho giai đoạn giảm tốc.

Sau lỗi, phép `PRAGMA integrity_check` chỉ-đọc trên `library.sqlite` trả về `ok`. Chỉ mục có 133.144 khối, 107.331 khối truy xuất được, 14.456 hàng ONNX dense và 14.456 hàng ONNX sparse; số hàng PyTorch dense/sparse là 340/340. Tiến trình `_g1_gpu_migrate.py` không còn thấy lúc 16:57; kích thước và thời gian sửa chỉ mục vẫn là 1.750.740.992 byte và 16:48:22 tại lần đọc lúc 17:05. Vì vậy mẻ B hiện đã dừng; trạng thái `PID còn sống` trong ghi chú 16:52 không được xác nhận bởi quan sát sau đó.

## 2. Đề xuất cho vé sau

Chưa sửa hay chạy lại gì trong Vé 0. Vé tiếp theo nên kiểm tra nguyên nhân `disk I/O error` ở tầng SQLite/hệ thống tệp trước khi cho phép ghi tiếp, rồi thử một mẫu nhỏ với **mẻ ghi ngoài 10 hoặc 20 khối, giữ batch suy luận GPU bên trong ở 2**. Cách thử này có thể giảm khoảng 5–10 lần số lần mở kết nối kiểm tra, mở kết nối ghi và giao dịch commit so với mẻ 2; số truy vấn kiểm tra từng khối vẫn giữ nguyên. Kết quả giao dịch ngoài lớn hơn hiện chưa được đo nên phải kiểm tra nhịp, tính toàn vẹn và lỗi ghi trên mẫu trước khi cân nhắc chạy phần còn lại. Không tiếp tục dùng bản sao lưu trong Vé 0.

## 3. Nhịp hiện tại và ETA

Nhịp **chưa hồi**: công việc không còn chạy. Đã ghi 6.128/99.003 khối (6,19%); còn 92.875 khối. Lần ghi cuối trong nhật ký là 16:48:24. Mốc GPU và tiến trình lúc 16:57/17:03 đều cho thấy trạng thái dừng, không có lần ghi mới sau đó.

Đo xác minh lại trên `h410asrock` lúc 18:05:18–18:05:48 +0700 bằng `nvidia-smi` qua bốn mẫu: nhiệt độ 51°C; xung đồ họa/bộ nhớ 607/405 MHz; VRAM dùng 500–515 MiB; tải 2–6%; công suất 11,42–11,44 W. Đây là trạng thái rỗi, không đại diện cho lúc giảm tốc. Khi kiểm tra, các tiến trình Python là Graphify, sidecar/MCP và Streamlit; không thấy tiến trình migration. `library.sqlite` vẫn 1.750.740.992 byte, sửa lần cuối 16:48:22; log `_g1_gpu_apply.log` có 243.449 byte, sửa lần cuối 16:48:24. Các mốc này khớp kết luận mẻ đã dừng; không ghi DB.


Nếu được phép chạy lại sau khi xử lý lỗi I/O, ngoại suy theo nhịp cuối quan sát được là 162 khối/224 giây = 0,723 khối/giây; 92.875 khối còn lại cần khoảng **128.420 giây, tức 35,7 giờ**. Đây chỉ là ETA có điều kiện nếu nhịp không giảm thêm; hiện tại không có ETA hoàn tất khi tiến trình đang dừng.
