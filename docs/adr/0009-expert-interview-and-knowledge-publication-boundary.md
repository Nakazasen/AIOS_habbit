# ADR-0009: Ranh giới phỏng vấn chuyên gia và xuất bản tri thức

Status: `ACCEPTED_REVISED`
Vai trò chủ sở hữu: Chủ sở hữu dự án / người duyệt kiến trúc / người duyệt quyền riêng tư
Xem xét lần cuối: 2026-09-09
Chu kỳ xem xét: Khi thay đổi nơi lưu dữ liệu thô, cách ghi thư viện dùng chung hoặc mức tin cậy giữa người dùng

## Bối cảnh

Goal 010 đã triển khai một vòng phỏng vấn, rút tri thức và xuất bản vào thư viện. Thiết kế ban đầu giả định môi trường doanh nghiệp có danh tính xác thực, hồ sơ chuyên gia, quyền theo phạm vi và người duyệt tách biệt. Sản phẩm hiện không có hệ tài khoản dùng chung; người dùng có quyền mở cùng thư mục thư viện vốn đã có thể đọc và thay đổi dữ liệu trong thư mục đó. Vì vậy lớp phân quyền trong ứng dụng tạo cảm giác an toàn nhưng không tạo ranh giới bảo mật thực, đồng thời làm luồng cá nhân và nhóm nhỏ khó dùng.

Ranh giới phù hợp hơn là cộng tác trong nhóm tin cậy: danh tính dùng để ghi nhận trách nhiệm, không dùng để cấp quyền. Hệ thống vẫn phải bảo vệ dữ liệu thô, tránh hai lượt ghi đè nhau, giữ lịch sử và phục hồi được khi xuất bản lỗi.

## Động lực quyết định

- Một người dùng có thể dùng chương trình như trợ lý cá nhân mà không đăng nhập hoặc cấu hình quản trị.
- Nhóm nhỏ dùng chung một thư viện mà không cần máy chủ, tài khoản, vai trò hay hỗ trợ IT.
- Mọi quyết định đưa tri thức vào thư viện có người nhận trách nhiệm, thời điểm, căn cứ và mức tự tin.
- Dữ liệu phỏng vấn thô vẫn ở máy cục bộ; thư viện dùng chung chỉ nhận nội dung đã được người dùng xác nhận.
- Ghi đồng thời không làm hỏng thư viện và có thể khôi phục bản trước.
- Giao diện đủ đơn giản để người không học công nghệ thông tin hoàn thành luồng chính.

## Các phương án

### A. Giữ phân quyền theo tài khoản, vai trò và phạm vi

Không chọn cho bản hiện tại. Muốn ranh giới này có ý nghĩa phải có dịch vụ danh tính và nơi lưu tập trung đáng tin cậy. Xây riêng phần đó vượt nhu cầu của trợ lý cá nhân và nhóm tin cậy.

### B. Chỉ một máy được phép ghi thư viện dùng chung

Không chọn. Cách này giảm xung đột nhưng gây khó hiểu, phụ thuộc một máy và không phù hợp cách cộng tác thực tế.

### C. Cộng tác tin cậy, ghi nhận trách nhiệm và ghi an toàn

Chọn. Ai truy cập được thư mục dùng chung đều có thể hỏi, phỏng vấn, xác nhận, xuất bản và thu hồi. Hệ thống không tuyên bố xác minh danh tính hay bảo vệ bí mật giữa những người cùng truy cập thư mục.

## Quyết định

