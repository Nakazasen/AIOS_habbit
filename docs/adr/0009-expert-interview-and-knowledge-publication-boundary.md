# ADR-0009: Ranh giới phỏng vấn chuyên gia và xuất bản tri thức

Status: `ACCEPTED`  
Owner role: Project owner / Architecture reviewer / Privacy reviewer  
Xem xét lần cuối: 2026-09-07  
Chu kỳ xem xét: Trước khi bắt đầu G1 hoặc khi thay đổi ranh giới identity, consent hay publication

## Bối cảnh

Vòng Case hiện có hỗ trợ yêu cầu chuyên gia, ghi quyết định và tạo lesson candidate có người duyệt. Nó chưa có phát hiện gap toàn kho, chat thích nghi, audio/transcription, danh tính nhiều chuyên gia thật hoặc đường xuất bản tri thức đã duyệt vào collection.

Nếu nối thẳng model với transcript và `library.sqlite`, một câu nói sai, mạo danh hoặc chép lời sai có thể trở thành căn cứ trả lời. Nếu tự xây tài khoản/password trong feature, phạm vi bảo mật tăng mạnh và trái ranh giới fail-closed của ADR-0007.

## Động lực quyết định

- Tạo AI phỏng vấn thực sự, không phải form cố định.
- Học tri thức mới nhanh nhưng vẫn có citation, phê duyệt và rollback.
- Bảo vệ audio/transcript và danh tính chuyên gia.
- Dùng lại Case/authorization/collection ingest/backup/lease hiện có.
- Giữ fine-tune ở đúng vai trò: tối ưu hành vi khi có dữ liệu đủ sạch, không làm kho sự thật.

## Các phương án

### A. Model tự phỏng vấn rồi ghi thẳng vào thư viện

Nhanh nhất nhưng không có ranh giới danh tính, consent, provenance và phê duyệt. Không chọn.

### B. Form câu hỏi cố định, người quản trị tự nhập SOP

An toàn hơn nhưng không đáp ứng chat nhiều vòng/tự hỏi tiếp và không giảm đủ công sức thu nhận kiến thức. Không chọn làm đích; chỉ dùng fallback khi model lỗi.

### C. Vòng candidate → review → publication có ba cửa khóa

AI đề xuất gap/câu hỏi/claim/SOP; AIOS kiểm soát identity, raw data và publication. Chọn.

## Quyết định

1. **Danh tính**: mọi multi-user action đi qua `IdentityProvider` và ánh xạ principal xác thực tới `ExpertProfile`/`ScopeGrant`. Không có ánh xạ thì deny; không fallback `local_admin` khi multi-user bật.
2. **Hội thoại**: Gemini điều khiển câu hỏi thích nghi nhưng AIOS giữ finite-state machine, budget, transition và idempotency. Model không trực tiếp ghi event hoặc tự tuyên bố approval.
3. **Dữ liệu thô**: audio/transcript là `local_only`, nằm ngoài Git, case DB và library. Case chỉ giữ locator/digest/consent metadata được phép.
4. **Tri thức**: transcript sinh `KnowledgeClaim` và artifact `candidate`; conflict không tự hòa giải. Chỉ artifact đã duyệt đúng scope/digest được seal thành publication package.
5. **Xuất bản**: publication dùng backup, `LibraryWriterLease`, đường ingest collection hiện có, SQLite integrity check và retrieval acceptance. Không cho model ghi SQL trực tiếp.
6. **Học**: nội dung đã duyệt được dùng ngay qua retrieval. Fine-tune tắt trong feature 010; G9 ghi `NOT_APPLICABLE`, còn huấn luyện bổ sung tương lai dùng Goal riêng.
7. **Mặc định triển khai**: Windows/OS identity; đồng ý ghi âm từng phiên; không tự xóa raw data; collection fixture khi test; agent audit tách biệt tự trả finding; không có checkpoint chờ con người trong chuỗi phát triển.

## Hệ quả

### Tích cực

- Có chat AI linh hoạt nhưng vẫn audit/rollback được.
- Tri thức mới có thể dùng ngay mà không cần huấn luyện lại model.
- Danh tính, consent và quyền duyệt độc lập với prompt/model.
- Audio có thể bị chặn mà chat văn bản vẫn tạo giá trị.

### Chi phí

- Identity thật và thao tác consent/approval được cấu hình khi vận hành; chuỗi phát triển dùng fixture và bộ mặc định đã khóa.
- Phải xây claim/provenance/publication lifecycle, không chỉ UI chat.
- Fine-tune chậm hơn mong muốn vì cần dataset/evaluation riêng.

## Bảo mật và quyền riêng tư

- Identity provider lỗi, grant thiếu/hết hạn/revoked đều fail-closed.
- Không ghi âm trước consent; rút consent dừng capture.
- Không gửi audio thô tới cloud ở bản đầu.
- Không log raw transcript, đường dẫn tuyệt đối, secret hoặc traceback.
- Raw data không vào Git và không được dùng train nếu thiếu consent/quyền sử dụng.
- Candidate/conflicted/revoked bị lọc khỏi retrieval thường.

## Khôi phục

- Tắt feature flags, giữ luồng ExpertRequest/ExpertReview hiện có.
- Gỡ identity adapter mới mà không đổi dữ liệu Case cũ.
- Thu hồi/re-index publication hoặc phục hồi collection backup.
- Khi transcription không đạt, khóa audio và giữ chat văn bản.
- Khi máy dev thiếu tài khoản OS thật, giữ multi-user runtime tắt, hoàn tất contract bằng fixture và tiếp tục; không giảm chuẩn xác thực.

## Bằng chứng và liên kết

- [Đặc tả 010](../../specs/010-expert-knowledge-acquisition/spec.md)
- [Kế hoạch 010](../../specs/010-expert-knowledge-acquisition/plan.md)
- [Hợp đồng danh tính/consent](../../specs/010-expert-knowledge-acquisition/contracts/identity-consent-and-privacy.md)
- [ADR-0007](0007-evidence-case-loop-boundaries.md)
- [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp)
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)
