# Đặc tả: Phỏng vấn chuyên gia và làm giàu tri thức đơn giản

**Mã tính năng**: `010-expert-knowledge-acquisition`
**Ngày tạo**: 2026-09-07
**Sửa theo kiểm toán**: 2026-09-09
**Trạng thái**: `REOPENED_FOR_SIMPLIFICATION`

## 1. Mục tiêu

Giúp một cá nhân hoặc nhóm nhỏ thu nhận kinh nghiệm thực tế bằng hội thoại, kiểm tra lại nội dung rút ra rồi đưa phần đã xác nhận vào thư viện có thể tìm kiếm. Người dùng cá nhân không phải đăng nhập. Nhóm dùng chung không phải cấu hình tài khoản, vai trò, máy quản lý hay quyền Windows/NAS trong ứng dụng.

Hệ thống bảo vệ điều có thể bảo vệ thực sự: dữ liệu phỏng vấn thô ở máy cục bộ, nội dung chưa xác nhận không đi vào thư viện, mỗi quyết định có người nhận trách nhiệm, hai lượt ghi không đè lên nhau và thư viện có bản sao để khôi phục. Tên người quyết định là thông tin tự khai để truy vết, không phải danh tính đã xác minh.

## 2. Hành trình người dùng và kiểm thử

### US1 — Chọn nơi lưu và bắt đầu phỏng vấn (P1)

Người dùng chọn “Thư viện cá nhân” hoặc “Thư viện dùng chung”. Với thư viện dùng chung, người dùng chọn một thư mục. Sau đó họ có thể nhập chủ đề cần hỏi hoặc chọn một nội dung còn thiếu do hệ thống gợi ý rồi bắt đầu ngay.

**Kiểm thử độc lập**: từ màn hình chính, một người chưa biết thuật ngữ kỹ thuật chọn được một trong hai loại thư viện và bắt đầu phỏng vấn mà không đăng nhập, không khởi động lại và không cấu hình quyền.

**Tiêu chí chấp nhận**:

1. Loại thư viện đang dùng và vị trí được giải thích bằng tiếng Việt dễ hiểu.
2. Đổi giữa thư viện cá nhân và dùng chung không cần khởi động lại.
3. Có thể bắt đầu từ chủ đề nhập tay; gợi ý nội dung còn thiếu là tùy chọn, không phải cửa chặn.
4. Không yêu cầu chọn vai trò, phạm vi quyền, hồ sơ chuyên gia, ngân sách lượt hay chủ thể leo thang trên giao diện.

### US2 — Trả lời bằng chữ hoặc giọng nói (P1)

Người dùng trả lời câu hỏi bằng văn bản. Nếu muốn dùng âm thanh, họ đọc giải thích ngắn, đồng ý trước khi ghi hoặc tải tệp, xem lại bản chép lời và sửa các mã máy, con số hoặc đơn vị trước khi tiếp tục.

**Kiểm thử độc lập**: hoàn thành một phiên bằng chữ và một phiên dùng tệp âm thanh giả lập; tạm dừng rồi tiếp tục mà không mất câu trả lời.

**Tiêu chí chấp nhận**:

1. Luôn có lựa chọn dùng văn bản; từ chối hoặc rút đồng ý ghi âm không chặn phiên.
2. Audio và bản chép lời thô chỉ ở vùng `local_only`, không nằm trong mã nguồn, kho điều phối hoặc thư viện tri thức.
3. Người dùng có thể sửa bản chép lời và xác nhận các thông số quan trọng.
4. Phiên có thể tạm dừng, tiếp tục hoặc kết thúc; không gửi lặp cùng một câu trả lời sau sự cố.
5. Giao diện thường không có fixture, tên bộ máy chép lời, phiên bản kỹ thuật hoặc đường dẫn hệ thống.

### US3 — Kiểm tra và chịu trách nhiệm về bản nháp (P1)

Hệ thống tạo bản nháp SOP hoặc bài học từ câu trả lời và nguồn liên quan. Người dùng đọc, sửa, xem nguồn đã dùng và quyết định có đưa nội dung vào thư viện hay không.

