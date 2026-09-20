# Feature Specification: Conversation Management UX

**Feature Branch**: `004-conversation-management-ux`

**Created**: 2026-08-22

**Trạng thái**: `TECHNICAL_PASS` — 2026-09-13: `pytest -q -m "not desktop_packaging"` 2774 passed / 0 failed. Test đóng gói desktop không thuộc cổng này. Không tuyên bố nghiệm thu xưởng.

**Input**: User description: "Deleting a conversation is difficult to use, does not clearly identify the target conversation, and leaves a blank screen until another conversation is selected."

## Làm rõ

### Phiên 2026-09-19

- Hỏi: Không tạo spec mới thì làm giàu spec nào cho quản lý nhiều thư viện? → Đáp: Làm giàu `004-conversation-management-ux` vì đây là spec tổ chức không gian làm việc gần nhất, spec đã `TECHNICAL_PASS` nên mở rộng an toàn.
- Hỏi: Mỗi kho preset là một thư viện riêng hay trỏ chung một thư viện? → Đáp: Mỗi kho là một thư viện riêng, vào kho khác không xóa hay trộn kho cũ.
- Hỏi: Máy yếu vào nhiều kho cùng lúc được không? → Đáp: Một lúc chỉ mở một kho để dùng, các kho khác giữ nguyên không tốn tài nguyên.

### Phiên 2026-09-19 (hộp thư chung)

- Hỏi: Hộp thư yêu cầu đặt ở đâu? → Đáp: Theo từng kho, nằm trong thư mục của kho đó để yêu cầu đi theo kho, thêm kho không cần sửa mã.
- Hỏi: Ai được đánh dấu yêu cầu đã xong? → Đáp: Mọi máy trong nhóm tin cậy đều được, nhưng phải ghi rõ ai đánh dấu và lúc nào.
- Hỏi: Yêu cầu có cần chọn kho đích không? → Đáp: Có, bắt buộc chọn kho đích để khỏi nhầm kho.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete the intended conversation safely (Priority: P1)

As a Workspace Chat user, I can start deletion from a clearly identified conversation and confirm exactly which conversation will be removed.

**Why this priority**: A mistaken or ambiguous deletion risks losing user work and is the immediate usability failure reported.

**Independent Test**: Create several conversations, choose delete for one named conversation, confirm, and verify only that conversation and its conversation-only data are removed.

**Acceptance Scenarios**:

1. **Given** several conversations in a notebook, **When** I choose the delete action for one conversation, **Then** the confirmation identifies that conversation by title before I can complete deletion.
2. **Given** a deletion confirmation, **When** I cancel, **Then** no conversation or related data changes.
3. **Given** a deletion confirmation, **When** I confirm, **Then** only the named conversation and its conversation-scoped data are removed.

---

### User Story 2 - Continue without a blank screen after deletion (Priority: P1)

As a Workspace Chat user, after deleting the conversation I am viewing, I immediately land in a usable next state instead of an empty black content area.

**Why this priority**: The current failure makes a normal destructive action appear to break the application.

**Independent Test**: Delete the active conversation while other conversations exist, then repeat when it is the last conversation; verify the page always presents a usable destination.

**Acceptance Scenarios**:

1. **Given** the active conversation is deleted and another conversation remains, **When** deletion completes, **Then** the application opens an available remaining conversation and its URL/state match it.
2. **Given** the active conversation is the last one, **When** deletion completes, **Then** the application presents a clear empty state with an immediate action to create a new conversation.
3. **Given** the conversation displayed in the URL no longer exists, **When** the page is refreshed, **Then** the application recovers to a valid conversation or the clear empty state.

---

### User Story 3 - Manage the selected conversation with confidence (Priority: P2)

As a Workspace Chat user, I can see which conversation is selected and manage that exact conversation without relying on ambiguous sidebar state.

**Why this priority**: Rename and deletion controls are currently separated from the conversation list and make it easy to lose track of their target.

**Independent Test**: Switch among similarly named conversations, open management controls, rename one, and confirm the changed title and selection remain unambiguous.

**Acceptance Scenarios**:

1. **Given** several conversations, **When** I select one, **Then** its selected state is visually distinct and the management area names that conversation.
2. **Given** the management area is open, **When** I rename the selected conversation, **Then** its list entry and management heading update together.
3. **Given** conversations have similar titles, **When** I open a destructive action, **Then** the confirmation still makes the target distinguishable.

### Câu chuyện 4 — Tạo thư viện mới mà không cần biết kỹ thuật (Ưu tiên: P1)

