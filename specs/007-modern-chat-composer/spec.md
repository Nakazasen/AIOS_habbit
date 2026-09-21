# Feature Specification: Modern Chat Composer

**Feature Branch**: `007-modern-chat-composer`

**Created**: 2026-08-25

**Trạng thái**: `TECHNICAL_PASS` — Playwright smoke 6/6 PASS 2026-09-12 (`scripts/smoke_007_modern_chat_composer.py`). Composer compact, chọn Gemini Web / C-AGENT / Nakazasen trong thanh chat, gửi câu hỏi (sổ chưa có nguồn thì hiện «Thiếu ngữ cảnh»), thumbnail ảnh, cửa sổ 360 px. Dán clipboard cần thao tác người dùng. Streamlit có thể giữ text sau gửi. Không tuyên bố nghiệm thu xưởng.

**Input**: User description: "Thiết kế lại thanh hỏi đáp theo AI IDE hiện đại: thumbnail ảnh đính kèm, dán nhanh ảnh clipboard, chọn Mô hình AI trong composer, và không còn vùng đính kèm choáng chỗ."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Soạn và gửi câu hỏi gọn gàng (Priority: P1)

Người dùng có thể nhập và gửi câu hỏi trong một thanh composer trực quan, gọn và nhất quán với giao diện ứng dụng hiện đại.

**Why this priority**: Đây là thao tác chính của Workspace Chat; giao diện phải giảm cảm giác biểu mẫu nặng nề và làm rõ hành động gửi.

**Independent Test**: Mở một cuộc trò chuyện, nhập văn bản và gửi câu hỏi; câu hỏi đi vào đúng luồng trả lời hiện có.

**Acceptance Scenarios**:

1. **Given** một cuộc trò chuyện đang mở, **When** người dùng nhìn vùng hỏi đáp, **Then** họ thấy một composer bo tròn chứa vùng nhập, nút đính kèm và nút gửi dễ nhận biết.
2. **Given** người dùng nhập một câu hỏi, **When** họ gửi bằng nút gửi, **Then** câu hỏi được xử lý như trước đây.
3. **Given** người dùng cần viết nhiều dòng, **When** nội dung dài hơn một dòng, **Then** vùng nhập mở rộng hợp lý mà vẫn giữ các nút thao tác dễ dùng.

---

### User Story 2 - Đính kèm hoặc dán ảnh không làm rối luồng hỏi (Priority: P2)

Người dùng có thể chọn tệp hoặc dán ảnh đã copy vào clipboard từ composer, thấy thumbnail có thể bỏ trước khi gửi, mà không phải nhìn một vùng tải tệp lớn khi chưa dùng đến.

**Why this priority**: Đính kèm ảnh là thao tác phụ nhưng cần luôn sẵn sàng và rõ ràng.

**Independent Test**: Chọn nút đính kèm, tải một ảnh hợp lệ, rồi gửi câu hỏi để xác nhận ảnh đi vào luồng xử lý hiện có.

**Acceptance Scenarios**:

1. **Given** composer đang ở trạng thái bình thường, **When** người dùng chưa chọn ảnh, **Then** vùng tải ảnh không chiếm không gian lớn.
2. **Given** người dùng cần đính kèm ảnh, **When** họ mở nút thêm ngữ cảnh, **Then** bộ chọn tệp và thao tác dán ảnh clipboard hiện ra với hướng dẫn định dạng hỗ trợ.
3. **Given** người dùng đã chọn hoặc dán ảnh, **When** ảnh sẵn sàng, **Then** composer hiện thumbnail và nút bỏ ảnh trước khi gửi.

---

### User Story 3 - Dùng được bằng bàn phím và màn hình hẹp (Priority: P3)

Người dùng có thể gửi câu hỏi bằng bàn phím và vẫn dùng được composer trên cửa sổ hẹp.

**Why this priority**: Các sản phẩm hiện đại cần hỗ trợ thao tác nhanh và bố cục thích ứng.

**Independent Test**: Dùng phím tắt gửi một câu hỏi và thu hẹp cửa sổ để kiểm tra các điều khiển vẫn truy cập được.

**Acceptance Scenarios**:

1. **Given** vùng nhập đang được chọn, **When** người dùng dùng phím tắt gửi hiện có, **Then** câu hỏi được gửi đúng một lần.
2. **Given** cửa sổ hẹp, **When** composer được hiển thị, **Then** vùng nhập và các nút không chồng lấp hoặc bị cắt.

---

### User Story 4 - Chọn Mô hình AI tại nơi hỏi (Priority: P2)

Người dùng có thể chọn động cơ AI đang dùng ngay trong thanh hỏi thay vì phải rời khỏi ngữ cảnh soạn câu hỏi.

