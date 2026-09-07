# Mẫu từ điển dữ liệu Iris LSU

Tệp này là hợp đồng mặc định cho T011. Mục tiêu là để chương trình tự kiểm tra và tự tạo ánh xạ ứng viên mà không bắt người dùng phải hiểu cấu trúc dữ liệu hay công thức thống kê. Giá trị thật chỉ được chương trình cục bộ đọc; tác tử dùng mô hình đám mây chỉ nhận kết quả tổng hợp đã làm sạch.

## 1. Ba bảng đầu vào tối thiểu

### 1.1. Thông số linh kiện theo lot

| Trường chuẩn | Bắt buộc | Kiểu | Ý nghĩa dễ hiểu |
|---|---:|---|---|
| `lot_measurement_id` | Tự tạo | chữ | ID bất biến từ digest nguồn và vị trí bản ghi |
| `component_lot_id` | Có | chữ | Mã lô linh kiện |
| `component_code` | Có | chữ | Loại linh kiện hoặc vị trí sử dụng |
| `metric_name` | Có | chữ | Tên thông số được đo |
| `value` | Có | số | Giá trị đo |
| `unit` | Có | chữ | Đơn vị đo |
| `event_time` | Có | thời gian | Lúc phép đo xảy ra |
| `ingested_at` | Không | thời gian | Lúc dữ liệu được nhận |
| `source_digest` | Tự tạo | chữ | Dấu kiểm tra nội dung nguồn |

### 1.2. Liên kết Unit với lot

| Trường chuẩn | Bắt buộc | Kiểu | Ý nghĩa dễ hiểu |
|---|---:|---|---|
| `link_id` | Tự tạo | chữ | ID bất biến từ digest nguồn và vị trí bản ghi |
| `unit_serial` | Có | chữ | Mã Unit hoặc serial |
| `component_lot_id` | Có | chữ | Lô linh kiện đã dùng |
| `component_code` | Có | chữ | Loại linh kiện hoặc vị trí sử dụng |
| `assembly_time` | Có | thời gian | Lúc lắp ráp hoặc thời điểm liên kết có hiệu lực |
| `line_id` | Không | chữ | Mã line |
| `station_id` | Không | chữ | Mã công đoạn |
| `ingested_at` | Không | thời gian | Lúc dữ liệu được nhận |
| `source_digest` | Tự tạo | chữ | Dấu kiểm tra nội dung nguồn |

### 1.3. Kết quả JIG và outcome

| Trường chuẩn | Bắt buộc | Kiểu | Ý nghĩa dễ hiểu |
|---|---:|---|---|
| `jig_result_id` | Tự tạo | chữ | ID bất biến từ digest nguồn và vị trí bản ghi |
| `unit_serial` | Có | chữ | Mã Unit hoặc serial |
| `jig_id` | Có | chữ | Mã JIG |
| `run_id` | Có | chữ | Mã lần đo |
| `event_time` | Có | thời gian | Lúc đo |
| `ingested_at` | Không | thời gian | Lúc dữ liệu được nhận |
| `metric_name` | Có | chữ | Tên thông số JIG |
| `value` | Không | số | Giá trị đo nếu có |
| `unit` | Không | chữ | Đơn vị đo nếu có |
| `jig_version` | Có | chữ | Phiên bản JIG |
| `process_version` | Có | chữ | Phiên bản quy trình |
| `target_label` | Có | mã | Kết quả cuối cùng `OK`, `NG` hoặc `UNKNOWN` |
| `failure_code` | Không | chữ | Mã lỗi do nguồn ghi nhận |
| `retest_outcome` | Không | mã | Kết quả đo lại hoặc sửa chữa |
| `source_digest` | Tự tạo | chữ | Dấu kiểm tra nội dung nguồn |

## 2. Cách chương trình tự tạo ánh xạ

