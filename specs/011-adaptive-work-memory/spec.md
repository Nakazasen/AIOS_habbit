# Đặc tả tính năng: Vòng trí nhớ công việc thích nghi

**Nhánh tính năng dự kiến**: `011-adaptive-work-memory`  
**Ngày tạo**: 2026-09-12  
**Trạng thái**: `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`  
**Đầu vào**: Nâng cấp Workspace Chat để càng dùng càng hữu ích như Grokbot, nhưng chỉ học từ tri thức đã được người dùng xác nhận và không thiết kế quá mức.

## 1. Mục tiêu

Workspace Chat phải nhớ lại đúng các bài học, quyết định và cách làm đã được xác nhận trước khi trả lời một việc liên quan. Người dùng có thể chủ động yêu cầu nhớ, quên hoặc sửa một bài học. Mức “thông minh dần” được đo bằng khả năng tái sử dụng tri thức đáng tin cậy, không phải bằng tự huấn luyện mô hình hoặc tự biến mọi hội thoại thành sự thật.

Goal 011 triển khai độc lập với trạng thái đóng của Goal 010. Artifact Goal 010 chỉ là một nguồn đọc tùy chọn: nếu có bản đã xuất bản và còn hiệu lực thì dùng; nếu chưa có hoặc Goal 010 chưa hoàn tất thì bỏ qua nguồn đó và tiếp tục bằng các nguồn trí nhớ còn lại.

## 2. Hành trình người dùng và kiểm thử

### Câu chuyện người dùng 1 — Nhắc lại bài học đúng lúc (Ưu tiên: P1) 🎯 MVP

Là người dùng Workspace Chat, khi hỏi một việc tương tự việc đã làm trước đây, tôi muốn AIOS tự tìm và dùng các bài học đã được xác nhận có liên quan để tôi không phải giải thích lại từ đầu.

**Lý do ưu tiên**: Đây là mắt xích đang thiếu để dữ liệu học hiện có tạo ra giá trị trong câu trả lời hằng ngày. Chỉ riêng lát cắt đọc này đã tạo một MVP hữu ích và không làm thay đổi dữ liệu.

**Kiểm thử độc lập**: Chuẩn bị một bài học đã xác nhận, một bài nháp, một bài đã thu hồi và một câu hỏi liên quan; chỉ bài đã xác nhận phải xuất hiện trong ngữ cảnh trả lời cùng nguồn gốc rõ ràng.

**Kịch bản nghiệm thu**:

1. **Cho trước** một bài học đã xác nhận, còn hiệu lực và đúng phạm vi, **khi** người dùng hỏi việc liên quan, **thì** AIOS đưa tối đa phần trí nhớ cần thiết vào câu trả lời và cho biết bài học đến từ đâu.
2. **Cho trước** chỉ có nội dung nháp, thiếu bằng chứng, đã thu hồi hoặc ngoài phạm vi, **khi** người dùng hỏi, **thì** AIOS không dùng nội dung đó như tri thức đáng tin cậy.
3. **Cho trước** không có bài học đủ liên quan, **khi** người dùng hỏi, **thì** AIOS trả lời theo luồng hiện tại mà không chèn mục trí nhớ rỗng hoặc lời nhắc gây nhiễu.
4. **Cho trước** hai bài học đủ tin cậy nhưng mâu thuẫn, **khi** người dùng hỏi, **thì** AIOS nêu rằng cần kiểm tra lại và không tự chọn một bên làm sự thật.

---

### Câu chuyện người dùng 2 — Chủ động nhớ và quên (Ưu tiên: P2)

Là người dùng, tôi muốn nói rõ điều gì cần nhớ lâu dài và điều gì phải quên để tôi kiểm soát trí nhớ của trợ lý.

**Lý do ưu tiên**: Trí nhớ chỉ bền vững khi có ý chí rõ ràng của người dùng; việc này ngăn hội thoại thường ngày bị biến thành dữ liệu học ngoài mong muốn.

**Kiểm thử độc lập**: Yêu cầu AIOS nhớ một quy tắc, xem trước nội dung, xác nhận, hỏi lại trong phiên mới, sau đó yêu cầu quên và xác nhận quy tắc không còn được dùng.

**Kịch bản nghiệm thu**:

