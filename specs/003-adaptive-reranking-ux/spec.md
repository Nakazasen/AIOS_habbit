# Feature Specification: Tìm kiếm thích ứng và chế độ Tìm kỹ

**Feature Branch**: `[main]`

**Created**: 2026-08-16

**Trạng thái**: `IMPLEMENTED_PENDING_REAL_BENCHMARK` — code và test đã có; chưa bật mặc định trước benchmark trên model/corpus thật

**Input**: User description: "Mặc định hệ thống tự đánh giá câu hỏi để dùng BGE-M3 Hybrid hoặc BGE-M3 Hybrid + Reranker; người dùng có quyền bật Tìm kỹ hơn, và hệ thống không được tự coi mọi câu hỏi là dễ."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự chọn mức tìm kiếm phù hợp (Priority: P1)

Là người dùng Workspace Chat, tôi chỉ cần đặt câu hỏi bằng ngôn ngữ tự nhiên. Hệ thống tự dùng cách tìm thông thường cho trường hợp rõ ràng và nâng lên cách tìm kỹ hơn khi câu hỏi phức tạp, kết quả ban đầu chưa đủ chắc chắn, hoặc hệ thống không tự tin về quyết định.

**Why this priority**: Đây là hành vi mặc định cho mọi câu hỏi. Nếu phân luồng sai theo hướng coi câu khó là câu dễ, chất lượng câu trả lời có thể giảm mà người dùng không biết.

**Independent Test**: Dùng một bộ câu hỏi đã được gắn nhãn gồm câu rõ ràng, câu nhiều ý, câu so sánh, câu cần nhiều nguồn, câu có nguồn mâu thuẫn và câu mơ hồ. Xác nhận câu rõ ràng đi đường nhanh, còn câu phức tạp hoặc chưa đủ bằng chứng được nâng lên đường tìm kỹ.

**Acceptance Scenarios**:

1. **Given** chế độ mặc định là `Tự động`, **When** người dùng hỏi một thông tin rõ ràng có một mục tiêu và kết quả tìm lần đầu đủ mạnh, **Then** hệ thống dùng tìm kiếm kết hợp thông thường và không chạy tầng xếp hạng lại.
2. **Given** chế độ mặc định là `Tự động`, **When** câu hỏi có nhiều ý, cần so sánh/tổng hợp/giải thích quan hệ hoặc cần bằng chứng từ nhiều nguồn, **Then** hệ thống yêu cầu tìm kiếm kết hợp cộng xếp hạng lại.
3. **Given** câu hỏi nhìn bề ngoài đơn giản, **When** kết quả tìm lần đầu thiếu độ phủ, quá giống nhau, mâu thuẫn hoặc không đủ nguồn, **Then** hệ thống tự nâng lên tìm kỹ thay vì kết luận đó là câu dễ.
4. **Given** các tín hiệu đánh giá không thống nhất hoặc ở sát ngưỡng, **When** hệ thống chưa chắc nên chọn đường nào, **Then** hệ thống ưu tiên tìm kỹ.

---

### User Story 2 - Người dùng chủ động yêu cầu Tìm kỹ hơn (Priority: P1)

Là người dùng cần độ chắc chắn cao, tôi có thể bật `Tìm kỹ hơn (có thể chậm hơn)` ngay tại vùng nhập câu hỏi. Lựa chọn này thể hiện nhu cầu của tôi, không bắt tôi hiểu tên model hay thuật ngữ RAG.

**Why this priority**: Người dùng mới là người biết mức độ quan trọng của câu hỏi. Hệ thống không được vô hiệu hóa yêu cầu tìm kỹ chỉ vì bộ phân loại cho rằng câu hỏi đơn giản.

**Independent Test**: Bật `Tìm kỹ hơn` cho cả câu hỏi đơn giản và câu hỏi khó; xác nhận mọi câu đều yêu cầu tầng xếp hạng lại, trạng thái đang chọn được hiển thị rõ, và lựa chọn duy trì trong cuộc hội thoại cho tới khi người dùng đổi lại.

