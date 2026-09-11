# Đặc tả: Trợ lý thực thi công việc cho kỹ sư

**Mã tính năng**: `009-agent-harness-adoption`

**Nhánh lập kế hoạch**: `gate1-local-case-sqlite`

**Ngày tạo**: 2026-09-07

**Ngày làm mới**: 2026-09-11

**Trạng thái**: `SPEC_PLAN_TASKS_REFRESHED`

## 0. Hiện trạng kế thừa

AIOS đã có nguồn AI cho Workspace Chat qua `antigravity_bridge.py`, nền Task Pack, kiểm tra báo cáo Agent, đọc tài liệu, hồ sơ vụ việc và xuất sơ đồ. Các phần này chưa tạo thành một trợ lý có thể nhận nhiều việc, tự đọc và sửa trong vùng an toàn, chạy kiểm tra thật rồi trả kết quả dễ hiểu.

Cầu nối AI của Workspace Chat phải được giữ. Goal 009 chỉ thay đường Agent lập trình NVIDIA cũ bằng runtime kế thừa phù hợp; không thay nguồn AI hiện hành và không dựng lại một IDE hay nền tảng đa Agent.

## 1. Mục tiêu

Giúp kỹ sư giao việc bằng tiếng Việt và nhận đầu ra dùng được mà không phải theo dõi từng lệnh hoặc đọc toàn bộ thay đổi mã nguồn. Vòng đầu hỗ trợ bốn việc liên quan:

1. Đọc, tìm và chỉnh sửa file trong vùng làm việc có thể hoàn tác.
2. Tạo hoặc cập nhật nhanh báo cáo lỗi kỹ thuật, kèm bảng và biểu đồ khi dữ liệu nguồn đủ.
3. Đối chiếu tài liệu nền để chỉ ra thiết kế công đoạn chưa hợp lý, phần còn thiếu hoặc mâu thuẫn, rồi đề xuất cải tiến có dẫn nguồn.
4. Sửa mã nguồn và chạy kiểm thử thật trước khi báo hoàn tất.

Người dùng đánh giá kết quả công việc bằng lời giải thích tiếng Việt đời thường. Toàn bộ thay đổi kỹ thuật vẫn có thể mở xem nhưng không phải bước bắt buộc.

## 2. Hành trình người dùng và kiểm thử

### US1 — Tạo báo cáo lỗi kỹ thuật nhanh (P1)

Kỹ sư chọn hồ sơ, log, bảng tính hoặc tài liệu liên quan rồi yêu cầu AIOS tạo hay cập nhật báo cáo lỗi. AIOS tự thu thập phần được phép, tạo file báo cáo có cấu trúc, thêm bảng hoặc biểu đồ phù hợp và ghi rõ căn cứ của từng kết luận.

**Kiểm thử độc lập**: với một bộ dữ liệu giả lập có log, số liệu và mô tả lỗi, hệ thống tạo được báo cáo tiếng Việt, biểu đồ khớp dữ liệu gốc và không bịa kết luận khi thiếu bằng chứng.

**Tiêu chí chấp nhận**:

1. Báo cáo nêu hiện tượng, ảnh hưởng, bằng chứng, giả thuyết, phần chưa chắc chắn và việc nên làm tiếp.
2. Mọi con số trong bảng hoặc biểu đồ truy ngược được tới nguồn và phép tổng hợp.
3. Khi dữ liệu không đủ để vẽ biểu đồ có ý nghĩa, hệ thống nói rõ và dùng bảng hoặc mô tả; không tạo biểu đồ trang trí.
4. Bản nháp được lưu tự động và có thể hoàn tác mà không cần duyệt từng thao tác file.

### US2 — Rà soát và cải tiến thiết kế công đoạn (P1)

Kỹ sư cung cấp SOP, hướng dẫn công việc, tiêu chuẩn, bản vẽ, MOM, báo cáo lỗi và số liệu công đoạn. AIOS đối chiếu các nguồn để chỉ ra chỗ sai, mâu thuẫn, thiếu kiểm soát hoặc khó thực hiện; sau đó tạo bản đề xuất cải tiến.

**Kiểm thử độc lập**: với một bộ tài liệu giả lập có một mâu thuẫn giới hạn, một bước thiếu điểm kiểm tra và một vấn đề chưa đủ bằng chứng, hệ thống phải tìm đúng ba loại vấn đề, trích đúng nguồn và phân biệt sự thật với đề xuất.

**Tiêu chí chấp nhận**:

1. Mỗi nhận xét phải chỉ rõ vị trí tài liệu hoặc bằng chứng làm căn cứ.
2. Kết quả tách rõ: điều tài liệu đang quy định, điểm bất hợp lý, ảnh hưởng có thể xảy ra, đề xuất cải tiến và thông tin cần xác minh thêm.
3. AIOS chỉ tạo bản nháp thiết kế công đoạn; không tự thay tài liệu chính thức, giới hạn sản xuất hay chỉ thị vận hành.
4. Có thể kèm sơ đồ luồng hiện tại và luồng đề xuất bằng khả năng trực quan hóa đã có của AIOS.

### US3 — Sửa lỗi mã nguồn và kiểm thử thật (P2)

Kỹ sư mô tả lỗi hoặc đưa file báo lỗi. Agent tự đọc, tìm, sửa file và chạy các lệnh kiểm thử cho phép trong vùng làm việc tách biệt. Các thao tác nằm trong phạm vi nhiệm vụ được tự động duyệt.

**Kiểm thử độc lập**: Agent sửa một lỗi trong repo giả lập, chạy kiểm thử thất bại, sửa tiếp tới khi đạt, rồi tạo kết quả có thể dùng hoặc hoàn tác mà workspace chính không bị mất thay đổi có trước.

**Tiêu chí chấp nhận**:

1. Agent được đọc và sửa trong vùng nhiệm vụ; bị chặn khi thoát khỏi vùng, đọc bí mật hoặc chạy lệnh nguy hiểm.
2. Kết quả kiểm thử lấy từ lần chạy thực tế, không lấy từ lời tự khai của mô hình.
3. Người dùng thấy bản tóm tắt “đã làm gì, kiểm thử ra sao, file nào bị tác động, còn rủi ro gì” và hai hành động đơn giản “Dùng kết quả” hoặc “Hoàn tác”.
4. Người dùng không bắt buộc xem `diff`, `hunk`, terminal hoặc mã kỹ thuật; phần đó chỉ mở theo nhu cầu.

### US4 — Giao nhiều việc và theo dõi dễ hiểu (P2)

Người dùng có thể giao thêm việc khi một việc khác đang chạy. AIOS xếp hàng và hiển thị trạng thái ngắn gọn: “Đang chờ”, “Đang làm”, “Cần bạn bổ sung”, “Đã xong”, “Chưa đạt kiểm thử” hoặc “Đã hoàn tác”.

**Kiểm thử độc lập**: tạo ba nhiệm vụ thuộc ba loại khác nhau, đóng rồi mở lại ứng dụng, tiếp tục đúng trạng thái và không ghi đè kết quả của nhau.

**Tiêu chí chấp nhận**:

1. Người dùng giao được ít nhất ba nhiệm vụ mà không phải chờ màn hình hiện tại hoàn tất.
2. Trong cùng một workspace chỉ có một nhiệm vụ ghi file tại một thời điểm; các việc còn lại được xếp hàng rõ ràng.
3. Hủy hoặc khởi động lại không làm lặp thao tác đã hoàn tất.
4. Không cần tạo cấu hình kỹ thuật, sửa JSON hoặc chọn từng quyền nhỏ.

## 3. Trường hợp biên bắt buộc

- Tài liệu mâu thuẫn, thiếu trang, scan kém hoặc không có số liệu đủ để vẽ biểu đồ.
- File đích đổi trong lúc Agent đang làm; workspace có thay đổi sẵn của người dùng.
- Đường dẫn Windows có khoảng trắng hoặc tiếng Việt; nội dung UTF-8 không bị lỗi dấu.
- Lệnh dài bị hủy, runtime mất kết nối hoặc ứng dụng khởi động lại.
- Chỉ dẫn độc hại nằm trong tài liệu, bí mật trong môi trường và đường dẫn thoát khỏi vùng nhiệm vụ.
- Nhiều nhiệm vụ cùng muốn sửa một workspace.
- Đề xuất thiết kế công đoạn có thể ảnh hưởng an toàn, chất lượng hoặc tài liệu chính thức.

## 4. Yêu cầu chức năng

