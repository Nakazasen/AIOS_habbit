# Kế hoạch triển khai: Phỏng vấn chuyên gia và làm giàu tri thức có kiểm soát

**Mã tính năng**: `010-expert-knowledge-acquisition` | **Ngày**: 2026-09-07 | **Đặc tả**: [spec.md](spec.md)

### 1. Tóm tắt

Xây vòng AI hội thoại thích nghi từ khoảng trống tri thức tới nội dung đã duyệt. C-AGENT qua Brain Gateway lập câu hỏi và hỏi tiếp theo câu trả lời; AIOS giữ danh tính, phạm vi, consent, provenance, phê duyệt và xuất bản. Tri thức mới được dùng ngay qua retrieval sau khi duyệt; fine-tune là nhánh tối ưu có điều kiện, không phải cơ chế lưu sự thật.

Triển khai theo G0–G10 với 81 task. G0 bắt đầu bằng ma trận học có chọn lọc từ STORM/Co-STORM, LangGraph, Microsoft GraphRAG, Microsoft Presidio và hai runtime Whisper; G1 khóa danh tính nhiều chuyên gia trước khi mở dữ liệu thật; G5 khóa audio cục bộ; G8 khóa đường xuất bản vào `library.sqlite`; G9 quyết định có đủ căn cứ fine-tune hay không.

## 2. Bối cảnh kỹ thuật

- **Ngôn ngữ**: Python 3.11; UI Streamlit hiện có; Markdown/JSON UTF-8 cho artifact.
- **AI hội thoại**: gọi model qua Brain Gateway/router theo privacy policy; adapter không hardcode mã model hay nhà cung cấp cố định.
- **Lưu trữ**: `workspace_cases.sqlite` cho workflow metadata; vùng `local_only` riêng cho audio/transcript; `library.sqlite` chỉ cho nội dung đã duyệt; không trộn kho dự đoán/log line.
- **Chép lời**: adapter chạy cục bộ; benchmark `whisper.cpp` và `faster-whisper` trên fixture tiếng Việt trước khi pin engine.
- **Danh tính**: `IdentityProvider` ánh xạ danh tính Windows/OS hoặc OIDC/SSO doanh nghiệp; không tự viết hệ mật khẩu.
- **Kiểm thử**: pytest, contract test, fault injection, privacy negative test, E2E Windows và diễn tập tự động bằng danh tính/chuyên gia fixture.
- **Quy mô bản đầu**: tối đa một phiên phỏng vấn đang ghi âm trên một máy; phiên văn bản có thể tồn tại song song nhưng thao tác duyệt/xuất bản vẫn dùng lease/idempotency.

## 3. Kiểm tra Hiến chương

| Cổng | Kết quả thiết kế |
| --- | --- |
| Tri thức có bằng chứng | Gap, claim, SOP và publication đều dẫn về nguồn/đoạn/actor/digest |
| Ứng viên trước, sự thật sau | Nội dung AI tạo luôn là `candidate`; mâu thuẫn không tự hợp nhất |
| Local-first và đồng ý | Audio/transcript ở máy; ghi âm cần consent; provider route theo nhãn dữ liệu |
| Quyền theo năng lực | Danh tính xác thực + scope grant; title hoặc ID nhập tay không cấp quyền |
| Khả năng thu hồi | Artifact versioned; publication có backup, receipt, revoke/supersede |
| Giao diện tiếng Việt | Chat, lỗi, consent, progress và báo cáo đều bằng tiếng Việt |
| Không over-engineer | Dùng Workspace Chat, Case service và ingest hiện có; chỉ thêm module theo ranh giới thiếu thực sự |

Không xin ngoại lệ Hiến chương. ADR-0009 và bộ mặc định an toàn đã được khóa cho lượt triển khai kỹ thuật; không còn checkpoint chờ người quyết định giữa các cổng.

## 4. Kiến trúc được chọn