**Acceptance Scenarios**:

1. **Given** người dùng đã chọn `Tìm kỹ hơn`, **When** họ gửi một câu hỏi đơn giản, **Then** hệ thống vẫn yêu cầu tìm kiếm kết hợp cộng xếp hạng lại.
2. **Given** người dùng đã chọn `Tìm kỹ hơn`, **When** bộ đánh giá tự động cho rằng câu hỏi dễ, **Then** lựa chọn của người dùng thắng quyết định tự động.
3. **Given** người dùng đổi từ `Tìm kỹ hơn` về `Tự động`, **When** họ gửi câu tiếp theo, **Then** hệ thống trở lại chính sách tự phân luồng.
4. **Given** người dùng mở lại cùng cuộc hội thoại trong phiên hiện tại, **When** vùng nhập được hiển thị, **Then** mức tìm kiếm đang chọn vẫn rõ ràng và không bị đổi ngầm.

---

### User Story 3 - Biết khi Tìm kỹ không thực hiện được (Priority: P2)

Là người dùng, nếu tầng tìm kỹ bị lỗi, quá thời hạn hoặc không đủ tài nguyên, tôi vẫn nhận được kết quả từ tìm kiếm thông thường nếu an toàn, đồng thời được báo ngắn gọn rằng yêu cầu tìm kỹ chưa được thực hiện đầy đủ.

**Why this priority**: Hạ cấp im lặng tạo cảm giác chắc chắn giả. Hệ thống phải tiếp tục hữu ích nhưng không được nói hoặc ngụ ý rằng đã chạy tìm kỹ khi thực tế chưa chạy.

**Independent Test**: Giả lập thiếu model, hết thời hạn, lỗi suy luận và thiếu bộ nhớ; xác nhận hệ thống hạ cấp có giới hạn, không treo giao diện, không mất dữ liệu riêng tư và hiển thị đúng trạng thái bằng tiếng Việt.

**Acceptance Scenarios**:

1. **Given** hệ thống đã yêu cầu tìm kỹ, **When** tầng xếp hạng lại không sẵn sàng, **Then** hệ thống thử dùng kết quả tìm kiếm kết hợp thông thường và hiển thị thông báo `Đã tìm theo chế độ thường vì Tìm kỹ hiện chưa sẵn sàng`.
2. **Given** cả tìm kiếm thông thường cũng không đủ bằng chứng, **When** hệ thống không thể đưa ra câu trả lời có căn cứ, **Then** hệ thống nói rõ chưa đủ nguồn thay vì bịa hoặc che giấu việc hạ cấp.
3. **Given** lỗi nội bộ có đường dẫn hoặc nội dung nhạy cảm, **When** trạng thái được ghi hoặc hiển thị, **Then** chỉ mã lý do an toàn được sử dụng.

---

### User Story 4 - Vận hành và audit được quyết định phân luồng (Priority: P3)

Là người vận hành hoặc kiểm toán viên, tôi có thể xác minh vì sao một câu hỏi đi đường thường, đường tìm kỹ hoặc bị hạ cấp thông qua dữ liệu chẩn đoán an toàn, mà không thu thập nguyên văn câu hỏi hay nội dung tài liệu.

**Why this priority**: Không có dấu vết quyết định thì không thể phát hiện tình trạng bộ phân luồng luôn coi câu hỏi là dễ, không thể so sánh chất lượng, và không thể chứng minh lựa chọn của người dùng đã được tôn trọng.

**Independent Test**: Chạy bộ câu hỏi định tuyến và kiểm tra mỗi lượt có chế độ do người dùng yêu cầu, chế độ hệ thống yêu cầu, chế độ thực tế, mã lý do, độ trễ từng giai đoạn và trạng thái hạ cấp; không có nội dung nguồn hoặc đường dẫn tuyệt đối.

**Acceptance Scenarios**:

