# Hợp đồng vòng phỏng vấn và xuất bản tri thức

## 1. Mục đích

Hợp đồng này khóa hành vi tối thiểu giữa chọn thư viện, phỏng vấn, bản nháp, quyết định và xuất bản. Tên hàm có thể thay đổi; trải nghiệm và an toàn dữ liệu không được thay đổi nếu chưa cập nhật ADR/đặc tả.

## 2. Lệnh nghiệp vụ

### `select_library`

**Đầu vào**: loại `personal|shared` và thư mục nếu dùng chung.
**Đầu ra**: lựa chọn thư viện hiện hành và kết quả kiểm tra khả năng đọc/ghi.
**Từ chối**: vị trí không hợp lệ hoặc không thể mở; giữ nguyên lựa chọn cũ và giải thích cách chọn lại.

### `suggest_knowledge_gaps`

**Đầu vào**: thư viện hiện hành và phạm vi nội dung tùy chọn.
**Đầu ra**: danh sách gợi ý có nguồn/lý do.
**Từ chối**: nguồn đổi giữa lượt hoặc không có căn cứ.
**Lưu ý**: lệnh này là tùy chọn; người dùng có thể nhập chủ đề và bỏ qua hoàn toàn.

### `start_or_resume_interview`

**Đầu vào**: chủ đề, `gap_id` tùy chọn, session ID tùy chọn và khóa chống gửi lặp.
**Đầu ra**: phiên/checkpoint và câu hỏi tiếp theo.
**Từ chối**: chủ đề trống, checkpoint cũ hoặc phiên không còn tồn tại. Không yêu cầu principal, hồ sơ chuyên gia, scope grant hoặc kế hoạch được duyệt.

### `submit_interview_answer`

**Đầu vào**: session/checkpoint, câu trả lời hoặc `unknown|uncertain|skip|pause|stop`, cùng khóa chống gửi lặp.
**Đầu ra**: biên nhận lượt và một trong `ask_followup|request_confirmation|complete|pause`.
**Từ chối**: checkpoint cũ, cùng khóa nhưng payload khác hoặc phiên không hoạt động.

Model chỉ được đề xuất hành động, lý do, câu hỏi và nguồn kích hoạt. Dịch vụ giới hạn số lượt, chặn lặp/dẫn dắt và lưu sự kiện; người dùng không phải cấu hình budget/token hoặc đọc schema.

### `build_artifact_candidate`

**Đầu vào**: các câu trả lời hoặc đoạn chép lời đã xác nhận cùng nguồn tham chiếu.
**Đầu ra**: bản nháp SOP/bài học theo phiên bản, điểm chưa chắc chắn và mâu thuẫn.
**Từ chối**: dùng bản chép lời có thông số quan trọng chưa xác nhận hoặc tạo kết luận không có căn cứ mà không đánh dấu rõ.

Việc tách phát biểu nhỏ, mã kiểm tra và bản đồ nguồn là chi tiết nội bộ. Giao diện trình bày nội dung, nguồn và điểm cần xem lại bằng tiếng Việt đời thường.

### `record_decision`

**Đầu vào**: đúng mã kiểm tra/phiên bản, `confirm|reject|request_change|revoke`, tên ghi nhận, độ tự tin, căn cứ, nguồn đã kiểm tra và xác nhận trách nhiệm.
**Đầu ra**: `DecisionRecord` ghi nối.
**Từ chối**: nội dung đã đổi, thiếu trường trách nhiệm hoặc bản nháp còn mâu thuẫn chưa được người dùng xử lý rõ.

Không kiểm tra vai trò, scope, cấm tự duyệt hoặc danh tính xác thực. Model không được tự gọi lệnh này.

### `publish_artifact`

**Đầu vào**: bản nội dung đã xác nhận, `DecisionRecord` khớp và thư viện hiện hành.
**Thứ tự bắt buộc**:

1. Xác minh quyết định, mã kiểm tra, phiên bản và trạng thái.
2. Chuẩn bị bản sao cục bộ từ thư viện hiện hành.
3. Lấy `LibraryWriterLease` trong thời gian ngắn.
4. Nếu khóa bận, giữ bản nháp và trả hướng dẫn thử lại.
5. Nạp nội dung vào bản sao, chạy kiểm tra nhanh.
6. Sao lưu thư viện dùng chung hiện tại.
7. Thay bằng snapshot đã kiểm tra và ghi biên nhận.
8. Giải phóng khóa trong cả trường hợp thành công lẫn lỗi.

Lỗi ở bất kỳ bước ghi nào không được tạo trạng thái `published`; thư viện dùng được gần nhất phải còn nguyên hoặc được khôi phục.

### `revoke_or_supersede_publication`

**Đầu vào**: bản xuất bản được chọn từ lịch sử, đúng mã kiểm tra, lý do và thông tin trách nhiệm như một quyết định mới.
**Đầu ra**: biên nhận loại bản cũ khỏi tri thức hiện hành và liên kết bản thay thế nếu có.
**Từ chối**: bản không tồn tại, nội dung đích đã đổi hoặc bản thay thế chưa được xác nhận.

## 3. Bất biến bắt buộc

- Model không tự xác nhận, thu hồi hoặc ghi thư viện.
- Không ghi một câu trả lời hai lần với cùng khóa chống lặp.
- Audio và bản chép lời thô không nằm trong DB hồ sơ hoặc thư viện.
- Nội dung chưa xác nhận, mâu thuẫn chưa xử lý hoặc đã thu hồi không đi vào truy xuất thường.
- Không ghi SQL trực tiếp từ model vào `library.sqlite`.
- Quyết định luôn gắn đúng nội dung/phiên bản và giữ lịch sử cũ.
- Khóa ghi chỉ điều phối đồng thời, không được dùng hoặc mô tả như quyền.
- Không yêu cầu người dùng thường nhập mã gói, mã băm hoặc câu hỏi nghiệm thu.

## 4. Hành vi khi lỗi

- Model lỗi: lưu tiến độ, giải thích và cho thử lại hoặc tiếp tục bằng câu hỏi thủ công; không nhân đôi lượt.
- Chép lời lỗi: không dùng mock trong runtime và không báo thành công giả; cho tiếp tục bằng văn bản.
- Thư viện đang bận: giữ nội dung, báo người dùng chờ và có nút thử lại.
- Mất kết nối/hết dung lượng/kiểm tra không đạt: giữ thư viện cũ và bản nháp, không lộ traceback.
- Provider không được phép nhận dữ liệu: dùng tuyến cục bộ được phép hoặc chặn, không âm thầm đổi tuyến.