- **FR-001**: Giữ nguyên cầu nối AI hiện hành của Workspace Chat; việc thay runtime Agent không được làm mất các nguồn AI đang dùng.
- **FR-002**: Runtime Agent phải được khóa phiên bản và vượt kiểm tra đọc, tìm, tạo file, sửa file, chạy lệnh, tiếp tục phiên và hoàn tác trước khi dùng.
- **FR-003**: Thao tác hợp lệ trong vùng nhiệm vụ được tự động duyệt; thao tác ngoài vùng, bí mật, quyền quản trị, commit, push, merge hoặc deploy bị từ chối ở vòng đầu.
- **FR-004**: Mọi thao tác sửa mã nguồn phải diễn ra trong vùng làm việc tách biệt và có checkpoint để hoàn tác.
- **FR-005**: Báo cáo và đề xuất thiết kế được tự lưu dưới dạng bản nháp; việc ban hành tài liệu chính thức vẫn nằm ngoài vòng đầu.
- **FR-006**: Mọi kết luận về lỗi hoặc thiết kế công đoạn phải gắn nguồn; phần chưa đủ bằng chứng phải được đánh dấu rõ.
- **FR-007**: Biểu đồ chỉ được tạo từ dữ liệu có nguồn và phải giữ thông tin phép tổng hợp; thiếu dữ liệu thì không được bịa biểu đồ.
- **FR-008**: Kiểm thử mã nguồn phải dựa trên kết quả chạy thật và trạng thái file quan sát được.
- **FR-009**: Giao diện mặc định chỉ hiện mục tiêu, tiến độ, kết quả, rủi ro và bước tiếp theo bằng tiếng Việt; chi tiết kỹ thuật được thu gọn.
- **FR-010**: Hệ thống phải nhận nhiều nhiệm vụ, xếp hàng thao tác ghi theo từng workspace và tiếp tục được sau khi mở lại ứng dụng.
- **FR-011**: Không lưu transcript hoặc đầu ra thô vào hồ sơ; chỉ lưu trạng thái, nguồn, tệp đầu ra, kết quả kiểm tra và thông tin đã làm sạch cần để truy vết.
- **FR-012**: Không gửi dữ liệu `local_only` hoặc bí mật tới nguồn AI không được phép.
- **FR-013**: Không dựng editor, terminal, cơ sở dữ liệu phiên, scheduler phân tán hoặc nền tảng đa Agent mới trong vòng đầu.
- **FR-014**: Bản nháp cải tiến công đoạn phải phân biệt rõ quy định hiện tại, phát hiện có bằng chứng, suy luận và đề xuất; không được tự nhận là tài liệu đã phê duyệt.
- **FR-015**: Mọi kết quả phải có hành động hoàn tác dễ hiểu; hoàn tác không được xóa thay đổi có trước của người dùng.

## 5. Thực thể chính

- **Nhiệm vụ Agent**: mục tiêu, loại công việc, nguồn được chọn, vùng file, lệnh cho phép và tiêu chí hoàn thành.
- **Mục hàng đợi**: thứ tự, trạng thái, workspace và khả năng tiếp tục.
- **Bản nháp đầu ra**: báo cáo lỗi, file hỗ trợ, sơ đồ hoặc đề xuất cải tiến công đoạn.
- **Nguồn dẫn chứng**: vị trí tài liệu, số liệu và phép tổng hợp đứng sau một nhận xét hoặc biểu đồ.
- **Kết quả thực thi**: file đã tạo/sửa, kiểm thử đã chạy, trạng thái, rủi ro và checkpoint hoàn tác.

## 6. Tiêu chí thành công đo được

- **SC-001**: Với bộ dữ liệu nghiệm thu, 100% số liệu trên báo cáo và biểu đồ truy ngược được tới nguồn; không có số liệu tự tạo.
- **SC-002**: Với bộ tài liệu công đoạn nghiệm thu, 100% nhận xét được gắn nguồn hoặc đánh dấu rõ là đề xuất/chưa đủ bằng chứng.
- **SC-003**: Người dùng không chuyên có thể giao một nhiệm vụ và tìm được kết quả hoặc nút hoàn tác mà không mở `diff`, terminal hay file JSON.
- **SC-004**: Ba nhiệm vụ liên tiếp được giữ đúng trạng thái qua một lần đóng/mở ứng dụng và không ghi đè nhau.
- **SC-005**: 100% thao tác ngoài vùng, truy cập bí mật và lệnh bị cấm trong bộ kiểm thử an toàn bị chặn.
- **SC-006**: Lỗi mã nguồn giả lập được sửa, kiểm thử thật đạt và hoàn tác thành công mà không làm mất thay đổi có trước.
- **SC-007**: 100% thông báo, lỗi, tiến độ và báo cáo do hệ thống tạo cho người dùng là tiếng Việt dễ hiểu, không lộ traceback hay đường dẫn tuyệt đối.

## 7. Giả định và ranh giới

- Một người dùng cục bộ; Workspace Chat là giao diện chính.
- OpenCode là runtime Agent được thử trước; Cline chỉ được đánh giá nếu OpenCode không đáp ứng vòng đọc–sửa–test–hoàn tác.
- `antigravity_bridge.py` tiếp tục cung cấp tuyến AI cho Workspace Chat và không nằm trong phạm vi loại bỏ.
- Code-OSS có thể được dùng như công cụ kỹ thuật bên ngoài, nhưng extension riêng không phải điều kiện của vòng đầu.
- Báo cáo lỗi và đề xuất thiết kế công đoạn là bản nháp hỗ trợ kỹ sư, không tự trở thành quyết định vận hành hoặc tài liệu quy chuẩn.