Người dùng không chuyên tạo thêm thư viện theo kho thực tế như `Iris LSU`, `Tài liệu nghiệp vụ chung`, `Guideline thiết kế công đoạn` bằng cách đặt tên và chọn thư mục, không cần hiểu `storage_root` hay `library.sqlite`.

**Vì sao ưu tiên này**: Sản phẩm hiện chỉ có một thư viện `Tri thức` tự tạo sẵn và không có nút tạo mới, nên người dùng không thể tách kho theo dòng máy và dồn mọi thứ vào một kho khiến máy yếu chậm.

**Kiểm thử độc lập**: Tạo 10 thư viện từ danh sách mẫu, mỗi thư viện có tên, mô tả và thư mục riêng, đóng mở độc lập, kho cũ giữ nguyên.

**Tình huống nghiệm thu**:

1. **Cho** đang ở mục vị trí thư viện, **khi** người dùng đặt tên và chọn thư mục rồi xác nhận, **thì** danh sách có thêm thư viện mới mà thư viện cũ không mất.
2. **Cho** thư mục đã chứa thư viện khác, **khi** người dùng xác nhận, **thì** hệ thống báo rõ và giữ nguyên vị trí hiện tại thay vì trộn kho.

---

### Câu chuyện 5 — Vào kho có sẵn bằng một chạm (Ưu tiên: P1)

Người dùng thấy danh sách kho do admin chuẩn bị sẵn gồm tên, mô tả, số tài liệu và ngày cập nhật, bấm `Vào kho này` là dùng được ngay, không cần biết đường dẫn và không tự thêm tài liệu rồi chờ nhúng.

**Vì sao ưu tiên này**: Nhập đường dẫn thủ công làm người không chuyên bỏ qua và tự thêm tài liệu gây chờ lâu và trùng kho.

**Kiểm thử độc lập**: Chuẩn bị 10 tệp mẫu kho, vào từng kho, xác nhận kho cũ còn nguyên và lịch sử trò chuyện không đi theo kho.

**Tình huống nghiệm thu**:

1. **Cho** có danh sách kho admin chuẩn bị, **khi** người dùng bấm vào một kho, **thì** kho đó mở được ngay và kho trước đó vẫn nguyên.
2. **Cho** chưa có kho nào được chuẩn bị, **khi** người dùng mở danh sách, **thì** hệ thống báo rõ chưa có kho thay vì hiện mã kỹ thuật.

---

### Câu chuyện 6 — Gửi yêu cầu thêm tài liệu về máy kho (Ưu tiên: P2)

Người dùng kho chung chọn đúng kho đích, ghi tên người gửi và nội dung cần thêm. Yêu cầu nằm trong thư mục của kho đó nên máy kho mở kho là thấy. Mọi máy trong nhóm tin cậy đều được đánh dấu đã xong nhưng phải ghi rõ ai làm và lúc nào.

**Vì sao ưu tiên này**: Kho chung do một máy kho nhập mới tránh trùng và tránh chờ nhúng trên máy yếu. Không có máy kho quy định ở đâu khác: máy giữ thư mục gốc của kho chính là máy kho.

**Kiểm thử độc lập**: Ghi yêu cầu rỗng thì bị nhắc, không chọn kho thì bị nhắc, ghi thật thì máy khác đọc được, đánh dấu xong thì ghi tên người làm.

**Tình huống nghiệm thu**:

1. **Cho** có nhiều kho, **khi** người dùng gửi yêu cầu mà chưa chọn kho, **thì** hệ thống nhắc chọn kho thay vì ghi bừa.
2. **Cho** yêu cầu đã gửi vào kho, **khi** máy khác mở kho đó, **thì** thấy yêu cầu kèm tên người gửi.
3. **Cho** kho đang nằm trên máy người gửi chứ không phải thư mục chung, **khi** người dùng gửi, **thì** hệ thống báo rõ máy kho chưa thấy yêu cầu này.

### Edge Cases

