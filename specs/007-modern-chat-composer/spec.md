# Feature Specification: Modern Chat Composer

**Feature Branch**: `007-modern-chat-composer`

**Created**: 2026-08-25

**Status**: Draft

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

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng có thể nhận biết nơi nhập, đính kèm và gửi câu hỏi trong vòng 5 giây khi mở cuộc trò chuyện.
- **SC-002**: 100% các luồng gửi văn bản, gửi kèm một ảnh, và gửi nội dung trống hiện có vẫn hoàn tất hoặc báo lỗi đúng cách.
- **SC-003**: Composer vẫn hiển thị đầy đủ vùng nhập và các thao tác chính ở chiều rộng 360 px trở lên.
- **SC-004**: Kiểm thử giao diện liên quan đến Workspace Chat hiện có tiếp tục vượt qua sau thay đổi.
- **SC-005**: Người dùng có thể chọn Mô hình AI, thêm hoặc dán ảnh, xem thumbnail và gửi câu hỏi mà không cần rời composer.

## Assumptions

- Phạm vi chỉ là composer hỏi đáp chính và vị trí lựa chọn cầu nối; không thay đổi thanh bên, trình quản lý nguồn hoặc logic định tuyến.
- Thao tác dán ảnh cần hành động người dùng vì trình duyệt bảo vệ quyền clipboard.
- Cầu nối được gọi là “Mô hình AI” trong UI để dễ hiểu, nhưng các lựa chọn vẫn là Gemini Web, C-AGENT API và Nakazasen Router chứ không giả định tên model nội bộ của từng dịch vụ.