1. **Cho trước** người dùng nói “hãy nhớ…”, **khi** chưa xác nhận bản xem trước, **thì** nội dung chưa được dùng như trí nhớ đã xác nhận.
2. **Cho trước** người dùng đã xác nhận một nội dung có căn cứ, **khi** mở phiên mới và hỏi việc liên quan, **thì** nội dung có thể được nhắc lại cùng nguồn gốc.
3. **Cho trước** người dùng yêu cầu quên một nội dung, **khi** xác nhận thao tác, **thì** nội dung không còn được truy xuất nhưng lịch sử quyết định vẫn đủ để kiểm toán.

---

### Câu chuyện người dùng 3 — Biến sửa sai thành bài học (Ưu tiên: P3)

Là người dùng, khi sửa một câu trả lời sai, tôi muốn AIOS đề xuất một bài học ngắn để tôi duyệt, nhờ đó lỗi tương tự ít lặp lại hơn.

**Lý do ưu tiên**: Sửa sai có tín hiệu mạnh hơn hội thoại thông thường, nhưng vẫn cần người dùng kiểm soát trước khi trở thành tri thức bền vững.

**Kiểm thử độc lập**: Tạo một câu trả lời sai, nhập phần sửa, duyệt bài học đề xuất và kiểm tra ở câu hỏi tương tự tiếp theo; bài học trùng lặp phải được hợp nhất hoặc yêu cầu xử lý xung đột.

**Kịch bản nghiệm thu**:

1. **Cho trước** người dùng sửa một câu trả lời, **khi** chưa duyệt bài học đề xuất, **thì** phần sửa chỉ là ứng viên và chưa ảnh hưởng câu trả lời khác.
2. **Cho trước** người dùng đã xem, chỉnh và xác nhận bài học, **khi** gặp câu hỏi tương tự, **thì** AIOS ưu tiên nhắc bài học đã xác nhận cùng căn cứ.
3. **Cho trước** bài học mới gần trùng hoặc trái với bài học hiện có, **khi** người dùng xác nhận, **thì** AIOS không tạo bản trùng âm thầm và yêu cầu chọn thay thế, giữ cả hai có cảnh báo hoặc hủy.

### Trường hợp biên bắt buộc

- Tệp trí nhớ hỏng, kho bị khóa hoặc một nguồn đọc không khả dụng: câu hỏi hiện tại vẫn chạy theo luồng cũ và có cảnh báo tiếng Việt ngắn, không lộ traceback.
- Trí nhớ rất dài hoặc có nhiều kết quả ngang điểm: chỉ dùng một số lượng hữu hạn, sắp xếp ổn định và cho người dùng xem nguồn gốc.
- Câu hỏi mới trái với một bài học cũ: yêu cầu hiện tại và bằng chứng hiện tại không bị bài học cũ ghi đè.
- Cùng một nội dung được yêu cầu nhớ nhiều lần: không tạo các bản sao không phân biệt được.
- Nội dung đã quên hoặc thu hồi xuất hiện trong cache: phải bị loại trước khi tạo câu trả lời.
- Tính năng bị tắt: hành vi và nội dung prompt của Workspace Chat giữ nguyên như baseline đã kiểm thử.
- Ngôn ngữ hoặc ký tự tiếng Việt khác cách viết nhưng cùng ý: tìm kiếm từ khóa phải chịu được khác biệt hoa/thường và khoảng trắng cơ bản; tìm kiếm ngữ nghĩa sâu không thuộc MVP.

## 3. Yêu cầu chức năng

