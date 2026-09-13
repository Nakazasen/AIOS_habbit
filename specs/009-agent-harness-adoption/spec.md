# Đặc tả: Trợ lý thực thi công việc cho kỹ sư

**Mã tính năng**: `009-agent-harness-adoption`

**Nhánh lập kế hoạch**: `gate1-local-case-sqlite`

**Ngày tạo**: 2026-09-07

**Ngày làm mới**: 2026-09-13

**Trạng thái**: `SPEC_PLAN_TASKS_REFRESHED`

## 0. Hiện trạng kế thừa

Workspace Chat đã hỏi được tài liệu. Goal 009 biến nó thành **trợ lý việc hàng ngày**: nạp log/Excel/Guideline, nói một câu, nhận file hoặc việc đã làm xong — muốn mở lại vào ngày mai.

Cầu nối hỏi đáp hiện có giữ nguyên. Không dựng IDE, không dựng nền tảng Agent.

## 1. Mục tiêu sản phẩm

Người dùng **muốn dùng, dùng lại, dựa vào** Goal 009 như trợ lý hằng ngày (cảm giác Grokbot), trên máy mình, với tài liệu của mình.

Việc vòng đầu — giao bằng tiếng Việt, tự xong, hiện «Đã xong»:

1. Viết báo cáo lỗi từ log, Excel, ảnh hiện trạng đã nạp.
2. So Guideline với bản thiết kế công đoạn: đạt / lệch / thiếu bằng chứng.
3. Sửa lỗi trong mã (vùng tách, test thật, hoàn tác được).
4. Giao thêm việc khi việc trước còn chạy.

Không bắt học UI, không duyệt từng lệnh, không xem `diff` mới được nhận kết quả.

### 1.1 Cấm over-engineer

Khóa cứng. Vi phạm là lệch Goal, không phải «làm kỹ».

- Không framework Agent, app mới, database phiên, scheduler, IDE, terminal nhúng, extension, đa Agent.
- Không màn hình quyền, JSON, schema, tên runtime, worktree, verifier trên UI.
- Không thêm bước «duyệt / ban hành / xác nhận từng mục» trên đường chính.
- Không lớp trừu tượng «phòng sau». Hai cách cùng đạt: **ít code hơn**.
- Hợp đồng trong `contracts/` chỉ cho người viết mã. Người dùng không thấy tên schema.
- Không clone Grok. Cùng cảm giác: nói → việc xong → mở lại được. Khác: local, có nguồn, hoàn tác, không gửi `local_only` trái phép.

### 1.2 Thế nào là hữu dụng

- Một câu + nguồn đã chọn là đủ giao việc.
- Kết quả là file hoặc thay đổi dùng được ngay, không «bản nháp chờ quy trình».
- Thiếu nguồn thì nói thiếu gì, không im và không đẻ form.
- Hôm sau mở lại, việc và file còn đó.
- An toàn **vô hình**: chặn secret, commit, ghi đè SOP gốc — không biến thành bài tập quyền.

## 2. Hành trình người dùng và kiểm thử

### US1 — Tạo báo cáo lỗi kỹ thuật nhanh (P1)

Kỹ sư chọn hồ sơ, log, bảng tính hoặc tài liệu liên quan rồi yêu cầu AIOS tạo hay cập nhật báo cáo lỗi. AIOS tự thu thập phần được phép, tạo file báo cáo có cấu trúc, thêm bảng hoặc biểu đồ phù hợp và ghi rõ căn cứ của từng kết luận.

**Kiểm thử độc lập**: với một bộ dữ liệu giả lập có log, số liệu và mô tả lỗi, hệ thống tạo được báo cáo tiếng Việt, biểu đồ khớp dữ liệu gốc và không bịa kết luận khi thiếu bằng chứng.

**Tiêu chí chấp nhận**:

1. Báo cáo nêu hiện tượng, ảnh hưởng, bằng chứng, giả thuyết, phần chưa chắc chắn và việc nên làm tiếp.
2. Mọi con số trong bảng hoặc biểu đồ truy ngược được tới nguồn và phép tổng hợp.
3. Khi dữ liệu không đủ để vẽ biểu đồ có ý nghĩa, hệ thống nói rõ và dùng bảng hoặc mô tả; không tạo biểu đồ trang trí.
4. File báo cáo được lưu tự động, hiện «Đã xong» ngay sau khi kiểm tra kỹ thuật đạt, và hoàn tác được. Không có bước duyệt.

### US2 — Rà soát và cải tiến thiết kế công đoạn (P1)

