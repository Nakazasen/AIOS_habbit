# Báo cáo chuẩn bị dữ liệu hỏi đáp cho vé nối giao diện

- Ngày làm: 2026-10-05 (máy KDTVN-PC0575, thợ opencode, vé `PREP-WIRE-QA-MAPPING`).
- Nguồn đọc: `docs/phieu-viec/chatgpt-enrichment-fixed/` (88 file: `mom` 15 file, `lsu` 39 file, `dieuchinh` 34 file). Chỉ đọc, không sửa hay xóa file nguồn.
- Đích đã ghi: `docs/phieu-viec/ket-qua/wire-qa-mapping.jsonl` (mỗi dòng 1 cặp).
- Cách ghi mỗi dòng: `{"id": "Qxxxx", "question": "...", "answer": "...", "source": "<tên file fixed>", "category": "MOM|LSU|dieu-tra-loi", "batch": "<số batch>"}`. Trong đó `question` lấy từ dòng Hỏi, `answer` giữ nguyên dòng Đáp (kèm câu nguồn file), `source` là đường dẫn tương đối dạng `mom/batch-01.md`, `category` đổi `mom` thành `MOM`, `lsu` thành `LSU`, `dieuchinh` thành `dieu-tra-loi`, `batch` là số trong tên file, `id` là `Q` kèm số thứ tự đệm 4 chữ số.

## Kết quả đếm

- Tổng số dòng: 3.392.
- Số `id` duy nhất: 3.392 (không trùng).
- Dòng thiếu `question` hay `answer` hay sai khung: 0.
- Sắp xếp theo số thứ tự tăng dần từ `Q0001` tới `Q3406` (có khoảng trống đã ghi rõ bên dưới).
- Số mẻ: 88. Mẻ ít nhất 10 cặp, mẻ nhiều nhất 50 cặp.

## Số cặp theo từng nhóm

- Nhóm `MOM`: 608 cặp (mẻ 01–15).
- Nhóm `LSU`: 1.790 cặp (mẻ 16–54).
- Nhóm `dieu-tra-loi`: 994 cặp (mẻ 55–88).
- Cộng lại: 608 + 1.790 + 994 = 3.392 cặp.

## Ví dụ 3 cặp mẫu

### Ví dụ 1 (nhóm `MOM`)

- `id`: `Q0001`, `source`: `mom/batch-01.md`, `category`: `MOM`, `batch`: `01`.
- Hỏi: Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?
- Đáp: ctrlMode quy định trạng thái truyền thông SLMP giữa Matecon, hệ thống cấp trên MOM và thiết bị. ctrlMode = 0 là chế độ sản xuất tự động, truyền thông được kích hoạt; Matecon gửi lệnh input/output đến ACR/CTU theo chỉ thị từ hệ thống cấp trên. ctrlMode = 1 là chế độ thủ công và chặn truyền thông. Nguồn file: マテコン操作手順書_v001_生産技術 TV.xlsx.

### Ví dụ 2 (nhóm `LSU`)

- `id`: `Q0610`, `source`: `lsu/batch-16.md`, `category`: `LSU`, `batch`: `16`.
- Hỏi: 文件中"人的因素"主要有哪些问题？
- Đáp: 包括对预测和预防不良的重要性认识不足、缺乏故障数据提取与分析技能，以及还没有主动进行故障预测和预防。来源文件：AI_LSU_du_doan_loi.xlsx.

### Ví dụ 3 (nhóm `dieu-tra-loi`)

- `id`: `Q3392`, `source`: `dieuchinh/batch-88.md`, `category`: `dieu-tra-loi`, `batch`: `88`.
- Hỏi: Với C0030, file quy định 3 step xử lý nào?
- Đáp: C0030：Bất thường hệ thống bản mạch FAX; step 1=Reset nguồn điện chính: tắt nguồn điện và nguồn điện chính, sau khi vượt quá 5s thì gắn lại bản mạch FAX rồi bật lại nguồn; step 2=Version up Firmware: cài đặt lại Firmware FAX; step 3=Thay thế bản mạch FAX: thay bản mạch FAX. Nguồn file: Iris2020_Cコール自己診断.xlsx

## Kiểm tra ngẫu nhiên 20 cặp

- Cách kiểm: lấy ngẫu nhiên 20 cặp (mã hạt 20261005), mỗi cặp xem `question` và `answer` có rỗng không, rồi đối chiếu 20 ký tự đầu của hỏi và đáp có nằm trong đúng file nguồn ghi ở trường `source` không.
- Kết quả: 20/20 đạt (hỏi và đáp không rỗng, khớp đúng file nguồn).
- Kiểm thêm: dạng `id` đúng `Q` kèm 4 chữ số 100% (0 sai), số trong trường `batch` khớp tên file nguồn 100% (0 lệch).

## Ghi chú bất thường

- Dải số từ 1 tới 3406 có 14 số trống, chia 2 nhóm có lý do rõ ràng: 639–648 (10 số, do file nhớ đệm hệ thống bị bỏ qua có chủ đích, đã ghi trong đầu file mẻ 16) và 3206, 3207, 3208, 3214 (4 số, trong đó `Q3214` trùng `Q3124` nên bản fixed đã loại để còn 3.392 cặp duy nhất, khớp verdict audit đã duyệt: thô 3.393 trừ 1 trùng).
- Không phát hiện cặp trùng `id` trong bản fixed (quét trực tiếp 3.392 đầu mục, 0 trùng).
- Đáp nhiều ký tự gốc (Nhật, Trung) được giữ nguyên chữ, file ghi theo dạng `UTF-8`, không bịa thêm trường.
- Vé này chỉ xử lý file, không đụng mã nguồn, không đụng nhánh `main`, không ghi đè file của thợ khác.