**Why this priority**: “Cầu nối AI” hiện là đường đến Gemini Web, C-AGENT hoặc Router; trình bày nó như một lựa chọn Mô hình AI trong composer phù hợp với kỳ vọng người dùng hiện đại.

**Independent Test**: Chọn từng lựa chọn Mô hình AI trong composer và gửi câu hỏi; câu hỏi được định tuyến theo lựa chọn hiện có.

**Acceptance Scenarios**:

1. **Given** composer đang mở, **When** người dùng mở lựa chọn Mô hình AI, **Then** họ thấy các lựa chọn Gemini Web, C-AGENT API và Nakazasen Router.
2. **Given** người dùng chọn C-AGENT, **When** họ cần cấu hình AgentFlow, **Then** cấu hình URL chỉ hiện trong phần cài đặt gọn, không chiếm vùng hỏi chính.

### Câu chuyện 5 — Gợi ý câu hỏi mở đầu từ tài liệu trong sổ (Ưu tiên: P1)

Người không chuyên mở cuộc trò chuyện mới thấy ngay 3 câu gợi ý sinh từ tài liệu đang bật trong sổ, bấm một câu là gửi luôn, không phải nghĩ câu hỏi.

**Vì sao ưu tiên này**: Ô chat trống làm người mới đứng hình. Gợi ý theo đúng tài liệu trong sổ giúp họ bắt đầu ngay và hỏi trúng kho.

**Kiểm thử độc lập**: Sổ có tài liệu thì hiện đúng 3 gợi ý nhắc tên tài liệu, sổ chưa có nguồn thì không hiện gợi ý mà giữ thông báo thiếu ngữ cảnh hiện có.

**Tình huống nghiệm thu**:

1. **Cho** sổ có tài liệu đang bật, **khi** người dùng mở cuộc trò chuyện mới, **thì** họ thấy 3 câu gợi ý nhắc đúng tên tài liệu trong sổ.
2. **Cho** người dùng bấm một câu gợi ý, **khi** câu được gửi, **then** câu hỏi gửi đi đúng chữ câu gợi ý đó.
3. **Cho** sổ chưa có nguồn, **khi** người dùng mở cuộc trò chuyện, **then** không hiện gợi ý mà giữ thông báo thiếu ngữ cảnh.

### Câu chuyện 6 — Gợi ý câu tiếp theo sau mỗi câu trả lời (Ưu tiên: P2)

Người dùng đọc xong câu trả lời thấy tiếp 3 câu gợi ý theo sau dựa trên trích dẫn vừa nhận, bấm là hỏi tiếp.

**Vì sao ưu tiên này**: Giữ mạch tìm hiểu cho người không chuyên, khỏi nghĩ câu tiếp theo.

**Kiểm thử độc lập**: Câu trả lời có trích dẫn thì gợi ý nhắc đúng nhãn trích dẫn, không có trích dẫn thì gợi ý chung chung mà vẫn đúng ngữ cảnh sổ.

### Câu chuyện 7 — Composer siêu thân thiện cho người không chuyên (Ưu tiên: P1, làm giàu 2026-09-21)

Người trực ban, kỹ sư line và quản lý xưởng mở Workspace Chat là nhận ra ngay chỗ nhập, chỗ gửi, không cần hướng dẫn riêng. Mọi chữ đều tiếng Việt dễ hiểu, nút đủ to để bấm, lỗi nằm ngay cạnh trường vừa làm.

**Vì sao ưu tiên này**: Giao diện hiện tại khó nhìn, khó hiểu với người không chuyên. Ô nhập là điểm chạm đầu tiên nên phải một thao tác là xong.

**Kiểm thử độc lập**: Mở cuộc trò chuyện mới, người chưa dùng bao giờ chỉ ra được chỗ nhập, chỗ đính kèm, chỗ gửi trong 5 giây; gửi trống thì thấy hướng dẫn ngay cạnh nút gửi.

**Tình huống nghiệm thu**:

1. **Cho** cuộc trò chuyện đang mở, **khi** người dùng nhìn composer, **thì** họ thấy nhãn tiếng Việt nhìn thấy được cho ô nhập, nút đính kèm và nút gửi mũi tên nằm trong cùng một cụm.
2. **Cho** người dùng gửi nội dung trống, **khi** gửi, **thì** hướng dẫn hiện ngay cạnh nút gửi, không chỉ báo ở đầu trang.
3. **Cho** câu hỏi đang chờ tài liệu, **khi** chờ, **thì** nút mũi tên đổi thành nút dừng ngay trong composer và bấm là hủy được.
4. **Cho** màn hình hẹp 360 px hoặc phóng to chữ, **khi** hiển thị, **thì** các nút không chồng lấp, không cuộn ngang, chữ không bị cắt.

