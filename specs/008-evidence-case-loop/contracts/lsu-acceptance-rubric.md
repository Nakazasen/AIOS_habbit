# Thang chấm tự động Iris LSU

Tệp này khóa cách T011, T022 và T029 tự đưa ra kết luận kỹ thuật. Mỗi kết luận phải kèm `rubric_version`, digest đầu vào, kết quả từng quy tắc và lệnh có thể chạy lại. AI không được đổi ngưỡng trong lúc chấm để lấy `PASS`.

## 1. Trạng thái dùng chung

| Trạng thái | Ý nghĩa |
|---|---|
| `PASS` | Tất cả điều kiện bắt buộc đạt bằng bằng chứng quan sát được |
| `PASS_WITH_WARNING` | An toàn để tiếp tục ở chế độ đọc-only nhưng còn cảnh báo cần theo dõi |
| `INSUFFICIENT_EVIDENCE` | Chưa đủ dữ liệu để kết luận hiệu quả; vẫn được chạy bóng học hỏi đọc-only |
| `BLOCKED_DATA` | Dữ liệu có lỗi làm kết quả không đáng tin; phải tạo bản sao đã chuẩn hóa hoặc bổ sung nguồn |
| `FAIL_TECHNICAL` | Code, test, migration hoặc hợp đồng sai |

`BLOCKED_DATA` chỉ chặn lượt dữ liệu đang lỗi. Nó không chặn các task kỹ thuật dùng fixture hoặc các nhánh không phụ thuộc.

## 2. Rubric T011 — Cổng dữ liệu

### 2.1. Điều kiện bắt buộc

| Quy tắc | Ngưỡng mặc định | Khi không đạt |
|---|---:|---|
| Đọc được schema CSV/XLSX | 100% tệp đã chọn | `BLOCKED_DATA` và nêu tệp cần xuất lại |
| Có đủ trường khóa bắt buộc | 100% | `BLOCKED_DATA` |
| Thời gian đọc được | ít nhất 99,5% dòng dùng để đánh giá | Cô lập dòng lỗi; dưới ngưỡng thì `BLOCKED_DATA` |
| Đơn vị nhận biết hoặc có ánh xạ | ít nhất 99,5% phép đo dùng | Cô lập dòng lỗi; dưới ngưỡng thì `BLOCKED_DATA` |
| Khóa chính trùng nhưng nội dung mâu thuẫn | 0 | `BLOCKED_DATA` |
| Unit đánh giá nối được lot và JIG | ít nhất 95% | Dưới ngưỡng là `BLOCKED_DATA`; phần không nối được luôn có báo cáo |
| Nhãn từ kết quả cuối cùng | 100% nhãn dùng để chấm | Nhãn không chắc chắn thành `UNKNOWN`, không suy đoán |
| Dữ liệu tương lai lọt vào feature | 0 | `BLOCKED_DATA` |
| Báo cáo không lộ dữ liệu thật | 100% kiểm tra | `FAIL_TECHNICAL` |

### 2.2. Kết luận tự động

- Đạt mọi điều kiện bắt buộc: tự đăng ký snapshot cục bộ và ghi `PASS`.
- Đạt điều kiện bắt buộc nhưng bao phủ chưa đủ 100% hoặc thiếu trường tùy chọn: đăng ký phần hợp lệ với digest riêng và ghi `PASS_WITH_WARNING`.
- Có mâu thuẫn khóa, rò rỉ tương lai hoặc không xác định được cấu trúc: không đăng ký snapshot, ghi `BLOCKED_DATA` cùng danh sách hành động.
- Chương trình không sửa file nguồn. Nếu có thể chuẩn hóa, chỉ tạo bản sao mới dưới vùng cục bộ và lưu biên nhận biến đổi.

## 3. Rubric T022 — Phát lại và mở chạy bóng

### 3.1. Điều kiện kỹ thuật bắt buộc

- Cùng snapshot, code, protocol và seed phải tạo cùng digest kết quả.
- Không có feature nào xảy ra sau `as_of_time`.
- Mỗi Unit chỉ có tối đa một cảnh báo trong một cửa sổ.
- Báo đủ cảnh báo đúng, cảnh báo nhầm, bỏ sót và thời gian cảnh báo sớm.
- Phương án không cảnh báo và EWMA dùng cùng tập đánh giá.
- Báo cáo và giao diện chỉ có tiếng Việt dễ hiểu, không lộ tên model, traceback, đường dẫn hoặc dữ liệu thô.

