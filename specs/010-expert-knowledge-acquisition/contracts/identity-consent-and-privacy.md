# Hợp đồng tên ghi nhận, đồng ý và quyền riêng tư

## 1. Tên ghi nhận

Ứng dụng có thể đọc tên tài khoản Windows/OS để điền sẵn, nhưng người dùng được sửa tên hiển thị trước khi ra quyết định. Tên này chỉ phục vụ lịch sử trách nhiệm.

Hệ thống phải nói rõ:

- Tên ghi nhận không phải danh tính đã xác minh.
- Tên ghi nhận không cấp hoặc từ chối quyền.
- Bất kỳ người nào mở được thư viện dùng chung đều có thể phỏng vấn, xác nhận, đưa vào thư viện và thu hồi.
- Mã máy và thời điểm chỉ hỗ trợ truy vết, không chứng minh chắc chắn ai đã thao tác.

Goal 010 không có tài khoản ứng dụng, hồ sơ chuyên gia, vai trò, phạm vi cấp quyền, quản trị viên hoặc chế độ nhiều người dùng phải bật/tắt.

## 2. Quyết định có trách nhiệm

Mọi quyết định `confirm`, `reject`, `request_change` hoặc `revoke` phải lưu:

- Đúng mã kiểm tra và phiên bản nội dung.
- Tên người quyết định.
- Thời điểm do hệ thống tự ghi.
- Mức tự tin: thấp, vừa hoặc cao.
- Lý do/căn cứ.
- Các nguồn người dùng cho biết đã kiểm tra.
- Xác nhận “Tôi đã kiểm tra nội dung và chịu trách nhiệm về quyết định này.”

Thiếu trường bắt buộc thì chưa ghi quyết định. Nếu nội dung thay đổi sau khi mở form, yêu cầu người dùng xem và xác nhận lại bản mới.

## 3. Đồng ý xử lý âm thanh

Trước khi ghi hoặc chép lời, giao diện giải thích ngắn gọn dữ liệu nào được tạo, lưu ở đâu và cách dừng. Người dùng có thể từ chối và tiếp tục bằng văn bản.

Khi rút đồng ý:

- Dừng xử lý âm thanh mới ngay.
- Không xóa dữ liệu cũ một cách âm thầm.
- Hiển thị lựa chọn tiếp tục bằng văn bản và thao tác xóa dữ liệu cục bộ nếu được hỗ trợ.
- Ghi lại thay đổi trạng thái đồng ý mà không lưu nội dung thô vào log.

## 4. Nhãn và tuyến dữ liệu

| Dữ liệu | Nhãn mặc định | Đích được phép |
| --- | --- | --- |
| Audio thô | `local_only` | Vùng phỏng vấn cục bộ |
| Bản chép lời máy | `local_only` | Vùng phỏng vấn cục bộ |
| Bản chép lời đã sửa | `local_only` cho tới khi rút ra bản nháp | Vùng phỏng vấn cục bộ |
| Tiến độ phiên | Siêu dữ liệu cục bộ | DB điều phối, không chứa bản chép lời thô |
| Bản nháp tri thức | Nội bộ | Kho bản nháp, không dùng cho hỏi đáp thường |
| Nội dung đã xác nhận | Theo phân loại của nguồn | Thư viện đã chọn |
| Quyết định và biên nhận | Siêu dữ liệu cục bộ | Lịch sử đã làm sạch |

Không đặt audio, bản chép lời thô, đường dẫn tuyệt đối, secret hoặc traceback vào UI/log thông thường. Không gửi dữ liệu `local_only` sang provider không được chính sách cho phép.

## 5. Hành vi chép lời

- Runtime thật chỉ báo thành công khi bộ máy chép lời thật đã chạy và trả kết quả hợp lệ.
- Mock/fixture chỉ được dùng trong test hoặc chế độ phát triển được nhận diện rõ, không có công tắc trong giao diện thường.
- Nếu bộ máy thật chưa sẵn sàng, giữ dữ liệu cục bộ, giải thích bằng tiếng Việt và đề nghị tiếp tục bằng văn bản.
- Không dùng hội thoại hoặc bản chép lời để fine-tune trong Goal 010.

## 6. Kiểm thử bắt buộc

- Tên OS được điền sẵn, người dùng sửa được và UI không gọi đó là xác thực.
- Quyết định thiếu độ tự tin, căn cứ, nguồn kiểm tra hoặc xác nhận trách nhiệm bị từ chối.
- Nội dung đổi phiên bản giữa lúc xem và xác nhận bị yêu cầu xem lại.
- Ghi/chế biến âm thanh trước đồng ý và sau khi rút đồng ý bị chặn.
- Audio/bản chép lời thô không xuất hiện trong Git, DB hồ sơ, thư viện, log hay payload trái chính sách.
- Bộ máy thật lỗi không rơi về mock rồi báo thành công.
- Restart đọc lại đúng trạng thái đồng ý và không tự đổi từ chối thành đồng ý.