- **FR-001**: Goal 011 MUST không phụ thuộc vào việc Goal 010 hoàn tất; adapter Goal 010 không sẵn sàng MUST trả về không có candidate thay vì chặn câu trả lời hoặc chặn triển khai.
- **FR-002**: Hệ thống MUST tìm trí nhớ liên quan trước khi tạo câu trả lời Workspace Chat.
- **FR-003**: Hệ thống MUST chỉ coi nội dung đã xác nhận, còn hiệu lực, có nguồn gốc và đúng phạm vi là đủ điều kiện dùng.
- **FR-004**: Hệ thống MUST loại nội dung nháp, ứng viên, thiếu bằng chứng, bị từ chối, lỗi thời, đã quên hoặc đã thu hồi khỏi ngữ cảnh trả lời.
- **FR-005**: Mỗi mục trí nhớ được dùng MUST giữ mã nguồn, loại nguồn, trạng thái, phạm vi, thời điểm và tham chiếu bằng chứng để kiểm toán.
- **FR-006**: Hệ thống MUST giới hạn số mục và dung lượng trí nhớ đưa vào một câu trả lời để không lấn át câu hỏi và nguồn hiện tại.
- **FR-007**: Trí nhớ MUST được trình bày như ngữ cảnh tham khảo; không được đóng vai chỉ dẫn hệ thống và không được ghi đè yêu cầu hiện tại hoặc bằng chứng hiện tại.
- **FR-008**: Khi không có kết quả đủ liên quan, hệ thống MUST giữ im lặng về trí nhớ và tiếp tục luồng trả lời hiện tại.
- **FR-009**: Khi các mục đủ điều kiện mâu thuẫn, hệ thống MUST không tự tuyên bố bên thắng và MUST cung cấp trạng thái cần kiểm tra lại.
- **FR-010**: Người dùng MUST có thể xem vì sao một mục được gợi lại và mở tham chiếu nguồn tương ứng khi nguồn còn tồn tại.
- **FR-011**: Người dùng MUST có thể yêu cầu nhớ một quy tắc hoặc bài học và xem trước bản ghi trước khi xác nhận.
- **FR-012**: Nội dung yêu cầu nhớ MUST không trở thành trí nhớ đã xác nhận nếu thiếu hành động xác nhận hoặc thiếu căn cứ bắt buộc.
- **FR-013**: Người dùng MUST có thể yêu cầu quên hoặc thu hồi một mục; mục đó MUST ngừng được truy xuất ngay sau khi xác nhận, trong khi lịch sử quyết định vẫn được giữ.
- **FR-014**: Khi người dùng sửa câu trả lời, hệ thống MUST tạo bản đề xuất bài học có thể sửa và MUST chờ xác nhận trước khi tái sử dụng.
- **FR-015**: Hệ thống MUST phát hiện bài học gần trùng và xung đột trước khi tạo bản bền vững mới.
- **FR-016**: Trí nhớ bền vững MUST lưu mẫu tri thức có cấu trúc đã xác nhận, không lưu toàn bộ hội thoại hoặc câu trả lời thô.
- **FR-017**: Dữ liệu `local_only`, dữ liệu chưa xác nhận và nội dung riêng tư MUST không đi vào lời nhắc gửi dịch vụ đám mây, gói xuất hoặc Git nếu chưa có đồng ý và chính sách rõ ràng.
- **FR-018**: Mọi thao tác nhớ, quên, thu hồi, hợp nhất, thay thế và dùng lại MUST tạo dấu vết kiểm toán không chứa bí mật hay nội dung thô bị cấm.
- **FR-019**: Tính năng MUST có công tắc tắt an toàn; khi tắt hoặc khi lớp trí nhớ lỗi, luồng trả lời hiện tại vẫn hoạt động.
- **FR-020**: Toàn bộ nhãn, cảnh báo, lỗi và hướng dẫn người dùng MUST là tiếng Việt dễ hiểu, không lộ tên engine, đường dẫn máy hoặc traceback.
- **FR-021**: MVP MUST chạy cục bộ trên laptop i5, RAM 16 GB, không GPU và không đòi mô hình, dịch vụ hay cơ sở dữ liệu mới.
- **FR-022**: Workspace Chat MUST luôn cho người dùng thấy lựa chọn “Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn”; lựa chọn MUST được giữ cục bộ qua lần khởi động sau và không buộc người dùng nhớ lệnh hoặc biến môi trường.

## 4. Thực thể chính

- **Mục nhớ dùng cho câu trả lời**: Bản nhìn thống nhất, chỉ đọc của một tri thức đủ điều kiện; gồm nội dung ngắn, phạm vi áp dụng, điều kiện không áp dụng, nguồn gốc, bằng chứng, trạng thái và độ mới.
- **Quyết định trí nhớ**: Ghi nhận việc người dùng xác nhận nhớ, quên, thu hồi, thay thế hoặc giữ một mục, cùng thời điểm và căn cứ.
- **Ứng viên bài học từ sửa sai**: Bản đề xuất chưa có hiệu lực, chứa lỗi đã gặp, cách sửa, phạm vi áp dụng và liên kết tới bằng chứng của phiên hiện tại.
- **Dấu vết gọi lại**: Ghi nhận truy vấn, các mục được chọn hoặc bị loại và lý do ở mức metadata an toàn để kiểm toán chất lượng.