```text
Corpus + bộ câu hỏi kiểm tra + case đã xác nhận
                    ↓
      Bản đồ bao phủ và ứng viên khoảng trống
                    ↓ người phụ trách duyệt/giao
 Danh tính xác thực + hồ sơ chuyên gia + scope grant
                    ↓
   Phiên chat thích nghi nhiều vòng của C-AGENT qua Brain Gateway
         ↙ văn bản               ↘ audio có consent
                                   chép lời cục bộ
                    ↓
      Claim có nguồn + xung đột + độ chắc chắn
                    ↓
          SOP / bài học dạng ứng viên
                    ↓ chuyên gia + người duyệt tài liệu
             Gói xuất bản bất biến
                    ↓ backup + writer lease + ingest
              library.sqlite + kiểm thử retrieval
                    ↓
       dùng ngay / thu hồi / thay thế / đánh giá lại
```

### 4.1 Phân vai hệ thống và mô hình AI

- **Gemini Flash 3.8**: Đóng vai trò là **Execution Specialist** viết mã nguồn, kiểm thử, refactor và thực thi theo nhiệm vụ kỹ thuật trong repo `AIOS_habbit`.
- **BGE-M3**: Đóng vai trò mô hình nhúng cục bộ cho RAG v2, chỉ tạo biểu diễn vector, tìm kiếm và xếp hạng đoạn trích (snippets) liên quan theo độ tương đồng.
- **AIOS Runtime**: Lớp kiểm soát tất định (deterministic). Sử dụng kết quả retrieval cùng metadata, version, digest và bộ câu hỏi bao phủ để tạo tín hiệu: thiếu nguồn, thiếu thuộc tính bắt buộc, mâu thuẫn và tài liệu lỗi thời (stale metadata). AIOS tự kiểm tra danh tính, scope và grant; model không tự chọn chuyên gia ngoài danh sách hợp lệ.
- **C-AGENT qua Brain Gateway**: Tiếp nhận gói tín hiệu và bằng chứng có giới hạn để giải thích gap candidate, xếp hạng candidate và sinh câu hỏi thích nghi tiếp theo. Cấu hình C-AGENT được quản lý qua Brain Gateway (không hardcode "Sonnet 4" trong source) và lưu model/provider receipt nếu endpoint phản hồi. Mọi đầu ra không kèm citation hợp lệ đều bị loại. Nếu C-AGENT không sẵn sàng, AIOS giữ nguyên tín hiệu tất định ở trạng thái `candidate`, không gọi cloud thay thế và không làm nghẽn kịch bản fixture.
- **Bảo mật `local_only`**: Dữ liệu `local_only` (âm thanh, bản chép lời thô) chỉ đi qua đường C-AGENT nội bộ được phép; không tự fallback sang cloud.

### 4.2 Ba cửa khóa

1. **Danh tính và phạm vi**: không có verified identity + scope thì không được nhận phiên, xác nhận claim, duyệt hoặc xuất bản.
2. **Dữ liệu phỏng vấn**: audio/transcript thô không rời vùng cục bộ nếu chưa có policy cho phép; consent có thể rút.
3. **Xuất bản tri thức**: candidate/conflicted không vào retrieval thường; chỉ gói đã ký đúng digest mới được ingest.

## 5. Cấu trúc dự kiến

```text
src/aios_habit/
├── expert_identity.py                  # ranh giới identity provider và scope
├── knowledge_coverage.py               # kiểm kê và gap candidate
├── expert_interview_models.py          # model trạng thái nghiệp vụ
├── expert_interview_repository.py      # workflow metadata SQLite
├── expert_interview_service.py         # orchestration và quyền
├── adaptive_interview_engine.py        # máy trạng thái chat
├── local_transcription.py              # protocol + adapter cục bộ
├── knowledge_claim_extractor.py        # claim/provenance/conflict
├── controlled_knowledge_artifact.py    # SOP/lesson candidate, diff, approval
└── knowledge_publication.py            # package, backup, ingest, revoke

tests/fixtures/expert_interview/         # chỉ fixture giả lập, không dữ liệu thật
tests/test_expert_identity.py
tests/test_knowledge_coverage.py
tests/test_adaptive_expert_interview.py
tests/test_local_transcription.py
tests/test_knowledge_claims.py
tests/test_knowledge_publication.py
tests/test_expert_knowledge_e2e.py
```