1. **Given** một lượt tìm kiếm hoàn tất, **When** kiểm toán viên xem bản ghi an toàn, **Then** họ phân biệt được `auto_fast`, `auto_deep`, `user_deep` và `degraded`.
2. **Given** bộ phân luồng có dấu hiệu thiên lệch về đường nhanh, **When** chạy báo cáo trên bộ kiểm thử, **Then** tỷ lệ và lỗi phân luồng theo từng nhóm câu hỏi được nhìn thấy rõ.
3. **Given** người dùng yêu cầu Tìm kỹ, **When** kiểm tra bản ghi, **Then** có bằng chứng rằng yêu cầu đó đã được thực hiện hoặc có mã lý do hạ cấp rõ ràng.

### Edge Cases

- Câu hỏi rất ngắn nhưng chứa đại từ phụ thuộc ngữ cảnh trước đó hoặc yêu cầu kiểm chứng tuyệt đối.
- Câu hỏi dài nhưng thực chất chỉ có một phép tra cứu rõ ràng.
- Câu hỏi có nhiều mệnh đề, nhiều dấu hỏi hoặc yêu cầu đối chiếu theo thời gian.
- Câu hỏi yêu cầu `tất cả`, `đầy đủ`, `so sánh`, `mâu thuẫn`, `vì sao`, `nguồn nào`, hoặc trích dẫn nhiều nguồn.
- Kết quả Hybrid có điểm cao nhưng đều đến từ một tài liệu, trong khi câu hỏi cần nhiều nguồn.
- Kết quả Hybrid có nhiều đoạn gần giống nhau, thiếu một phần bắt buộc của câu hỏi, hoặc các nguồn mâu thuẫn.
- Người dùng bật Tìm kỹ cho câu hỏi đơn giản.
- Tầng xếp hạng lại chưa tải xong, hết thời hạn, lỗi giữa chừng hoặc vượt ngân sách tài nguyên.
- Câu hỏi thuộc đường truy vấn Excel có cấu trúc hiện có; đường chuyên dụng này được xét trước chính sách tìm kiếm văn bản thích ứng.
- Không có bằng chứng phù hợp sau cả hai mức tìm kiếm.
- Hai câu hỏi được gửi gần nhau trong khi tiến trình xếp hạng lại đang bận.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Workspace Chat MUST mặc định hiển thị mức tìm kiếm `Tự động` và MUST NOT bắt người dùng chọn tên model, profile hoặc thuật ngữ kỹ thuật.
- **FR-002**: Workspace Chat MUST cung cấp lựa chọn `Tìm kỹ hơn (có thể chậm hơn)` ở vùng nhập câu hỏi, với trạng thái đang chọn luôn nhìn thấy được.
- **FR-003**: Lựa chọn `Tìm kỹ hơn` của người dùng MUST thắng mọi kết luận tự động rằng câu hỏi là dễ và MUST yêu cầu tầng xếp hạng lại cho tới khi người dùng đổi lại `Tự động`.
- **FR-004**: Ở chế độ `Tự động`, quyết định trước truy xuất MUST dựa trên các tín hiệu có thể kiểm thử như số mục tiêu cần trả lời, loại ý định, nhu cầu nhiều nguồn, quan hệ/thời gian/so sánh, tính mơ hồ và yêu cầu kiểm chứng; một model sinh câu trả lời MUST NOT là trọng tài duy nhất.
- **FR-005**: Ở chế độ `Tự động`, hệ thống MUST chạy tìm kiếm kết hợp trước và MUST đánh giá lại độ đầy đủ của bằng chứng bằng các tín hiệu như độ phủ mục tiêu, độ đa dạng nguồn, độ phân biệt giữa ứng viên, trùng lặp và mâu thuẫn.
- **FR-006**: Hệ thống MUST yêu cầu xếp hạng lại khi cổng trước truy xuất đánh giá câu hỏi phức tạp, cổng sau truy xuất đánh giá bằng chứng chưa chắc chắn, hoặc quyết định nằm trong vùng không chắc chắn.
- **FR-007**: Trường hợp được xác định là đường nhanh MUST đáp ứng đồng thời: một mục tiêu rõ ràng, không cần tổng hợp nhiều nguồn, kết quả lần đầu đủ độ phủ, không có tín hiệu mâu thuẫn và quyết định không nằm sát ngưỡng.
- **FR-008**: Hệ thống MUST giữ đường truy vấn Excel có cấu trúc hiện có ở trước bộ phân luồng tìm kiếm văn bản; tính năng này MUST NOT ép truy vấn Excel phù hợp đi qua reranker văn bản.
- **FR-009**: Nếu tầng xếp hạng lại không sẵn sàng, quá thời hạn hoặc lỗi, hệ thống MAY hạ cấp về tìm kiếm kết hợp thông thường nhưng MUST đánh dấu `degraded`, ghi mã lý do an toàn và thông báo cho người dùng bằng tiếng Việt.
- **FR-010**: Hệ thống MUST NOT ghi hoặc hiển thị rằng Tìm kỹ đã hoàn tất nếu tầng xếp hạng lại không thực sự tạo ra bảng xếp hạng cuối cùng.
- **FR-011**: Nếu bằng chứng vẫn không đủ sau đường hiệu lực cuối cùng, hệ thống MUST trả lời có giới hạn hoặc từ chối kết luận thay vì bịa thêm thông tin.
- **FR-012**: Mọi xử lý phân luồng, Hybrid và reranker trong phạm vi tính năng này MUST chạy cục bộ; nội dung câu hỏi, đoạn tài liệu và dữ liệu `local_only` MUST NOT được gửi ra dịch vụ ngoài.
- **FR-013**: Hệ thống MUST bảo vệ máy tham chiếu i5, RAM 16 GB bằng giới hạn số ứng viên, thời hạn, một số lượng tiến trình suy luận bị chặn, tái sử dụng model đã tải và cơ chế ngắt tạm thời sau lỗi tài nguyên lặp lại.
- **FR-014**: Mỗi lượt MUST tạo chẩn đoán an toàn gồm mức do người dùng chọn, mức hệ thống yêu cầu, mức thực tế, mã lý do quyết định, trạng thái hạ cấp, độ trễ Hybrid, độ trễ reranker và số lượng ứng viên; MUST NOT chứa nguyên văn câu hỏi, đoạn tài liệu, thông tin đăng nhập hoặc đường dẫn tuyệt đối.
- **FR-015**: Chính sách phân luồng MUST có bộ kiểm thử gắn nhãn độc lập bao phủ câu dễ, câu khó, câu mơ hồ, câu thiếu bằng chứng, câu nhiều nguồn và yêu cầu Tìm kỹ của người dùng; thay đổi ngưỡng MUST được kiểm thử hồi quy trước khi kích hoạt.
- **FR-016**: Kích hoạt sản xuất MUST bị chặn nếu reranker không cải thiện chất lượng trên tập câu khó, làm giảm chất lượng tập câu dễ vượt ngưỡng cho phép, vượt ngân sách độ trễ/bộ nhớ, làm lộ dữ liệu hoặc không có đường hoàn tác.
- **FR-017**: Hệ thống MUST có một công tắc vận hành cục bộ để tắt định tuyến thích ứng và quay về cấu hình Hybrid đã được phê duyệt mà không phải xây lại chỉ mục tài liệu.
- **FR-018**: Giao diện MUST dùng ngôn ngữ hướng kết quả: `Tự động`, `Tìm kỹ hơn`, `Đang tìm kỹ`, `Đã tìm kỹ`, và thông báo hạ cấp; tên profile kỹ thuật chỉ được phép xuất hiện trong công cụ chẩn đoán dành cho nhà phát triển.