Thiếu một điều kiện trên là `FAIL_TECHNICAL`; tác tử thực thi sửa code rồi tác tử kiểm toán chạy lại.

### 3.2. Ngưỡng khuyến nghị mặc định

Đây là ngưỡng khởi động sản phẩm cho chế độ chạy bóng đọc-only, không phải tiêu chuẩn chính thức của Kyocera/Iris và không được dùng để quyết định dừng máy hoặc xuất hàng. Khi dữ liệu thật tích lũy đủ, hệ thống tạo một phiên bản rubric mới để so sánh; bản cũ vẫn giữ để quay lại.

Một phương pháp được tự chọn làm ứng viên chạy bóng khi đồng thời:

- tập giữ lại có ít nhất 200 Unit, ít nhất 30 `NG` và ít nhất ba khoảng thời gian;
- tỷ lệ phát hiện `NG` ít nhất 80%;
- cảnh báo nhầm không quá 10 trên 100 Unit;
- trung vị thời gian cảnh báo sớm lớn hơn 0;
- không nhóm JIG/giai đoạn đủ ít nhất 10 `NG` nào có tỷ lệ phát hiện dưới 60%;
- kết quả tốt hơn phương án không cảnh báo về số bỏ sót và không vi phạm điều kiện kỹ thuật.

Hồi quy logistic chỉ được thử khi mỗi lớp có ít nhất `max(30, 10 × số feature hiệu lực)` bản ghi. Không đạt thì model trả `not_applicable`; EWMA và luồng chạy bóng vẫn tiếp tục.

### 3.3. Quyết định tự động không tạo đường cụt

| Kết quả | Chế độ được mở tự động |
|---|---|
| Đạt ngưỡng mặc định | `AUTO_SHADOW` — chạy bóng đọc-only với threshold đã đóng băng |
| Đủ an toàn kỹ thuật nhưng chưa đủ mẫu hoặc chưa đạt ngưỡng hiệu quả | `LEARNING_SHADOW` — chạy bóng đọc-only để thu outcome, luôn ghi rõ chưa đủ bằng chứng |
| Có rò rỉ tương lai, schema sai hoặc kết quả không tái lập | `BLOCKED_DATA` hoặc `FAIL_TECHNICAL`; không chạy trên lô đó |

Hai chế độ chạy bóng không phát lệnh máy, không đổi thông số, không chặn/xuất hàng và không gửi cảnh báo ra ngoài ứng dụng. Người dùng có thể tắt ngay và quay lại phiên bản rubric trước.

## 4. Rubric T029 — Kiểm toán và tự chữa lỗi

Tác tử kiểm toán phải là một vai trò riêng, không phải tác tử vừa sửa nhóm file đang chấm. Nó được tự kết luận cổng kỹ thuật theo bằng chứng lệnh thật.

1. Chạy đủ lệnh kiểm tra khóa trong `tasks.md` và smoke trình duyệt.
2. Với mỗi lỗi do thay đổi của đợt này, tạo phiếu lỗi có lệnh tái hiện, file nghi ngờ và tiêu chí sửa.
3. Giao lại cho tác tử thực thi sửa; chạy test tập trung rồi chạy lại cổng liên quan.
4. Tối đa hai vòng sửa cho cùng một nguyên nhân. Không xóa test, hạ assertion, đổi rubric hoặc miễn trừ để lấy `PASS`.
5. Lỗi nền có trước vẫn phải ghi riêng và chứng minh bằng lệnh tái hiện; nó không được che lỗi mới.
6. Nếu còn nguy cơ mất/rò dữ liệu, migration không phục hồi hoặc có thay đổi ngoài phạm vi, kết luận `FAIL_TECHNICAL` và dừng ghi.
7. Khi mọi cổng kỹ thuật đạt, tác tử kiểm toán tự đánh dấu T029 và trạng thái `TECHNICAL_COMPLETE`.

## 5. Điều duy nhất AI không tự làm

AI không được phát lệnh làm thay đổi máy móc, PLC, thông số công đoạn, trạng thái chặn/xuất hàng hoặc xóa/ghi đè dữ liệu nguồn. Nếu sau này có nhu cầu đó, phải mở một đặc tả khác có cầu dao phần cứng và quyền vận hành riêng; không nằm trong 29 task này.