- The selected conversation has already been deleted in another tab or external cleanup before the page reruns.
- Deletion persistence fails; the existing conversation remains selected and a clear error is shown.
- A stale URL references a conversation from another notebook or a conversation that no longer exists.
- The notebook has no conversations before first use or after deleting its final conversation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The conversation list MUST provide a clear selected state and a management entry point associated with a specific conversation.
- **FR-002**: Rename and delete controls MUST visibly name the conversation they affect.
- **FR-003**: Deletion confirmation MUST require an explicit confirm action and MUST offer a cancel action that preserves all data.
- **FR-004**: On successful deletion, the system MUST remove only the selected conversation and its conversation-scoped messages, temporary sources, and source selections.
- **FR-005**: After successful deletion of the active conversation, the system MUST select a remaining conversation when one exists; otherwise it MUST show a usable no-conversation state with a create action.
- **FR-006**: The application MUST clear or replace an invalid conversation reference in both in-memory navigation state and the browser URL.
- **FR-007**: If deletion fails or the selected conversation cannot be found, the system MUST preserve valid existing state and show a clear Vietnamese error message.
- **FR-008**: Existing notebook-level sources and data belonging to other conversations MUST remain unchanged by conversation management actions.
- **FR-009**: Hệ thống PHẢI cho phép tạo thư viện mới bằng tên và thư mục, mỗi thư viện có kho tìm kiếm riêng, thư viện cũ giữ nguyên.
- **FR-010**: Hệ thống PHẢI hiện danh sách kho admin chuẩn bị sẵn kèm tên, mô tả, số tài liệu và ngày cập nhật, cho phép vào kho bằng một chạm mà không bắt nhập đường dẫn.
- **FR-011**: Vào kho khác KHÔNG được xóa hay trộn kho cũ, lịch sử trò chuyện KHÔNG đi theo kho.
- **FR-012**: Hệ thống PHẢI cho phép ghi yêu cầu thêm tài liệu về máy kho, yêu cầu rỗng PHẢI bị nhắc bằng tiếng Việt.
- **FR-014**: Yêu cầu PHẢI ghi vào thư mục của kho đích đã chọn để máy kho mở kho là thấy, PHẢI ghi tên người gửi, PHẢI bắt buộc chọn kho đích.
- **FR-015**: Mọi máy đều được đánh dấu yêu cầu đã xong nhưng PHẢI ghi tên người làm và thời điểm, kho chỉ nằm trên máy người gửi PHẢI báo rõ máy kho chưa thấy.
- **FR-016**: Trong sổ PHẢI luôn thấy thư viện đang dùng và đổi được sang thư viện khác mà không mất cuộc trò chuyện và tài liệu đã lưu.
- **FR-017**: Lúc tạo sổ mà chỉ còn một thư viện PHẢI hiện câu xác nhận thay vì ô chọn vô nghĩa.
- **FR-013**: Mọi nhãn, nút, thông báo và lỗi của luồng thư viện PHẢI là tiếng Việt dễ hiểu, không hiện mã kỹ thuật hay lỗi thô.

### Key Entities

- **Workspace conversation**: A titled discussion belonging to one notebook, with conversation-scoped messages, temporary sources, and source selections.
- **Active conversation reference**: The currently displayed conversation as represented by application navigation state and shareable page location.
- **Deletion target**: The explicitly identified conversation pending confirmation; it must not drift when the selected conversation changes.
- **Thư viện**: Kho tìm kiếm riêng theo tên và thư mục, sổ tài liệu trỏ vào thư viện để hỏi.
- **Kho preset**: Gói kho do admin chuẩn bị sẵn gồm tên, mô tả, thư mục, phiên bản và ngày cập nhật, đọc từ thư mục mẫu mà không cần sửa mã.
- **Yêu cầu máy kho**: Ghi chú của người dùng kho chung đề nghị thêm tài liệu, lưu trên máy để gửi cho máy kho.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In all tested deletion cases, users reach a usable conversation or no-conversation state immediately after one confirmation action, with no blank content screen.
- **SC-002**: In all tested rename and deletion cases involving multiple similarly named conversations, the UI identifies the target before the change is committed.
- **SC-003**: In automated deletion tests, no messages, temporary sources, selections, or notebook-level sources belonging to other conversations are changed.
- **SC-004**: A stale or deleted conversation link recovers to a usable state on the first page refresh.
- **SC-005**: Tạo 10 thư viện mẫu đều mở độc lập được, thư viện cũ còn nguyên sau mỗi lần tạo và vào kho.
- **SC-006**: Mọi màn hình luồng thư viện không còn mã kỹ thuật hay lỗi thô, quét tiếng Việt đạt.

## Assumptions

- Conversation deletion remains permanent, but requires a lightweight in-context confirmation rather than a typed title challenge.
- When deleting the active conversation, the application chooses the first remaining conversation in the existing list order; it does not create a replacement automatically.
- Conversation management remains within the Workspace Chat sidebar and does not change notebook archival or deletion behavior.
