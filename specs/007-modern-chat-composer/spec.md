# Feature Specification: Modern Chat Composer

**Feature Branch**: `007-modern-chat-composer`

**Created**: 2026-08-25

**Trạng thái**: Phần composer, gợi ý, thẻ kết luận, bong bóng hỏi đáp, bước chờ và cụm trích dẫn giữ `TECHNICAL_PASS` theo smoke và kiểm thử đã ghi trong `tasks.md`. Phần hình thức toàn khung (câu chuyện 12–14) đã có mã và kiểm thử tĩnh; chưa có smoke trình duyệt, không tính nghiệm thu xưởng.

**Input**: User description: "Thiết kế lại thanh hỏi đáp theo AI IDE hiện đại: thumbnail ảnh đính kèm, dán nhanh ảnh clipboard, chọn Mô hình AI trong composer, và không còn vùng đính kèm choáng chỗ."

## Làm rõ

### Phiên 2026-09-21 (hình thức toàn khung)

- Hỏi: Tạo spec mới vì giao diện cả chương trình xấu, hay làm giàu spec đã có? → Đáp: Làm giàu spec này, vì đây là spec giao diện Workspace Chat đang mở. Không mở số spec mới.
- Hỏi: Đổi cách hỏi đáp, xóa hội thoại, thư viện hay tìm nguồn? → Đáp: Không. Chỉ đổi hình thức người dùng nhìn thấy. Hành vi đã đạt giữ nguyên.
- Hỏi: Làm mặt sáng hay giữ mặt tối hiện tại? → Đáp: Một mặt sáng cho đợt này. Mặt tối hiện tại chính là kiểu đang bị chê, và không làm hai mặt song song.

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

### Câu chuyện 9 — Nhìn là biết đâu là hỏi, đâu là đáp (Ưu tiên: P1, làm giàu 2026-09-21)

Người dùng mở hội thoại là phân biệt ngay bằng mắt thường đâu là câu hỏi của mình, đâu là câu trả lời của AI. Chữ đáp án dễ đọc trên màn hình rộng nhờ giới hạn bề rộng dòng, nội dung dài bao nhiêu cũng hiện đầy đủ, không cắt bớt.

**Vì sao ưu tiên này**: Màn hình hiện tại mọi thứ trông giống nhau và chữ dàn full-width nên đọc mệt, người dùng gọi là hỗn độn.

**Kiểm thử độc lập**: Mở hội thoại có sẵn một cặp hỏi đáp, bong bóng hỏi và đáp khác màu/khung rõ rệt; đáp án dài vẫn hiện đầy đủ.

**Tình huống nghiệm thu**:

1. **Cho** hội thoại có câu hỏi và câu trả lời, **khi** nhìn màn hình, **thì** bong bóng hỏi và đáp khác màu/khung rõ rệt.
2. **Cho** câu trả lời rất dài, **khi** hiển thị, **thì** toàn bộ nội dung hiện đầy đủ, chỉ giới hạn bề rộng dòng để dễ đọc.
3. **Cho** đáp án mới nhất, **khi** hiển thị, **thì** có dấu hiệu nhận biết đáp án mới nhất.

### Câu chuyện 10 — Lúc chờ biết máy đang làm gì (Ưu tiên: P1, làm giàu 2026-09-21)

Người dùng gửi câu hỏi xong thấy ngay 3 bước tiến triển: tìm nguồn, đọc trích đoạn, tổng hợp trả lời. Bước đang chạy sáng lên theo đúng trạng thái thật của hệ thống, không phần trăm giả.

**Vì sao ưu tiên này**: Lúc chờ chỉ có một dòng xoay vòng nên sốt ruột, không biết tiến triển.

**Kiểm thử độc lập**: Gửi câu hỏi khi tài liệu đang chuẩn bị thì bước tìm nguồn sáng; khi AI đang xử lý thì bước tổng hợp sáng.

**Tình huống nghiệm thu**:

1. **Cho** câu hỏi đang chờ tài liệu, **khi** nhìn, **thì** bước tìm nguồn đang chạy.
2. **Cho** AI đang xử lý, **khi** nhìn, **thì** bước tổng hợp đang chạy.
3. **Cho** mọi trạng thái chờ, **khi** hiển thị, **thì** không có phần trăm hay thời gian giả.

### Câu chuyện 11 — Trích dẫn gọn trong một cụm (Ưu tiên: P2, làm giàu 2026-09-21)

Người dùng thấy trích dẫn gom trong một cụm thu gọn có đếm số lượng, bấm mới mở từng nguồn. Nội dung không mất, chỉ gọn màn hình.

**Vì sao ưu tiên này**: Mỗi nguồn một khung mở sẵn kèm hộp xanh xếp chồng làm màn hình dài lê thê.

**Kiểm thử độc lập**: Mở đáp án có 3 nguồn trích dẫn, màn hình chỉ hiện một cụm gọn có đếm số lượng; bấm mở mới thấy từng nguồn.

**Tình huống nghiệm thu**:

1. **Cho** đáp án có nhiều nguồn trích dẫn, **khi** hiển thị, **thì** các khung chi tiết mặc định đóng.
2. **Cho** cụm trích dẫn, **khi** nhìn, **thì** thấy số lượng nguồn ngay trên tiêu đề cụm.

### Câu chuyện 12 — Ba vùng trông như một chương trình (Ưu tiên: P1, làm giàu 2026-09-21)

Người dùng mở Hỏi tài liệu, Hồ sơ và tri thức, hoặc Công cụ nâng cao đều thấy cùng một mặt sáng, cùng kiểu tiêu đề, cùng một màu cho việc chính. Không còn cảm giác mỗi màn một kiểu, cũng không còn nút chỉ nhận ra nhờ biểu tượng cảm xúc.

**Vì sao ưu tiên này**: Thanh hỏi và bong bóng đã chỉnh riêng, nhưng khung chương trình vẫn lẫn nền tối, chữ trang trí và biểu tượng cảm xúc. Người dùng nhìn cả chương trình vẫn thấy xấu.

**Kiểm thử độc lập**: Mở lần lượt ba vùng. Nền, tiêu đề và nút việc chính cùng một kiểu. Mỗi mục điều hướng có tên tiếng Việt nhìn thấy.

**Tình huống nghiệm thu**:

1. **Cho** người dùng đang ở một vùng, **khi** chuyển sang hai vùng còn lại, **thì** nền, thẻ, tiêu đề và màu nút việc chính không đổi kiểu.
2. **Cho** thanh điều hướng, **khi** nhìn, **thì** mỗi mục có tên tiếng Việt nhìn thấy, không phải đoán bằng biểu tượng cảm xúc.
3. **Cho** một việc chính và một việc nguy hiểm trên cùng màn, **khi** nhìn, **thì** hai việc khác màu, và màu việc chính không trùng màu kết luận Bình thường, Cần kiểm tra hay Nguy cơ.

### Câu chuyện 13 — Chữ tiếng Việt đọc được cả ca (Ưu tiên: P1, làm giàu 2026-09-21)

Người trực ban đọc câu trả lời, nhãn và nút mà không mất dấu, không bị cắt chữ, không phải nheo mắt trên nền tối lẫn sáng. Máy không có mạng thì chữ vẫn đủ dấu.

**Vì sao ưu tiên này**: Chữ là việc người dùng làm cả ca. Kiểu chữ trang trí hoặc chữ tải từ internet sẽ mất dấu hoặc đứng hình trong xưởng.

**Kiểm thử độc lập**: Ngắt mạng, mở một câu trả lời có đủ dấu tiếng Việt và một nhãn dài. Dấu còn đủ, nhãn xuống dòng, chữ thân bài không nhỏ hơn cỡ đọc thông thường.

**Tình huống nghiệm thu**:

1. **Cho** máy không nối mạng, **khi** mở chương trình, **thì** chữ giao diện vẫn đủ dấu tiếng Việt.
2. **Cho** nhãn tiếng Việt dài và cửa sổ 360 px hoặc chữ được phóng to, **khi** hiển thị, **thì** nhãn xuống dòng, không bị cắt cụt, vùng làm việc không cuộn ngang.
3. **Cho** chữ thân bài trên nền sáng, **khi** đối chiếu, **thì** tương phản đạt mức đọc được 4.5:1 và nút đang chọn bằng bàn phím có viền nhìn thấy.

### Câu chuyện 14 — Chỗ trống và lỗi nói rõ việc tiếp theo (Ưu tiên: P1, làm giàu 2026-09-21)

Khi chưa có sổ, chưa có hội thoại, đang chờ hoặc gặp lỗi, người dùng thấy một câu tiếng Việt ngay tại chỗ đó: chuyện gì xảy ra và làm gì tiếp. Không có khối cảnh báo chiếm cả trang, không có câu tiếng Anh của khung chương trình.

**Vì sao ưu tiên này**: Màn trống và lỗi hiện giống biểu mẫu mặc định, người không chuyên không biết bước tiếp theo.

**Kiểm thử độc lập**: Mở chương trình khi chưa có sổ, rồi mở sổ chưa có hội thoại. Mỗi màn một câu tiếng Việt kèm việc cần làm, không chiếm cả trang.

**Tình huống nghiệm thu**:

1. **Cho** chưa có sổ, **khi** mở chương trình, **thì** có một câu tiếng Việt nói chưa có sổ và cách tạo sổ.
2. **Cho** sổ chưa có hội thoại, **khi** mở sổ, **thì** có một câu tiếng Việt nói chưa có cuộc trò chuyện và cách tạo.
3. **Cho** một lỗi ở vùng đang dùng, **khi** lỗi xảy ra, **thì** câu giải thích nằm tại vùng đó, tiếng Việt, không hiện câu lỗi thô.

### Edge Cases