Không tạo toàn bộ module ngay. G1–G2 chỉ mở các file danh tính/coverage; module sau chỉ được tạo khi cổng trước đạt. UI được nâng trong `workspace_case_ui.py` thay vì dựng app mới.

## 6. Cổng triển khai

| Cổng | Phạm vi | Điều kiện ra |
| --- | --- | --- |
| G0 | Khóa ADR, bộ mặc định, fixture, upstream matrix và baseline | Kiểm thử tài liệu/fixture đạt; tự chuyển G1 |
| G1 | `IdentityProvider`, ExpertProfile, scope grant và negative impersonation | Multi-user fail-closed; disable/revoke có hiệu lực ngay |
| G2 | Kiểm kê corpus, bộ câu hỏi bao phủ và gap candidate | Mọi gap có evidence; không hứa “toàn bộ gap” |
| G3 | InterviewPlan theo gap/chuyên gia/công đoạn | Kế hoạch có budget, câu hỏi nền, tiêu chí dừng và người phù hợp |
| G4 | Chat văn bản thích nghi nhiều vòng | Hỏi tiếp đúng lý do, pause/resume/idempotency, không dẫn dắt/lặp vô hạn |
| G5 | Consent, ghi âm và chép lời cục bộ | Rút consent hoạt động; raw data không rò; thuật ngữ/số bắt buộc sửa xác nhận |
| G6 | Claim, provenance, uncertainty và conflict | 100% claim có nguồn; conflict không tự giải quyết |
| G7 | SOP/bài học candidate, diff và hai lớp duyệt cần thiết | Chưa duyệt không dùng; revoke/supersede đọc lại được |
| G8 | PublicationPackage → backup/lease/ingest → retrieval receipt | Lỗi ghi rollback; citation acceptance đạt; candidate bị chặn |
| G9 | Báo cáo đủ điều kiện fine-tune | Tự kết luận `NOT_APPLICABLE` cho feature 010; không train |
| G10 | Threat model, E2E Windows, diễn tập tự động và full quality gate | SC-001–SC-010 đạt; docs và handover đồng bộ |

## 7. Lộ trình thực hiện

### G0 — Khóa mặc định và dữ liệu thử

Lập ma trận upstream trước khi viết code: học perspective-guided questioning/turn policy từ STORM, checkpoint/human-in-the-loop từ LangGraph, claim provenance từ GraphRAG, redaction defense-in-depth từ Presidio và transcription offline từ Whisper. Chỉ kế thừa pattern/module có license, version và test phù hợp; không copy giao diện hay dựng thêm framework.

Bộ mặc định cố định cho Goal: Windows/OS là nguồn danh tính; tài khoản OS hiện tại là người quản trị hệ thống; người trả lời và người duyệt dùng scope riêng trong fixture; đồng ý ghi âm theo từng phiên; không tự xóa audio/bản chép lời; kiểm thử chỉ xuất bản vào collection fixture; fine-tune tắt và G9 trả `NOT_APPLICABLE`. Tạo fixture thuần giả lập gồm tài liệu đủ/thiếu/xung đột, hội thoại và audio không chứa dữ liệu nhà máy.

### G1–G2 — Nền tin cậy và phát hiện khoảng trống

Làm danh tính trước. Sau đó tạo coverage map từ inventory + câu hỏi chuẩn + kết quả retrieval + case/feedback đã duyệt. AI chỉ xếp hạng và giải thích gap candidate. Reviewer là người quyết định gap nào đáng phỏng vấn.

### G3–G4 — AI phỏng vấn bằng chat

Sinh InterviewPlan có mục tiêu và ngân sách. Máy trạng thái chọn câu hỏi tiếp dựa trên gap và lượt trước; mỗi follow-up phải gắn một lý do hữu hạn. Phiên dừng khi tiêu chí đủ căn cứ đạt, chuyên gia dừng, hết budget hoặc cần escalation.