1. **Chọn thư viện**: trên giao diện, người dùng chọn “Thư viện cá nhân” hoặc “Thư viện dùng chung”. Chọn thư viện dùng chung bằng thư mục; đổi qua lại không cần khởi động lại ứng dụng.
2. **Danh tính ghi nhận**: ứng dụng điền sẵn tên tài khoản Windows/OS nhưng cho sửa tên hiển thị. Giá trị này chỉ là thông tin tự khai để truy vết, không phải danh tính đã xác minh và không cấp quyền.
3. **Quyền thao tác**: không có tài khoản, vai trò, quản trị viên hay quyền theo công đoạn trong Goal 010. Người có thể mở thư viện được coi là thành viên của nhóm tin cậy và có thể thực hiện toàn bộ vòng tri thức.
4. **Quyết định nội dung**: khi xác nhận hoặc thu hồi, phải lưu tên người quyết định, thời điểm tự động, mức tự tin `thấp|vừa|cao`, lý do/căn cứ, nguồn đã kiểm tra và xác nhận chịu trách nhiệm. Quyết định gắn với đúng nội dung, mã kiểm tra và phiên bản.
5. **Hội thoại**: có thể bắt đầu trực tiếp từ một chủ đề do người dùng nhập hoặc từ nội dung còn thiếu được gợi ý. Không bắt buộc duyệt khoảng trống, chọn hồ sơ chuyên gia hay cấu hình ngân sách kỹ thuật trước khi hỏi.
6. **Dữ liệu thô**: audio và bản chép lời thô là `local_only`, nằm ngoài Git, `workspace_cases.sqlite` và `library.sqlite`. Chỉ nội dung đã được người dùng xem và xác nhận mới được đưa vào thư viện.
7. **Xuất bản**: `LibraryWriterLease` chỉ là khóa ghi ngắn hạn chống hai tiến trình sửa cùng lúc, không phải quyền. Bất kỳ người dùng nào lấy được khóa trước đều có thể ghi; khi bận, giao diện giải thích và cho thử lại.
8. **An toàn ghi**: sửa trên bản sao cục bộ, kiểm tra nhanh, sao lưu bản dùng chung hiện tại, thay snapshot đã kiểm tra rồi giải phóng khóa. Lỗi không được đánh dấu là đã xuất bản.
9. **Lịch sử**: không xóa quyết định cũ. Sửa, thu hồi hoặc thay thế tạo bản ghi mới và giữ khả năng quay lại bản trước.
10. **Học**: tri thức đã xác nhận được dùng qua truy xuất. Fine-tune không thuộc Goal 010 và không xuất hiện trong luồng người dùng.

## Giao diện tối thiểu

Luồng chính chỉ có bốn chặng: chọn thư viện → phỏng vấn → kiểm tra bản nháp → xác nhận và đưa vào thư viện. Mỗi chặng có một hành động chính. Mã nội bộ, mã băm, câu hỏi nghiệm thu, trạng thái máy, fixture và chi tiết sao lưu không xuất hiện ở bề mặt chính; chỉ đặt trong phần “Chi tiết kỹ thuật” thu gọn khi thật sự cần hỗ trợ.

Màn hình xác nhận chỉ yêu cầu các thông tin có ý nghĩa với người dùng: tên người quyết định, mức tự tin, căn cứ, nguồn đã kiểm tra và ô xác nhận trách nhiệm. Ngày giờ do hệ thống tự điền.

## Rủi ro được chấp nhận

- Người có quyền truy cập thư mục dùng chung có thể thêm, sửa ngoài ứng dụng, thu hồi hoặc xóa dữ liệu.
- Tên người quyết định có thể được khai không đúng.
- Mô hình này không bảo vệ bí mật khác nhau giữa các thành viên cùng dùng thư viện.

Giao diện và tài liệu phải nói rõ đây là lịch sử trách nhiệm, không phải cơ chế xác thực. Khi tương lai cần quyền truy cập khác nhau, tạo Goal riêng cho dịch vụ tập trung hoặc tách thư viện; không mở rộng Goal 010 bằng một lớp phân quyền nửa vời.

## Hệ quả

### Tích cực

- Dùng cá nhân ngay, không cần đăng nhập hay cấu hình.
- Nhóm nhỏ cùng ghi được, không phụ thuộc một máy quản lý.
- Ít màn hình và ít khái niệm kỹ thuật hơn.
- Vẫn giữ được nguồn, trách nhiệm, lịch sử và phục hồi dữ liệu.

### Đánh đổi

- Không ngăn được thành viên trong nhóm tin cậy cố tình mượn tên hoặc sửa file trực tiếp.
- Không phù hợp môi trường cần phân quyền bảo mật chính thức.
- Cần sửa phần triển khai cũ đang dùng hồ sơ chuyên gia/quyền theo phạm vi và giao diện nhiều bước.

## Không thuộc phạm vi

- Đăng nhập, mật khẩu, SSO, vai trò, quản trị viên và quyền theo tài liệu/công đoạn.
- Cấu hình quyền Windows/NAS hoặc yêu cầu IT cấp quyền.
- Máy chủ trung tâm, cơ sở dữ liệu phân tán hoặc nhiều người sửa cùng một giao dịch.
- Hệ quản trị tài liệu, công cụ họp trực tuyến hoặc pipeline fine-tune.

## Bằng chứng và liên kết

- [Đặc tả 010](../../specs/010-expert-knowledge-acquisition/spec.md)
- [Kế hoạch 010](../../specs/010-expert-knowledge-acquisition/plan.md)
- [Hợp đồng danh tính, đồng ý và quyền riêng tư](../../specs/010-expert-knowledge-acquisition/contracts/identity-consent-and-privacy.md)
- [Hợp đồng vòng tri thức](../../specs/010-expert-knowledge-acquisition/contracts/expert-knowledge-loop.md)