- Khi người dùng gửi nội dung trống và không có ảnh, hệ thống vẫn hiển thị thông báo hướng dẫn hiện có.
- Khi tải ảnh thất bại hoặc người dùng hủy, composer quay về trạng thái sẵn sàng nhập câu hỏi.
- Khi người dùng gửi câu hỏi đang chờ chuẩn bị nguồn, composer không tạo thêm một lần gửi ngoài ý muốn.
- Nhãn tiếng Việt dài hơn chữ Anh. Nhãn phải xuống dòng ở cửa sổ hẹp và khi phóng chữ, không cắt cụt nếu không có cách xem đủ chữ.
- Máy yêu cầu giảm chuyển động. Nội dung và trạng thái nút phải đúng ngay, không chờ hiệu ứng xuất hiện.
- Màu việc chính không được trùng màu đã dùng cho Bình thường, Cần kiểm tra hoặc Nguy cơ.
- Máy không có mạng. Chữ giao diện vẫn đủ dấu, không đứng chờ font từ internet.

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
- **FR-021**: Bong bóng hỏi và đáp PHẢI khác màu/khung rõ rệt; đáp án mới nhất PHẢI có dấu hiệu nhận biết.
- **FR-022**: Chữ đáp án PHẢI giới hạn bề rộng dòng để dễ đọc; nội dung dài bao nhiêu cũng PHẢI hiện đầy đủ, không cắt bớt.
- **FR-023**: Lúc chờ PHẢI hiện 3 bước tìm nguồn, đọc trích đoạn, tổng hợp trả lời; bước đang chạy PHẢI theo đúng trạng thái thật, không phần trăm giả.
- **FR-024**: Trích dẫn PHẢI gom trong cụm thu gọn có đếm số lượng; các khung chi tiết mặc định đóng.
- **FR-025**: Ba vùng Hỏi tài liệu, Hồ sơ và tri thức, Công cụ nâng cao PHẢI dùng cùng nền sáng, cùng thẻ sáng, cùng kiểu tiêu đề và cùng một màu cho việc chính.
- **FR-026**: Màu việc chính KHÔNG được trùng màu kết luận Bình thường, Cần kiểm tra hoặc Nguy cơ. Việc nguy hiểm PHẢI dùng một màu hủy riêng.
- **FR-027**: Mọi nút và mục điều hướng PHẢI có tên tiếng Việt nhìn thấy. Biểu tượng cảm xúc KHÔNG được là cách duy nhất để nhận ra một nút.
- **FR-028**: Chữ giao diện PHẢI đủ dấu tiếng Việt khi máy không nối mạng. Chữ thân bài KHÔNG nhỏ hơn 16 px, giãn dòng khoảng một lần rưỡi. Nhãn dài PHẢI xuống dòng; nếu buộc rút gọn thì PHẢI có cách xem đủ chữ.
- **FR-029**: Chữ thường trên nền sáng PHẢI đạt tương phản 4.5:1. Nút đang chọn bằng bàn phím PHẢI có viền nhìn thấy.
- **FR-030**: KHÔNG có chuyển động trang trí. Khi máy yêu cầu giảm chuyển động, trạng thái cuối của nút và nội dung PHẢI đúng ngay.
- **FR-031**: Màn chưa có sổ, chưa có hội thoại, đang chờ hoặc lỗi PHẢI có một câu tiếng Việt tại đúng vùng, nói chuyện gì xảy ra và việc làm tiếp theo, không chiếm cả trang bằng một khối cảnh báo chung.
- **FR-032**: Tiêu đề cửa sổ người dùng thấy PHẢI là tiếng Việt. Vùng làm việc KHÔNG cuộn ngang ở bề rộng 360, 768, 1024 và 1440 px.

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
- **SC-011**: Người dùng phân biệt hỏi và đáp bằng mắt thường; đáp án dài hiện đầy đủ, chỉ giới hạn bề rộng dòng.
- **SC-012**: Lúc chờ thấy 3 bước tiến triển theo đúng trạng thái thật, không phần trăm giả.
- **SC-013**: Trích dẫn gom trong cụm thu gọn có đếm số lượng, khung chi tiết mặc định đóng.
- **SC-014**: Người kiểm thử mở lần lượt ba vùng và nhận ra cùng nền, cùng kiểu tiêu đề, cùng màu nút việc chính mà không cần giải thích.
- **SC-015**: Trên ba vùng không còn nút chính nào chỉ nhận ra bằng biểu tượng cảm xúc.
- **SC-016**: Ở 360 px và 1280 px, khi phóng chữ, nhãn tiếng Việt không bị cắt và vùng làm việc không cuộn ngang.
- **SC-017**: Chữ thân bài trên nền sáng đạt tương phản 4.5:1; viền đang chọn nhìn thấy trên điều hướng và nút gửi.
- **SC-018**: Màn chưa có sổ và màn chưa có hội thoại, mỗi màn một câu tiếng Việt kèm việc cần làm, không một khối cảnh báo chiếm cả trang.
- **SC-019**: Ngắt mạng, chữ giao diện vẫn đủ dấu tiếng Việt.

## Assumptions

- Hành vi hỏi, gửi, xóa, thư viện, tìm nguồn và mail giữ nguyên. Đợt hình thức không đổi các luồng đó.
- Hình thức mới áp dụng cho cả ba vùng đang mở trong Workspace Chat: Hỏi tài liệu, Hồ sơ và tri thức, Công cụ nâng cao. Không làm trang giới thiệu. Không trang trí lại công cụ đã ngừng hỗ trợ nằm ngoài ba vùng này.
- Một mặt sáng cho đợt này. Không làm mặt tối song song.
- Không tải font hay biểu tượng từ internet. Chữ phải đủ dấu bằng font có sẵn trên máy hoặc font đóng gói cùng chương trình.
- Thao tác dán ảnh cần hành động người dùng vì trình duyệt bảo vệ quyền clipboard.
- Cầu nối được gọi là “Mô hình AI” trong UI để dễ hiểu, nhưng các lựa chọn vẫn là Gemini Web, C-AGENT API và Nakazasen Router chứ không giả định tên model nội bộ của từng dịch vụ.