Kỹ sư chọn Guideline / tiêu chuẩn (luật) và bản thiết kế / SOP nháp (đối tượng), có thể kèm MOM, bản vẽ, báo cáo lỗi. AIOS tự gán vai trò nguồn theo [hợp đồng rà soát](contracts/agent-process-design-review-v1.md), đối chiếu từng điều: đạt, vi phạm hoặc chưa đủ bằng chứng; rồi lưu bản nháp đề xuất.

**Kiểm thử độc lập**: bộ giả lập có Guideline, bản thiết kế lệch một giới hạn, một bước thiếu điểm kiểm tra và một chỗ thiếu bằng chứng. Hệ thống gán đúng vai trò, ghi đúng `pass`/`violate`/`insufficient`, dẫn nguồn và không chặn «Đã xong» để chờ người tick từng mục.

**Tiêu chí chấp nhận**:

1. Mỗi mục kiểm tra có `verdict` và vị trí nguồn, hoặc nhãn `insufficient`.
2. Kết quả tách rõ hiện trạng, phát hiện, ảnh hưởng, đề xuất và câu hỏi cần xác nhận. Đề xuất không được viết như quy định đã ban hành.
3. Chỉ bản nháp; không ghi đè SOP/JIG/tiêu chuẩn/giới hạn sản xuất chính thức.
4. Có thể kèm sơ đồ hiện tại và đề xuất. Verifier đạt thì hiện «Đã xong» ngay; không duyệt từng finding.

### US3 — Sửa lỗi mã nguồn và kiểm thử thật (P2)

Kỹ sư mô tả lỗi hoặc đưa file báo lỗi. Agent tự đọc, tìm, sửa file và chạy các lệnh kiểm thử cho phép trong vùng làm việc tách biệt. Các thao tác nằm trong phạm vi nhiệm vụ được tự động duyệt.

**Kiểm thử độc lập**: Agent sửa một lỗi trong repo giả lập, chạy kiểm thử thất bại, sửa tiếp tới khi đạt, rồi tạo kết quả có thể dùng hoặc hoàn tác mà workspace chính không bị mất thay đổi có trước.

**Tiêu chí chấp nhận**:

1. Agent được đọc và sửa trong vùng nhiệm vụ; bị chặn khi thoát khỏi vùng, đọc bí mật hoặc chạy lệnh nguy hiểm.
2. Kết quả kiểm thử lấy từ lần chạy thực tế, không lấy từ lời tự khai của mô hình.
3. Người dùng thấy bản tóm tắt “đã làm gì, kiểm thử ra sao, file nào bị tác động, còn rủi ro gì”. Việc **xong trong worktree** khi test quan sát được đạt; không bắt bấm «Dùng kết quả» mới tính hoàn tất. «Hoàn tác» luôn có. «Đưa vào thư mục đang làm» là tùy chọn khi không xung đột.
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
- **FR-003**: Thao tác hợp lệ trong vùng nhiệm vụ được tự động duyệt, không hỏi người dùng. Thao tác ngoài vùng, bí mật, quyền quản trị, commit, push, merge hoặc deploy bị từ chối. Không dựng màn hình chọn từng quyền.
- **FR-004**: Mọi thao tác sửa mã nguồn phải diễn ra trong vùng làm việc tách biệt và có checkpoint để hoàn tác.
- **FR-005**: Báo cáo lỗi xưởng là file dùng được: tự lưu, hiện «Đã xong», không cổng duyệt. Rà soát công đoạn (US2) không ghi đè SOP/JIG/tiêu chuẩn gốc.
- **FR-006**: Mọi kết luận về lỗi xưởng hoặc thiết kế công đoạn phải gắn nguồn; phần chưa đủ bằng chứng phải được đánh dấu rõ. Payload US1 theo `contracts/agent-factory-error-report-v1.md`. Khi Agent gãy mới dùng `contracts/agent-error-report-v1.md`.
- **FR-007**: Biểu đồ chỉ được tạo từ dữ liệu có nguồn và phải giữ thông tin phép tổng hợp; thiếu dữ liệu thì không được bịa biểu đồ.
- **FR-008**: Kiểm thử mã nguồn phải dựa trên kết quả chạy thật và trạng thái file quan sát được.
- **FR-009**: Giao diện mặc định chỉ hiện mục tiêu, tiến độ, kết quả, rủi ro và bước tiếp theo bằng tiếng Việt; chi tiết kỹ thuật được thu gọn.
- **FR-010**: Hệ thống phải nhận nhiều nhiệm vụ, xếp hàng thao tác ghi theo từng workspace và tiếp tục được sau khi mở lại ứng dụng.
- **FR-011**: Không lưu transcript hoặc đầu ra thô vào hồ sơ; chỉ lưu trạng thái, nguồn, tệp đầu ra, kết quả kiểm tra và thông tin đã làm sạch cần để truy vết.
- **FR-012**: Không gửi dữ liệu `local_only` hoặc bí mật tới nguồn AI không được phép.
- **FR-013**: Cấm over-engineer: không editor, terminal, DB phiên, scheduler phân tán, nền tảng đa Agent, màn hình quyền, hay abstraction chưa có người dùng thật.
- **FR-014**: Rà soát công đoạn tách quy định hiện tại, phát hiện có nguồn, suy luận và đề xuất; không ghi đè SOP/JIG gốc.
- **FR-015**: Mọi kết quả có «Hoàn tác» dễ hiểu; không xóa thay đổi có trước của người dùng.
- **FR-016**: UI không hiện tên schema, OpenCode, worktree, verifier, receipt. Chỉ mục tiêu, tiến độ, kết quả, rủi ro, bước tiếp bằng tiếng Việt.