1. Chỉ đọc CSV hoặc XLSX bằng tiến trình cục bộ; không gửi dòng dữ liệu, đường dẫn, serial hoặc nội dung tài liệu cho tác tử đám mây.
2. Chuẩn hóa tên cột về chữ thường, bỏ khoảng trắng thừa và đối chiếu danh sách bí danh cấu hình cục bộ.
3. Chỉ tự nhận ánh xạ khi đúng một cột đạt đồng thời điều kiện tên, kiểu dữ liệu và tỷ lệ giá trị hợp lệ. Nếu nhiều cột cùng phù hợp, trạng thái là `ambiguous` và không tự đoán.
4. Mỗi ánh xạ tự động phải lưu tên trường chuẩn, mã cột nguồn đã băm, kiểu suy ra, tỷ lệ hợp lệ, đơn vị nhận biết, độ tin cậy và lý do. Không lưu giá trị mẫu vào báo cáo chia sẻ.
5. Kết quả `OK`/`NG` chỉ được xác nhận tự động khi đến từ trường kết quả cuối cùng đã ánh xạ, có cùng Unit/lần đo và không mâu thuẫn với retest cuối. Tên tệp, tên thư mục hoặc nội dung AI không được dùng làm nhãn.
6. Kết quả mâu thuẫn, thiếu khóa hoặc không rõ thứ tự retest phải thành `UNKNOWN`; chương trình vẫn xuất danh sách cần bổ sung thay vì chặn toàn bộ việc xây dựng.

## 3. Cấu hình mặc định để không phải hỏi người dùng

- Múi giờ: `Asia/Ho_Chi_Minh`.
- Ưu tiên rủi ro: bỏ sót lỗi nghiêm trọng hơn cảnh báo nhầm.
- Đích đầu tiên: `BOWSKEW_4_BEAM`.
- Khoảng dự báo: kết quả JIG cuối cùng tiếp theo của cùng Unit.
- Chiều rủi ro: hai phía khi tài liệu cục bộ chưa chỉ rõ tăng hay giảm là xấu.
- EWMA: hệ số `0.2`, cửa sổ nền 50 điểm hợp lệ gần nhất, tối thiểu 20 điểm và giới hạn 3 độ lệch chuẩn.
- Nếu có nhiều metric đủ điều kiện, xếp theo tỷ lệ dữ liệu hợp lệ rồi tên chuẩn và chỉ chạy tối đa 20 metric; không dùng outcome để chọn metric. Một Unit có nguy cơ khi ít nhất một metric vượt giới hạn; chỉ lưu tối đa ba yếu tố lệch chuẩn hóa lớn nhất và vẫn tạo tối đa một cảnh báo cho Unit trong cùng cửa sổ.
- Feature được phép: giá trị số của lot/Unit có thời gian không vượt thời điểm dự báo; cấm outcome, retest và dữ liệu đến sau.
- Giới hạn máy: CSV 100 MB, XLSX 25 MB, 200.000 dòng mỗi sheet, lô 10.000 dòng và một luồng tính toán số.

Mọi giá trị mặc định phải có `rubric_version` và digest để có thể đổi hoặc quay lại mà không sửa mã nguồn.

## 4. Báo cáo tổng hợp an toàn

Tiện ích kiểm tra cục bộ chỉ được trả cho tác tử các trường sau:

- loại nguồn và số tệp, không có đường dẫn tuyệt đối;
- mã cột đã băm, trường chuẩn đề xuất, kiểu dữ liệu và đơn vị;
- tổng số dòng, tỷ lệ rỗng, tỷ lệ hợp lệ, số khóa trùng và số khóa mồ côi;
- số `OK`, `NG`, `UNKNOWN` và số mâu thuẫn;
- trạng thái từng quy tắc trong rubric cùng hướng khắc phục tiếng Việt;
- digest của schema và rubric.

Không xuất serial, giá trị đo, nội dung log, tên người, tên sheet nhạy cảm, sơ đồ hoặc dòng dữ liệu thật.

## 5. Nguồn cục bộ cho các đợt sau

Kho tài liệu LSU được đăng ký bằng bí danh `KHO_LSU_CUC_BO`. Gói mã lỗi và sơ đồ Kyocera được đăng ký bằng bí danh `GOI_KYOCERA_CUC_BO`. Đường dẫn thật nằm trong cấu hình cục bộ bị Git bỏ qua. T011 chỉ dùng nguồn LSU; nguồn Kyocera chỉ được dùng khi mở task pack US4, không kéo điều tra line vào lát cắt hiện tại.