### Câu chuyện 8 — Thẻ JIG, biểu đồ và mail dễ hiểu cho mọi ca (Ưu tiên: P2, làm giàu 2026-09-21)

Người dùng dán log JIG vào Omnibar hoặc nhập file CSV thì nhận thẻ kết luận một câu tiếng Việt: Bình thường, Cần kiểm tra, hoặc Nguy cơ, kèm nguyên nhân nghi ngờ và việc cần làm tiếp. Biểu đồ xu hướng đánh dấu điểm bất thường bằng hình và chữ, kèm bảng số gọn. Dữ liệu trực tiếp có nút Tạm dừng/Tiếp tục. Mail cảnh báo luôn duyệt trước khi gửi.

**Vì sao ưu tiên này**: Bước 1 trong sheet các bước đòi hỏi nhập log, chọn biểu đồ, cảnh báo ngưỡng/xu hướng và mail kèm biểu đồ. Người không chuyên chỉ hành động được khi thẻ nói rõ kết luận và bước tiếp theo.

**Kiểm thử độc lập**: Dán một dòng log vượt ngưỡng, thẻ hiện kết luận Nguy cơ kèm ngưỡng vi phạm; biểu đồ có điểm đánh dấu và bảng số; mail thử hiện màn hình duyệt trước khi gửi.

**Tình huống nghiệm thu**:

1. **Cho** log dán vào vượt ngưỡng, **khi** xử lý xong, **thì** thẻ hiện kết luận, tên JIG, thông số vi phạm và đề xuất kiểm tra, toàn bộ tiếng Việt.
2. **Cho** thẻ có biểu đồ, **khi** xem, **thì** điểm bất thường có hình và chữ kèm theo, có bảng số thay thế, không phân biệt chỉ bằng màu sắc.
3. **Cho** luồng trực tiếp đang chạy, **khi** người dùng bấm Tạm dừng, **thì** dòng chat ngừng cập nhật nhưng dữ liệu vẫn ghi ngầm.
4. **Cho** cảnh báo đủ điều kiện gửi mail, **khi** gửi, **thì** hệ thống hiện màn hình duyệt nội dung và biểu đồ trước, chỉ gửi khi người dùng đồng ý.

### Edge Cases