**Kiểm thử độc lập**: tạo một bản nháp, sửa nội dung rồi xác nhận hoặc từ chối; bản chưa xác nhận không xuất hiện trong kết quả hỏi đáp thông thường.

**Tiêu chí chấp nhận**:

1. Bản nháp nói rõ đây chưa phải tri thức chính thức.
2. Mỗi kết luận quan trọng có nguồn tham chiếu hoặc được đánh dấu cần kiểm tra.
3. Nội dung mâu thuẫn được chỉ ra để người dùng quyết định; AI không tự chọn bên thắng.
4. Form quyết định ghi: tên người quyết định, thời điểm tự động, mức tự tin `thấp|vừa|cao`, lý do/căn cứ, nguồn đã kiểm tra và xác nhận chịu trách nhiệm.
5. Tên tài khoản Windows/OS được điền sẵn nhưng có thể sửa; giao diện nói rõ đây là tên ghi nhận, không phải xác minh danh tính.

### US4 — Đưa vào thư viện và khôi phục khi lỗi (P1)

Sau khi xác nhận, người dùng đưa bản hiện tại vào thư viện đã chọn. Nếu thư viện đang được người khác cập nhật, ứng dụng giải thích ngắn gọn và cho thử lại. Người dùng không phải chọn máy được quyền ghi hoặc nhập câu hỏi nghiệm thu kỹ thuật.

**Kiểm thử độc lập**: xuất bản vào thư viện cá nhân và dùng chung, thử hai lượt ghi trùng thời điểm, thu hồi một bản và phục hồi sau lỗi mô phỏng.

**Tiêu chí chấp nhận**:

1. Bất kỳ người nào mở được thư viện dùng chung đều có thể ghi; khóa ghi chỉ chống ghi đồng thời.
2. Lượt ghi dùng bản sao cục bộ, kiểm tra nhanh, sao lưu bản dùng chung rồi thay bằng snapshot đã kiểm tra.
3. Lỗi giữa chừng không làm mất bản thư viện sử dụng được gần nhất và không ghi trạng thái “đã đưa vào thư viện”.
4. Nội dung bị thu hồi hoặc thay thế không còn được dùng như bản hiện hành nhưng lịch sử vẫn còn.
5. Mã gói, mã băm, mã biên nhận, kiểm tra SQLite và câu hỏi nghiệm thu chỉ nằm trong chi tiết kỹ thuật thu gọn hoặc nhật ký hỗ trợ.

### US5 — Dùng giao diện đơn giản với người không chuyên (P1)

Người dùng đi theo bốn chặng có tên đời thường: chọn thư viện → phỏng vấn → kiểm tra bản nháp → xác nhận và đưa vào thư viện.

**Kiểm thử độc lập**: một người không học công nghệ thông tin hoàn thành các nhiệm vụ chính từ màn hình ứng dụng mà không cần đọc tài liệu kỹ thuật.

**Tiêu chí chấp nhận**:

1. Mỗi chặng có tối đa một hành động chính nổi bật; hành động phụ được đặt sau hoặc trong phần thu gọn.
2. Không hiển thị token trạng thái nội bộ hoặc từ như `fixture`, `digest`, `claim`, `approved`, `Markdown`, `JSON`, `lease` trên bề mặt chính.
3. Mọi lỗi cho biết điều gì xảy ra và người dùng nên làm gì tiếp theo.
4. Không có màn hình phân quyền chuyên gia trong luồng Goal 010.
5. Màn hình xác nhận và đưa vào thư viện không bắt người dùng nhập thông tin mà hệ thống có thể tự tạo.

## 3. Trường hợp biên bắt buộc