### Key Entities

- **Search Preference**: Lựa chọn người dùng trong cuộc hội thoại, gồm `auto` hoặc `deep`, thời điểm thay đổi và phạm vi hiệu lực.
- **Routing Decision**: Quyết định cho một câu hỏi, gồm yêu cầu của người dùng, kết quả cổng trước truy xuất, kết quả cổng đủ bằng chứng, đường được yêu cầu, đường thực tế và mã lý do.
- **Evidence Sufficiency Assessment**: Đánh giá kết quả Hybrid đầu tiên theo độ phủ, đa dạng nguồn, trùng lặp, mâu thuẫn và độ rõ của thứ hạng.
- **Retrieval Execution Record**: Bản ghi chẩn đoán đã làm sạch, gồm thời gian từng giai đoạn, số ứng viên, trạng thái reranker và hạ cấp; không chứa nội dung người dùng.
- **Adaptive Retrieval Policy**: Phiên bản quy tắc, ngưỡng, ngân sách tài nguyên và trạng thái bật/tắt được dùng để tái hiện quyết định.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên bộ kiểm thử định tuyến có ít nhất 60 câu cân bằng theo nhóm, ít nhất 95% quyết định `Tự động` khớp nhãn đã duyệt và 100% trường hợp ở vùng không chắc chắn được nâng lên Tìm kỹ.
- **SC-002**: 100% câu hỏi gửi khi người dùng bật `Tìm kỹ hơn` ghi nhận yêu cầu Tìm kỹ; không trường hợp nào bị bộ đánh giá tự động hạ xuống đường nhanh.
- **SC-003**: 100% trường hợp reranker lỗi, quá thời hạn hoặc thiếu tài nguyên được hạ cấp minh bạch hoặc trả lời chưa đủ bằng chứng; không có hạ cấp im lặng.
- **SC-004**: Trên tập câu khó đã đóng băng, đường Tìm kỹ cải thiện ít nhất 5% chỉ số xếp hạng bằng chứng chính so với Hybrid, không làm giảm tỷ lệ tìm thấy bằng chứng đúng quá 2%, và không được kích hoạt nếu không đạt.
- **SC-005**: Trên máy tham chiếu i5, RAM 16 GB, đường nhanh có độ trễ p95 không tăng quá 10% so với baseline Hybrid đo lại cùng phiên; đường Tìm kỹ ấm đạt p95 không quá 5 giây, không hết bộ nhớ và luôn chừa ít nhất 2 GB RAM khả dụng trong bài đo tải chuẩn.
- **SC-006**: 100% lượt kiểm thử có thể xác định đường được yêu cầu, đường thực tế và lý do; 0 bản ghi chẩn đoán chứa nguyên văn câu hỏi, đoạn nguồn, đường dẫn tuyệt đối hoặc bí mật.
- **SC-007**: Người dùng thử nghiệm có thể bật Tìm kỹ, nhận biết trạng thái đang dùng và hiểu thông báo hạ cấp trong tối đa 10 giây mà không cần giải thích thuật ngữ kỹ thuật.
- **SC-008**: Công tắc hoàn tác đưa hệ thống về Hybrid đã phê duyệt trong một lần khởi động lại, không xây lại chỉ mục và không làm mất hội thoại hoặc nguồn đã nhập.

## Assumptions

- Workspace Chat là giao diện duy nhất trong phạm vi; không khôi phục Case Cockpit hoặc Habit Studio.
- `Tự động` là mặc định. `Tìm kỹ hơn` là lựa chọn theo cuộc hội thoại và giữ nguyên cho tới khi người dùng đổi lại.
- Bộ đánh giá tự động giai đoạn đầu dùng tín hiệu tất định và kết quả truy xuất; nếu sau này thêm model phân loại, model đó chỉ là tín hiệu phụ và không được quyền hạ cấp yêu cầu Tìm kỹ của người dùng.
- Tìm kiếm Hybrid đã kích hoạt, chỉ mục hiện có và đường Excel có cấu trúc được tái sử dụng.
- Reranker phải là model cục bộ đã ghim phiên bản và checksum; việc tải model từ mạng trong lúc hỏi không nằm trong phạm vi.
- Việc chọn model sinh câu trả lời (ví dụ model cloud) không thuộc tính năng này; tính năng chỉ quyết định tìm và xếp hạng bằng chứng.
- Luôn bật reranker cho mọi câu hỏi, thay đổi ingestion/chunking toàn hệ thống và xây lại chỉ mục là ngoài phạm vi bản đầu.
