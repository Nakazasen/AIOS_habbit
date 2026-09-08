# Nghiên cứu và quyết định kỹ thuật

## 0. Ma trận học từ hệ trưởng thành

Trước khi code, Gemini phải đọc kiến trúc, test và license ở commit/tag được pin; ưu tiên học pattern rồi nối vào ranh giới AIOS. Không chép toàn repo, UI, thương hiệu hoặc kéo dependency khi vài cấu trúc dữ liệu/hợp đồng là đủ.

| Repo nguồn | Pin Tag / Commit | Giấy phép (License) | Adopt (Kế thừa trực tiếp) | Adapt (Thích nghi vào AIOS) | Reject (Từ chối / Loại bỏ) | So sánh năng lực với AIOS & Chi phí bảo trì |
| --- | --- | --- | --- | --- | --- | --- |
| [Stanford STORM/Co-STORM](https://github.com/stanford-oval/storm) | Tag `v1.1.2` (commit `7d7d56e`) | MIT | Tư duy hỏi đa góc nhìn (multi-perspective querying), chiến lược câu hỏi follow-up dựa trên thông tin thiếu. | Thuật toán discourse turn policy và rubric kiểm tra độ đầy đủ thích nghi vào `AdaptiveInterviewEngine`. | Không giả lập chuyên gia bằng LLM; không dùng pipeline sinh bài viết kiểu Wikipedia tự động; không kéo dspy/storm dependencies nặng. | AIOS đã có cấu trúc Case/Task; chỉ cần thuật toán follow-up thích nghi; chi phí bảo trì thấp nếu không kéo thư viện. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Tag `v0.2.20` (commit `a92f03c`) | MIT | Bất biến máy trạng thái bền vững (durable execution), semantics checkpoint & resume, ngắt tương tác con người (human-in-the-loop interrupt). | Máy trạng thái `AdaptiveInterviewEngine` lưu checkpoint append-only vào `workspace_cases.sqlite`, gắn idempotency key. | Không cài đặt framework `langgraph` hoặc `langchain` vào repo; không phụ thuộc các abstraction graph phức tạp. | AIOS đã có SQLite Event Sourcing & Repository pattern; tự cài đặt FSM chuẩn nhẹ hơn, không phát sinh technical debt. |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | Tag `v0.3.2` (commit `6f8b1d9`) | MIT | Cấu trúc đơn vị văn bản nguồn (TextUnit / source references), mô hình claim nguyên tử, mốc thời gian và provenance breadcrumbs. | Khái niệm `TranscriptSegment` và `KnowledgeClaim` liên kết nguồn gốc với mã kiểm tra nội dung (digest) trong `knowledge_claim_extractor.py`. | Không thay thế kho vector/lexical RAG v2 hoặc `library.sqlite` bằng Graph database cồng kềnh; không dùng pipeline tài liệu mở. | AIOS đã có `library.sqlite` và RAG v2; chỉ cần lớp biểu diễn claim nguyên tử để truy nguyên nguồn gốc. |
| [Microsoft Presidio](https://github.com/microsoft/presidio) | Tag `v2.2.354` (commit `b54c82a`) | MIT | Khái niệm pattern recognizer cho dữ liệu nhạy cảm cục bộ; quy tắc dán nhãn privacy (privacy labeling). | Bộ lọc kiểm tra vệ sinh dữ liệu fixture và quét từ ngữ trọng yếu (`test_expert_interview_fixture_hygiene.py`). | Không kéo toàn bộ runtime Presidio/spaCy nặng vào môi trường; không dùng detector cloud; giữ nguyên tắc `local_only` gốc. | AIOS vận hành nguyên tắc fail-closed local-only; regex và pattern định danh chuyên biệt nhẹ hơn nhiều so với kéo cả NLP stack. |
| [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp) | Tag `v1.7.1` (commit `69e46a3`) | MIT | Ranh giới CLI/subprocess boundary, binary độc lập cho Windows chạy 100% offline không cần GPU hay Python runtime nặng. | Subprocess adapter trong `local_transcription.py` với cấu hình đường dẫn an toàn và timeout bảo vệ. | Không nhúng C API trực tiếp bằng CFFI/ctypes; không tự biên dịch động trong quá trình chạy. | Thích hợp với máy trạm Windows Core i5/16GB không GPU của AIOS; dễ đóng gói và cô lập lỗi subprocess. |
| [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) | Tag `v1.0.3` (commit `f81b1c5`) | MIT | Khái niệm word-level timestamps, Voice Activity Detection (VAD) và hotwords cho thuật ngữ công đoạn sản xuất. | Đo đạc đối chứng trong kịch bản benchmark tiếng Việt (`scripts/benchmark_local_transcription.py`). | Không bắt buộc cài đặt CTranslate2 nếu hệ thống thiếu môi trường; không chặn chat chữ nếu thiếu engine chép lời. | Được dùng làm phương án so sánh benchmark; nếu môi trường không tương thích thì fallback an toàn về text chat. |

Thứ tự ưu tiên tái sử dụng: API/module hiện có của AIOS → pattern và test từ upstream → adapter mỏng → dependency pin phiên bản. Tuyệt đối không copy code tùy tiện; chỉ kế thừa pattern kiến trúc và triển khai tinh gọn theo chuẩn nội bộ AIOS.

## 1. Cách hệ thống “học”

### Quyết định

Dùng hai vòng tách biệt:

1. **Học tri thức vận hành**: claim/SOP/bài học đã duyệt được xuất bản có version vào collection và dùng ngay qua retrieval.
2. **Học trọng số**: chỉ mở Gate Card fine-tune riêng khi G9 chứng minh một tác vụ hành vi ổn định không đạt bằng retrieval/prompting.

### Lý do

Tri thức công đoạn thay đổi, cần citation và phải thu hồi được. Fine-tune không phải kho dữ kiện đáng tin, khó xóa một phát biểu và có nguy cơ học cả lỗi transcript. Retrieval đáp ứng cập nhật nhanh, provenance và rollback. Fine-tune chỉ hợp lý cho hành vi lặp lại như phân loại loại gap, giữ cấu trúc output hoặc chuẩn hóa thuật ngữ sau khi có tập mẫu sạch.

### Phương án loại

- Tự fine-tune sau mỗi buổi: không có holdout, khó rollback, dễ khuếch đại sai sót và vướng quyền sử dụng dữ liệu.
- Không có fine-tune vĩnh viễn: loại vì có thể bỏ lỡ cải thiện sau khi đủ dữ liệu; thay bằng cổng đủ điều kiện rõ ràng.

## 2. Phát hiện khoảng trống tri thức

### Quyết định

Kết hợp kiểm kê tất định với AI xếp hạng:

- Taxonomy công đoạn/thiết bị/lỗi và nguồn tài liệu đã biết.
- Bộ câu hỏi bao phủ có expected evidence.
- Kết quả retrieval không đủ citation, nguồn mâu thuẫn/lỗi thời và case thật đã xác nhận.
- AI gom nhóm, diễn giải và ưu tiên thành `KnowledgeGapCandidate`.

### Lý do

Không có cách đáng tin để chứng minh “toàn bộ lỗ hổng” trong một kho mở. Coverage map làm rõ đã đo phần nào; AI giúp tìm mẫu và ưu tiên nhưng mỗi gap vẫn cần evidence và reviewer.

### Phương án loại

- Chỉ hỏi model “kho còn thiếu gì”: nhanh nhưng không kiểm chứng phạm vi và sinh khoảng trống tưởng tượng.
- Chỉ dùng danh sách checklist thủ công: đáng tin nhưng không tận dụng case/retrieval mới và tốn công duy trì.

## 3. Điều khiển hội thoại nhiều vòng

### Quyết định

Dùng máy trạng thái hữu hạn do AIOS kiểm soát. C-AGENT qua Brain Gateway đề xuất `next_action` có schema và lý do; service kiểm tra scope, budget và transition trước khi hiển thị câu hỏi.

Các lý do follow-up được phép: thiếu điều kiện, thiếu ngưỡng/đơn vị, thiếu ngoại lệ, thiếu ví dụ/phản ví dụ, chưa rõ độ chắc chắn, thiếu nguồn hoặc phát hiện mâu thuẫn. Mỗi phiên có giới hạn lượt, thời gian và token.

### Lý do

Giữ được chat tự nhiên nhưng tránh loop vô hạn, hỏi ngoài phạm vi và model tự đánh dấu hoàn tất. Checkpoint/idempotency giúp pause/resume an toàn.

### Phương án loại

- Form cố định: không xử lý câu trả lời mơ hồ và không phải trải nghiệm chat thích nghi.
- Agent tự do hoàn toàn: khó audit, khó giới hạn chi phí và dễ dẫn dắt chuyên gia.

## 4. Danh tính nhiều chuyên gia

### Quyết định

Tạo interface `IdentityProvider`, không tạo mật khẩu riêng. Thứ tự spike:

1. Windows/OS identity cho triển khai nội bộ một máy/domain.
2. OIDC/SSO doanh nghiệp khi cần nhiều máy hoặc chính sách tập trung.
3. `local_admin` hiện có chỉ cho chế độ một người dùng, không được trình bày như multi-user.

`ExpertProfile` ánh xạ principal đã xác thực tới năng lực; `ScopeGrant` quyết định hành động/phạm vi/thời hạn. Không ánh xạ được thì deny.

### Lý do

Xác thực và vòng đời tài khoản là hạ tầng bảo mật chuyên dụng. Viết hệ password mới tăng rủi ro mà không tạo giá trị miền.

## 5. Ghi âm và chép lời

### Quyết định tạm thời

Thiết kế adapter cục bộ và benchmark hai ứng viên trước khi khóa:

- [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp): hỗ trợ Windows và chạy hoàn toàn cục bộ; phù hợp gói nhẹ, ranh giới subprocess rõ.
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper): có word timestamps, VAD và hotwords; thuận lợi cho thuật ngữ/mốc thời gian nhưng thêm runtime Python/CTranslate2.

Model gốc Whisper hỗ trợ nhận dạng tiếng nói đa ngôn ngữ theo [tài liệu chính thức](https://github.com/openai/whisper). Quyết định cuối dựa trên fixture tiếng Việt có tiếng ồn, mã máy, đơn vị và số; đo CPU/GPU/RAM, thời gian, độ ổn định timestamps, đóng gói Windows, license và khả năng chạy offline.

### Chốt an toàn

- Không tải audio lên dịch vụ cloud trong bản đầu.
- Ghi âm cần consent rõ ràng và chỉ báo đang ghi.
- Transcript máy không đi thẳng vào claim; chuyên gia sửa/xác nhận các token quan trọng.
- Nếu cả hai engine không đạt ngưỡng sử dụng, giữ chat văn bản và chặn audio thay vì chọn đại.

## 6. Lưu trữ

### Quyết định

- `workspace_cases.sqlite`: gap/interview/approval/publication metadata, ID và digest cần audit.
- Vùng `local_only` do owner chọn: audio, transcript máy và bản sửa; không commit.
- `library.sqlite`: chỉ nội dung đã duyệt sau publication package.
- Không đưa raw interview vào `line_events.sqlite` hoặc `production_prediction.sqlite`.

### Lý do

Giữ đúng ADR-0007, giảm phạm vi rò rỉ và cho phép retention raw khác retention tri thức chính thức.

## 7. Tạo SOP và xuất bản

### Quyết định

Tạo `KnowledgeClaim` nguyên tử trước, rồi mới dựng `KnowledgeArtifactCandidate`. Mọi dòng/section của SOP phải dẫn được tới claim và source segment. Sau duyệt, tạo `PublicationPackage` bất biến, backup collection, lấy writer lease, ingest qua pipeline hiện có, chạy `quick_check` và câu hỏi retrieval acceptance.

### Lý do

Không ghi trực tiếp SQL vào `library.sqlite`; dùng lại đường ingest và bảo vệ concurrency/backup sẵn có. Claim layer giúp phát hiện mâu thuẫn và diff khi source thay đổi.

## 8. Điều kiện mở fine-tune

G9 chỉ cho phép tạo Gate Card fine-tune riêng khi đồng thời đạt:

- Có tác vụ mục tiêu cụ thể và metric baseline, không dùng mục tiêu chung “thông minh hơn”.
- Retrieval + prompt/schema vẫn không đạt ngưỡng sau tuning hợp lý.
- Có tập mẫu đã duyệt, ẩn danh, có quyền sử dụng, đủ lớn theo learning curve thực đo.
- Có train/dev/holdout tách nguồn/chuyên gia để chống leakage.
- Không chứa raw audio/transcript, secret hoặc dữ liệu `local_only` chưa được phép.
- Có canary, rollback về base model và cách vô hiệu hóa adapter/checkpoint.

Nếu thiếu một điều kiện, kết luận `NOT_APPLICABLE`; hệ vẫn học tri thức qua library và chat bằng C-AGENT qua Brain Gateway bình thường.

## 9. Bộ mặc định đã khóa cho Goal tự chạy

1. Dùng Windows/OS identity; adapter fixture chỉ dành cho test.
2. Tài khoản OS hiện tại là quản trị hệ thống; quyền trả lời, xác nhận và xuất bản là các scope tách biệt.
3. Ghi âm chỉ khi đồng ý theo từng phiên; rút đồng ý dừng ngay; từ chối vẫn chat chữ.
4. Audio và bản chép lời ở local-only root; không tự xóa, cho người có quyền xóa thủ công.
5. Test dùng collection fixture; runtime dùng collection đang chọn và kiểm tra quyền publish/revoke.
6. Fine-tune tắt; G9 tự kết luận `NOT_APPLICABLE` và không tạo training job.

Bộ mặc định này giúp quá trình phát triển không chờ quyết định. Khi triển khai doanh nghiệp muốn đổi sang OIDC, lịch xóa tự động hoặc fine-tune, đó là Goal cấu hình/kiểm toán riêng, không làm phình feature 010.