- Hai người cùng thử cập nhật một thư viện; một lượt được ghi, lượt kia nhận hướng dẫn chờ và thử lại.
- Hai người dùng cùng tên hiển thị; lịch sử vẫn lưu thêm máy và thời điểm nhưng không tuyên bố phân biệt danh tính chắc chắn.
- Thư mục dùng chung bị mất kết nối, chỉ đọc, đổi bên ngoài hoặc hết dung lượng.
- Người dùng sửa bản nháp sau khi đã mở form xác nhận; quyết định cũ không áp dụng cho nội dung mới.
- Bản chép lời sai mã máy, con số hoặc đơn vị; nội dung chưa xác nhận không được xuất bản.
- Nguồn mâu thuẫn, thiếu hoặc đã cũ; hệ thống nêu rõ thay vì tự hợp nhất.
- Ứng dụng dừng giữa lúc ghi; thư viện cũ vẫn mở được và lần chạy sau giải thích trạng thái.
- Người khác sửa/xóa trực tiếp file thư viện; hệ thống chỉ có thể phát hiện và cảnh báo, không được hứa ngăn chặn.

## 4. Yêu cầu chức năng

- **FR-001**: Cho phép chọn thư viện cá nhân hoặc thư viện dùng chung ngay trên giao diện và đổi lựa chọn không cần khởi động lại.
- **FR-002**: Cho phép bắt đầu phỏng vấn từ chủ đề nhập tay hoặc từ gợi ý nội dung còn thiếu.
- **FR-003**: Gợi ý nội dung còn thiếu phải kèm căn cứ và luôn là đề xuất; không bắt buộc duyệt đề xuất trước khi phỏng vấn.
- **FR-004**: Phiên phỏng vấn có giới hạn an toàn nội bộ, lưu được tiến độ và hỗ trợ tạm dừng, tiếp tục, bỏ qua hoặc kết thúc.
- **FR-005**: Câu hỏi tiếp theo phải liên quan tới chủ đề hoặc câu trả lời trước, không lặp vô hạn và không dẫn dắt người dùng xác nhận giả thuyết.
- **FR-006**: Văn bản là đường mặc định; âm thanh là tùy chọn và cần đồng ý rõ ràng trước khi xử lý.
- **FR-007**: Audio và bản chép lời thô phải ở vùng `local_only`, ngoài mã nguồn, kho điều phối và thư viện tri thức.
- **FR-008**: Bản chép lời phải cho sửa; mã máy, số và đơn vị phải được người dùng xác nhận trước khi dùng trong nội dung xuất bản.
- **FR-009**: Nội dung AI tạo luôn là bản nháp cho đến khi một người xác nhận.
- **FR-010**: Bản nháp phải giữ nguồn tham chiếu, điều kiện áp dụng, điểm chưa chắc chắn và nội dung mâu thuẫn có ý nghĩa.
- **FR-011**: Quyết định xác nhận, từ chối, yêu cầu sửa hoặc thu hồi phải gắn với đúng nội dung và phiên bản.
- **FR-012**: Mỗi quyết định phải lưu tên ghi nhận, máy, thời điểm, mức tự tin, lý do/căn cứ, nguồn đã kiểm tra và xác nhận chịu trách nhiệm.
- **FR-013**: Tên Windows/OS chỉ dùng điền sẵn và có thể sửa; hệ thống không gọi đó là danh tính đã xác minh.
- **FR-014**: Goal 010 không kiểm tra vai trò, phạm vi quyền, quản trị viên hoặc cấm tự duyệt. Người truy cập được thư viện được coi là thành viên nhóm tin cậy.
- **FR-015**: Chỉ nội dung đã xác nhận và chưa bị thu hồi mới xuất hiện trong truy xuất thông thường.
- **FR-016**: Mọi lượt ghi thư viện phải dùng khóa ghi ngắn hạn, bản sao cục bộ, kiểm tra toàn vẹn, sao lưu và thay snapshot an toàn.
- **FR-017**: Khi khóa ghi đang bận, không tự giành quyền hoặc báo lỗi kỹ thuật; hiển thị lời giải thích và nút thử lại.
- **FR-018**: Thu hồi, thay thế và khôi phục tạo lịch sử mới, không xóa dấu vết quyết định trước.
- **FR-019**: Giao diện chính chỉ dùng tiếng Việt dễ hiểu và bốn chặng của hành trình; chi tiết kỹ thuật được ẩn mặc định.
- **FR-020**: Fixture, tên model/provider, mã băm, mã gói, trạng thái nội bộ và đường dẫn hệ thống không xuất hiện ở luồng người dùng thường.
- **FR-021**: Không âm thầm dùng kết quả chép lời giả hoặc nguồn thay thế rồi gắn nhãn như kết quả thật.
- **FR-022**: Fine-tune nằm ngoài Goal 010 và không xuất hiện trên giao diện người dùng.