## 5. Tiêu chí thành công đo được

- **SC-001**: Trong bộ kiểm thử trạng thái nguồn, 100% nội dung nháp, thiếu bằng chứng, bị từ chối, đã quên hoặc đã thu hồi không xuất hiện trong ngữ cảnh trả lời.
- **SC-002**: Trong bộ tối thiểu 30 tình huống đã gắn nhãn, ít nhất 90% câu hỏi có bài học liên quan gọi lại đúng ít nhất một mục và 100% câu hỏi không liên quan không bị chèn trí nhớ.
- **SC-003**: Mỗi câu trả lời dùng trí nhớ cho phép truy ra đúng nguồn và quyết định xác nhận trong 100% tình huống nghiệm thu.
- **SC-004**: Người dùng hoàn tất luồng nhớ hoặc quên trong không quá ba hành động chính sau khi nhập yêu cầu.
- **SC-005**: Một bài học được sửa và xác nhận có thể được dùng ở phiên mới, còn bản chưa xác nhận không ảnh hưởng phiên mới trong 100% tình huống nghiệm thu.
- **SC-006**: Trên máy tham chiếu i5, RAM 16 GB, không GPU, ít nhất 95% lượt tìm trí nhớ trong kho 10.000 mục hoàn tất dưới 500 ms và phần tăng bộ nhớ làm việc không vượt 200 MB.
- **SC-007**: Không có hội thoại thô, bí mật hoặc nội dung `local_only` chưa được đồng ý xuất hiện trong dữ liệu xuất, Git hay dữ liệu gửi nhà cung cấp ngoài ở toàn bộ kiểm thử riêng tư.
- **SC-008**: Khi công tắc tắt hoặc lớp trí nhớ lỗi, 100% kiểm thử hồi quy xác nhận Workspace Chat vẫn dùng hành vi baseline và hiển thị lỗi an toàn bằng tiếng Việt nếu cần.
- **SC-009**: Toàn bộ quality gate bắt buộc của repo đạt `PASS`, quickstart đạt, và kiểm toán độc lập không còn finding mức chặn trước khi Goal 011 được đánh dấu hoàn thành.

## 6. Giả định và ranh giới

- Người dùng mục tiêu là cá nhân hoặc nhóm nhỏ tin cậy có quyền mở cùng thư viện; tên người thao tác dùng để truy vết, không phải xác thực danh tính.
- Workspace Chat là giao diện duy nhất được hỗ trợ cho tính năng này.
- Các kho hiện có tiếp tục là nguồn sự thật của từng loại tri thức; Goal 011 tạo lớp đọc thống nhất, không nhập tất cả dữ liệu vào một kho mới.
- Tìm kiếm MVP dùng từ khóa có kiểm soát và metadata đã có. Vector search, GraphRAG và reranker cục bộ được hoãn cho đến khi benchmark chứng minh tìm kiếm đơn giản không đủ.
- Không fine-tune, không tự thay model, không tự học từ toàn bộ hội thoại, không chạy agent nền 24/7 và không kích hoạt WorkflowCard để tự thực thi trong Goal này.
- Không mở rộng sang tài khoản, RBAC, máy chủ trung tâm, đồng bộ đa thiết bị hoặc quyền bảo mật giữa thành viên cùng thư viện.
- Bàn giao/tiếp tục phiên, kích hoạt WorkflowCard và tự động hóa agent được đưa ra Goal sau; không thuộc vòng học tối thiểu này.
- Các ngưỡng giới hạn ngữ cảnh mặc định dự kiến là tối đa 5 mục và 4.000 ký tự; kế hoạch kỹ thuật có thể chọn ngưỡng thấp hơn nếu kiểm thử cho thấy an toàn hơn, nhưng không được vượt nếu chưa cập nhật đặc tả.