### G5 — Audio cục bộ

Benchmark hai adapter trên cùng máy và fixture tiếng Việt. Chọn một adapter theo độ đúng thuật ngữ, tốc độ, tài nguyên, khả năng đóng gói và license; không chọn bằng độ phổ biến. Raw audio, transcript máy và transcript đã sửa tách biệt; chỉ bản đã xác nhận mới đi tiếp.

### G6–G8 — Từ lời nói tới tri thức dùng được

Tách claim nguyên tử, giữ uncertainty/conflict, dựng SOP/bài học candidate có citation. Sau duyệt, khóa PublicationPackage rồi gọi đường ingest collection hiện có dưới writer lease và backup. Chạy retrieval acceptance trước khi ghi `PUBLISHED`.

### G9 — Fine-tune có điều kiện

Đo retrieval + prompting trước. Chỉ đề xuất fine-tune nếu có một tác vụ hành vi lặp lại chưa đạt, đủ mẫu đã duyệt/ẩn danh, quyền sử dụng rõ, tập holdout và phương án rollback. Kiến thức sự thật tiếp tục ở library; trọng số chỉ học hành vi/định dạng/phân loại ổn định.

### G10 — Diễn tập và đóng cổng kỹ thuật

Chạy diễn tập tự động theo SC-003/SC-004, negative privacy/authority, E2E Windows và toàn bộ quality gate. Một agent audit ở phiên/vai trò tách biệt kiểm tra rồi tự trả finding cho agent thực thi sửa. Goal kết thúc ở `TECHNICAL_READY`; việc người thật đồng ý ghi âm và duyệt nội dung là vận hành sản phẩm sau đó, không phải cổng phát triển.

## 8. Thứ tự và ước lượng

- G0–G1: 4–7 ngày.
- G2–G3: 5–8 ngày.
- G4: 5–8 ngày.
- G5: 4–7 ngày.
- G6–G8: 8–13 ngày.
- G9–G10: 4–7 ngày cho đánh giá và diễn tập tự động.

Tổng kỹ thuật dự kiến **30–50 ngày làm việc**. Goal tự tiếp tục qua các cổng; khả năng phụ thuộc thiết bị/tài khoản thật giữ feature flag tắt nếu môi trường không có, nhưng không chặn các nhánh kỹ thuật còn lại hoặc diễn tập fixture.

## 9. Tài liệu thiết kế và thực thi

- Quyết định công nghệ: [research.md](research.md).
- Mô hình dữ liệu: [data-model.md](data-model.md).
- Hợp đồng vòng nghiệp vụ: [contracts/expert-knowledge-loop.md](contracts/expert-knowledge-loop.md).
- Hợp đồng danh tính/consent: [contracts/identity-consent-and-privacy.md](contracts/identity-consent-and-privacy.md).
- Kịch bản xác minh: [quickstart.md](quickstart.md).
- Danh sách việc: [tasks.md](tasks.md).
- Chỉ dẫn chạy liên tục cho Gemini: [GEMINI_FLASH_3_8_GOAL.md](GEMINI_FLASH_3_8_GOAL.md).

## 10. Hoàn tác

- Tắt feature flag và multi-user adapter; quay về quy trình ExpertRequest/ExpertReview hiện có.
- Giữ raw interview trong vùng cục bộ; mặc định không tự xóa và cho người có quyền xóa thủ công.
- Thu hồi publication bằng receipt/version, phục hồi backup nếu ingest hỏng và re-index collection.
- Nếu adapter danh tính thật chưa chạy trên máy dev, giữ multi-user thật tắt, hoàn tất contract bằng fixture và tiếp tục; không dùng actor tự khai để đi vòng.
- Nếu transcription local chưa chạy trên máy dev, giữ audio thật tắt, hoàn tất adapter/fixture và tiếp tục chat văn bản; không đưa transcript sai vào tri thức.