## 5. Thực thể chính

- **LibrarySelection**: loại thư viện, tên hiển thị và vị trí đang dùng.
- **RecordedPerson**: tên ghi nhận, tên tài khoản OS gợi ý, máy và thời điểm; không mang quyền.
- **KnowledgeGapCandidate**: nội dung còn thiếu được gợi ý cùng căn cứ; không phải cửa chặn.
- **InterviewSession**: chủ đề, tiến độ và lịch sử hỏi–đáp có thể tiếp tục.
- **TranscriptSegment**: bản chép lời cục bộ, bản sửa và thông số cần xác nhận.
- **KnowledgeArtifactCandidate**: SOP hoặc bài học dạng bản nháp có nội dung, nguồn và phiên bản.
- **DecisionRecord**: quyết định, người nhận trách nhiệm, mức tự tin, căn cứ, nguồn đã kiểm tra và thời điểm.
- **PublicationReceipt**: kết quả sao lưu, ghi, kiểm tra và khôi phục dành cho lịch sử hỗ trợ.

## 6. Tiêu chí thành công đo được

- **SC-001**: Người dùng lần đầu chọn được thư viện và bắt đầu phỏng vấn trong không quá 3 thao tác chính, không cần đăng nhập hoặc đọc hướng dẫn kỹ thuật.
- **SC-002**: 100% quyết định đưa vào hoặc thu hồi tri thức có đủ các trường trách nhiệm của FR-012.
- **SC-003**: 100% audio và bản chép lời thô trong kiểm thử không xuất hiện trong mã nguồn, kho điều phối, thư viện tri thức, nhật ký thường hoặc dữ liệu gửi ra ngoài trái chính sách.
- **SC-004**: 100% nội dung xuất bản có ít nhất một nguồn hoặc đánh dấu rõ phần chưa có căn cứ; 0 bản nháp/chưa xác nhận/đã thu hồi xuất hiện như tri thức hiện hành.
- **SC-005**: Trong kiểm thử hai lượt ghi đồng thời, không có ghi đè âm thầm và thư viện cuối cùng vượt qua kiểm tra toàn vẹn.
- **SC-006**: Với lỗi mô phỏng giữa lúc xuất bản, bản thư viện dùng được gần nhất vẫn mở được và lịch sử không ghi thành công giả.
- **SC-007**: 0 từ kỹ thuật bị cấm ở FR-020 xuất hiện trên bề mặt chính của luồng Goal 010.
- **SC-008**: Một lượt đi bộ giao diện với người không chuyên hoàn thành đủ bốn chặng mà không cần trợ giúp; mọi điểm vướng được ghi thành finding trước khi đóng Goal.

## 7. Giả định và ranh giới

- Thư viện dùng chung dành cho nhóm tin cậy. Quyền truy cập thư mục do môi trường bên ngoài quyết định; ứng dụng không cấu hình quyền Windows/NAS.
- Người dùng hiểu rằng tên ghi nhận có thể sửa và không được xác minh.
- Mỗi thời điểm chỉ một tiến trình ghi một snapshot; nhiều người có thể đọc và chuẩn bị nội dung song song.
- Workspace Chat vẫn là giao diện chính; không tạo ứng dụng hoặc hệ thiết kế giao diện mới.
- Phiên bản đầu ưu tiên văn bản. Âm thanh là tiện ích tùy chọn và có thể tắt khi bộ máy thật chưa sẵn sàng.
- Không xây đăng nhập, vai trò, máy chủ trung tâm, cơ sở dữ liệu phân tán, hệ quản trị tài liệu hoặc fine-tune trong Goal này.