- Khi người dùng gửi nội dung trống và không có ảnh, hệ thống vẫn hiển thị thông báo hướng dẫn hiện có.
- Khi tải ảnh thất bại hoặc người dùng hủy, composer quay về trạng thái sẵn sàng nhập câu hỏi.
- Khi người dùng gửi câu hỏi đang chờ chuẩn bị nguồn, composer không tạo thêm một lần gửi ngoài ý muốn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST trình bày vùng hỏi đáp chính dưới dạng một composer bo tròn, cô đọng và trực quan.
- **FR-002**: Composer MUST có vùng nhập văn bản, thao tác đính kèm ảnh và thao tác gửi trong cùng một cụm điều khiển dễ nhận biết.
- **FR-003**: Hệ thống MUST giữ nguyên luồng gửi câu hỏi, kiểm tra nội dung trống, xử lý ảnh và trạng thái chờ chuẩn bị nguồn hiện có.
- **FR-004**: Hệ thống MUST chỉ mở vùng tải ảnh khi người dùng yêu cầu đính kèm hoặc đã chọn ảnh.
- **FR-004a**: Hệ thống MUST cho phép người dùng dán một ảnh từ clipboard qua một thao tác có xác nhận của trình duyệt, rồi xem thumbnail và bỏ ảnh trước khi gửi.
- **FR-005**: Người dùng MUST có thể gửi bằng nút gửi và phím tắt gửi hiện có.
- **FR-006**: Composer MUST hoạt động trên cả cửa sổ rộng và hẹp, không để các điều khiển chồng lấp.
- **FR-007**: Nhãn, hướng dẫn và phản hồi hiển thị cho người dùng MUST giữ Vietnamese-first.
- **FR-008**: Composer MUST hiển thị lựa chọn Mô hình AI ở thanh công cụ dưới vùng nhập và ánh xạ chính xác đến lựa chọn cầu nối AI hiện có.
- **FR-009**: Cấu hình và kiểm tra kết nối chuyên sâu MUST được thu gọn, không xuất hiện trong tiêu đề cuộc trò chuyện hoặc vùng hỏi mặc định.
- **FR-010**: Composer MUST hiển thị hành động gửi dưới dạng mũi tên biểu tượng nhỏ nằm trong composer; không hiển thị một nút chữ gửi/hỏi lớn bên ngoài vùng soạn.
- **FR-011**: Khi câu hỏi đang chờ chuẩn bị tài liệu, hành động mũi tên MUST đổi thành biểu tượng dừng trong chính composer và người dùng có thể hủy câu hỏi chờ đó.
- **FR-012**: Hệ thống PHẢI hiện tối đa 3 câu gợi ý mở đầu sinh từ tên tài liệu đang bật trong sổ, nếu chưa bật nguồn nào thì dùng tên tài liệu trong sổ, bấm gợi ý PHẢI gửi đúng chữ câu đó.
- **FR-013**: Sau mỗi câu trả lời có trích dẫn, hệ thống PHẢI hiện tối đa 3 câu gợi ý tiếp theo nối mạch câu đang hỏi và ghi tên tài liệu dễ hiểu thay vì mã trích dẫn, chữ gửi đi PHẢI mang tên tài liệu đầy đủ kèm câu hỏi và ý chính câu trả lời trước để câu trả lời bám đúng mạch.
- **FR-014**: Composer PHẢI có nhãn tiếng Việt nhìn thấy được cho ô nhập, thao tác đính kèm và thao tác gửi; không dùng gợi ý mờ thay cho nhãn.
- **FR-015**: Nút gửi và nút dừng PHẢI đủ to để bấm (tối thiểu 44 px) và cách nhau tối thiểu 8 px; lỗi và hướng dẫn PHẢI hiện ngay cạnh trường vừa thao tác.
- **FR-016**: Thẻ kết quả JIG PHẢI mở đầu bằng một câu kết luận tiếng Việt (Bình thường, Cần kiểm tra, Nguy cơ) kèm tên JIG, thông số vi phạm và việc cần làm tiếp.
- **FR-017**: Biểu đồ xu hướng PHẢI đánh dấu điểm bất thường bằng hình và chữ kèm theo, kèm bảng số gọn thay thế; không phân biệt trạng thái chỉ bằng màu sắc.
- **FR-018**: Luồng trực tiếp PHẢI có nút Tạm dừng/Tiếp tục; khi tạm dừng, dòng chat ngừng cập nhật nhưng dữ liệu vẫn ghi ngầm.
- **FR-019**: Mail cảnh báo PHẢI hiện màn hình duyệt nội dung và biểu đồ trước khi gửi; chỉ gửi khi người dùng đồng ý.
- **FR-020**: Mọi chữ người dùng đọc trong composer, thẻ JIG, biểu đồ và mail PHẢI là tiếng Việt dễ hiểu; chữ tương phản tối thiểu 4.5:1, giữ thứ tự phím bấm, tôn trọng chế độ giảm chuyển động.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng có thể nhận biết nơi nhập, đính kèm và gửi câu hỏi trong vòng 5 giây khi mở cuộc trò chuyện.
- **SC-002**: 100% các luồng gửi văn bản, gửi kèm một ảnh, và gửi nội dung trống hiện có vẫn hoàn tất hoặc báo lỗi đúng cách.
- **SC-003**: Composer vẫn hiển thị đầy đủ vùng nhập và các thao tác chính ở chiều rộng 360 px trở lên.
- **SC-004**: Kiểm thử giao diện liên quan đến Workspace Chat hiện có tiếp tục vượt qua sau thay đổi.
- **SC-005**: Người dùng có thể chọn Mô hình AI, thêm hoặc dán ảnh, xem thumbnail và gửi câu hỏi mà không cần rời composer.
- **SC-006**: Sổ có tài liệu thì 3 gợi ý mở đầu nhắc đúng tên tài liệu, bấm gợi ý gửi đúng chữ, sổ chưa có nguồn thì không hiện gợi ý.
- **SC-007**: Người chưa dùng bao giờ nhận ra chỗ nhập, chỗ đính kèm và chỗ gửi trong 5 giây; gửi trống thì hướng dẫn hiện ngay cạnh nút gửi.
- **SC-008**: Composer và thẻ JIG dùng được ở 360 px, phóng to chữ không chồng lấp, không cuộn ngang, không cắt chữ.
- **SC-009**: Thẻ JIG vượt ngưỡng hiện đúng kết luận, tên JIG, thông số vi phạm và đề xuất kiểm tra; biểu đồ có điểm đánh dấu bằng hình và chữ kèm bảng số.
- **SC-010**: Luồng trực tiếp tạm dừng được mà không mất dữ liệu ngầm; mail cảnh báo chỉ gửi sau khi người dùng duyệt.

## Assumptions

- Phạm vi chỉ là composer hỏi đáp chính và vị trí lựa chọn cầu nối; không thay đổi thanh bên, trình quản lý nguồn hoặc logic định tuyến.
- Thao tác dán ảnh cần hành động người dùng vì trình duyệt bảo vệ quyền clipboard.
- Cầu nối được gọi là “Mô hình AI” trong UI để dễ hiểu, nhưng các lựa chọn vẫn là Gemini Web, C-AGENT API và Nakazasen Router chứ không giả định tên model nội bộ của từng dịch vụ.