## 5. Thực thể chính

- **Nhiệm vụ Agent**: mục tiêu, loại công việc, nguồn được chọn, vùng file, lệnh cho phép và tiêu chí hoàn thành.
- **Mục hàng đợi**: thứ tự, trạng thái, workspace và khả năng tiếp tục.
- **File đầu ra**: báo cáo lỗi dùng được, sơ đồ, hoặc bản rà soát công đoạn.
- **Nguồn dẫn chứng**: vị trí tài liệu, số liệu và phép tổng hợp đứng sau một nhận xét hoặc biểu đồ.
- **Kết quả thực thi**: file đã tạo/sửa, kiểm thử đã chạy, trạng thái, rủi ro và checkpoint hoàn tác.

## 6. Tiêu chí thành công đo được

- **SC-001**: Với bộ dữ liệu nghiệm thu, 100% số liệu trên báo cáo và biểu đồ truy ngược được tới nguồn; không có số liệu tự tạo.
- **SC-002**: Với bộ tài liệu công đoạn nghiệm thu, 100% nhận xét được gắn nguồn hoặc đánh dấu rõ là đề xuất/chưa đủ bằng chứng.
- **SC-003**: Người dùng không chuyên giao việc, thấy «Đã xong» hoặc «Cần bổ sung nguồn», mở được kết quả và hoàn tác được — không mở `diff`, terminal, JSON và không duyệt từng bước.
- **SC-008**: 100% việc US1/US2 có nguồn đọc được phải kết thúc không cần click phê duyệt. «Cần bạn bổ sung» chỉ khi thiếu nguồn hoặc file hỏng.
- **SC-004**: Ba nhiệm vụ liên tiếp được giữ đúng trạng thái qua một lần đóng/mở ứng dụng và không ghi đè nhau.
- **SC-005**: 100% thao tác ngoài vùng, truy cập bí mật và lệnh bị cấm trong bộ kiểm thử an toàn bị chặn.
- **SC-006**: Lỗi mã nguồn giả lập được sửa, kiểm thử thật đạt và hoàn tác thành công mà không làm mất thay đổi có trước.
- **SC-007**: 100% thông báo, lỗi, tiến độ và báo cáo do hệ thống tạo cho người dùng là tiếng Việt dễ hiểu, không lộ traceback hay đường dẫn tuyệt đối.
- **SC-009**: Giao US1 hoặc US2 chỉ cần chọn nguồn và một câu/nút việc. Không có màn hình cấu hình, JSON hay danh sách quyền.
- **SC-010**: Trên UI thường không xuất hiện các chữ `schema`, `OpenCode`, `worktree`, `verifier`, `receipt`, `harness`.

## 7. Giả định và ranh giới

- Một người dùng cục bộ; Workspace Chat là giao diện chính.
- OpenCode là runtime Agent được thử trước; Cline chỉ được đánh giá nếu OpenCode không đáp ứng vòng đọc–sửa–test–hoàn tác.
- `antigravity_bridge.py` tiếp tục cung cấp tuyến AI cho Workspace Chat và không nằm trong phạm vi loại bỏ.
- Code-OSS có thể được dùng như công cụ kỹ thuật bên ngoài, nhưng extension riêng không phải điều kiện của vòng đầu.
- Báo cáo lỗi xưởng là file kết quả dùng được. Rà soát công đoạn không ghi đè SOP/JIG/tiêu chuẩn gốc và không tự đổi giới hạn sản xuất.
- Không dự đoán lỗi line và không tự lấy dữ liệu sản xuất khi người dùng chưa nạp nguồn.
