# Nghiên cứu và quyết định: Vòng trí nhớ công việc thích nghi

## 1. Baseline đã xác minh

- `build_workspace_ai_prompt()` trong `src/aios_habit/workspace_chat_ai_answer.py` hiện chỉ nhận câu hỏi, lịch sử chat và nguồn của request; chưa có trí nhớ trước câu trả lời.
- `MemoryUnit` trong `src/aios_habit/core.py` đã có trạng thái `verified` và bắt buộc evidence cho trạng thái này.
- `SeniorLearningCard` trong `src/aios_habit/learning_models.py` đã có `confidence=confirmed`, vùng áp dụng, vùng không áp dụng, evidence và retrieval keywords nhưng hiện chủ yếu phục vụ case.
- `CaseLesson` đã có `approved/revoked` và `WorkspaceCaseService.search_approved_lessons()`.
- Goal 010 đã có artifact approved, publication an toàn và FTS trong thư viện; các task đóng Goal còn mở không ngăn Goal 011 đọc những artifact riêng lẻ đã đủ điều kiện.
- Graphify nối các god node `Workspace`, `Case`, `learning_models.py` và `memory_unit.schema.json`; điều này củng cố phương án dùng lớp đọc qua các nguồn hiện hữu thay vì tạo kho trí nhớ mới.

## 2. Quyết định 1 — Định nghĩa “thông minh dần”

**Quyết định**: Đo bằng việc tái sử dụng đúng tri thức đã xác nhận, giảm lặp lỗi và tiếp tục công việc qua phiên. Không dùng khái niệm tự huấn luyện model trong Goal 011.

**Lý do**: Repo đã có tài sản học nhưng thiếu vòng đọc trước câu trả lời. Khép mắt xích này tạo giá trị trực tiếp, kiểm toán được và chạy được trên CPU.

**Phương án đã xem xét**:

- Fine-tune định kỳ: loại vì cần dữ liệu lớn, GPU, đánh giá drift và rollback model.
- Cho LLM tự tóm tắt toàn bộ chat thành memory: loại vì dễ học sai và vi phạm consent.
- Chỉ lưu chat history dài hơn: loại vì không tạo tri thức có cấu trúc và tăng rò rỉ/ngữ cảnh nhiễu.

## 3. Quyết định 2 — Một lớp đọc, không một kho mới

**Quyết định**: `WorkspaceMemoryService` tạo view chuẩn hóa từ ba nguồn nền: verified `MemoryUnit`, confirmed `SeniorLearningCard`, approved `CaseLesson`; adapter thứ tư đọc Goal 010 artifact còn được xuất bản khi nguồn này sẵn sàng. Dữ liệu gốc không bị chuyển hoặc sao chép hàng loạt.

**Lý do**: Mỗi nguồn có lifecycle riêng. Một nguồn tùy chọn chưa sẵn sàng không được khóa các nguồn khác. Hợp nhất vật lý sẽ tạo migration, đồng bộ trạng thái và nguy cơ stale duplicate không cần thiết.

**Phương án đã xem xét**:

- Một SQLite/vector database mới: loại ở MVP vì trùng dữ liệu, tăng migration và không cần cho 10.000 mục.
- Chỉ dùng thư viện Goal 010: loại vì bỏ qua MemoryUnit, SeniorLearningCard và CaseLesson đã có.
- Gọi trực tiếp từng nguồn ngay trong prompt builder: loại vì trộn persistence/privacy vào hàm dựng prompt và khó kiểm thử.

## 4. Quyết định 3 — Tìm từ khóa xác định trước

**Quyết định**: Chuẩn hóa Unicode, bỏ khác biệt hoa/thường và khoảng trắng, tách token; chấm trọng số cho title, tags/retrieval keywords, applies_when và nội dung. Source-specific FTS hiện có chỉ dùng để lấy candidate; service xếp hạng cuối theo một công thức ổn định.

**Lý do**: Không cần GPU/model, cold start thấp, dễ giải thích “vì sao được nhớ lại”, đủ để kiểm chứng mắt xích P3 trước khi đầu tư retrieval sâu.

**Phương án đã xem xét**:

- BGE-M3 hoặc reranker: hoãn vì laptop không GPU, model lớn và benchmark hiện tại chưa chứng minh cần thiết cho memory loop.
- GraphRAG/LightRAG: hoãn vì bài toán đầu tiên là eligibility và vòng phản hồi, không phải quan hệ đa bước.
- LIKE đơn giản trên toàn bộ field: không chọn làm công thức cuối vì khó xếp hạng và kém ổn định với tiếng Việt.

## 5. Quyết định 4 — Chính sách đủ điều kiện và xung đột

**Quyết định**: Lọc eligibility trước khi score. Trạng thái nguồn là quyền lực hơn điểm liên quan. Hai mục mâu thuẫn đủ điều kiện không tự phân thắng; kết quả mang `conflict` và prompt yêu cầu kiểm tra nguồn hiện tại.

**Lý do**: Một điểm semantic cao không biến draft/revoked thành tri thức đúng. Fail-closed phù hợp Constitution.

**Phương án đã xem xét**:

- “Mới nhất luôn thắng”: loại vì độ mới không chứng minh độ đúng.
- “Nguồn Goal 010 luôn thắng”: loại vì loại nguồn không thay thế scope/evidence.
- Cho model quyết định: loại vì không xác định và khó audit.

## 6. Quyết định 5 — Ranh giới riêng tư và consent

**Quyết định**: Mỗi item có `privacy_classification` và `export_allowed`. Cloud path chỉ nhận item được phép xuất; local path chỉ nhận `local_only` khi caller chọn rõ. Tập item được gửi là một phần consent fingerprint; tập thay đổi thì yêu cầu xác nhận lại.

**Lý do**: Trí nhớ được gọi lại tự động không đồng nghĩa người dùng đã đồng ý gửi ra ngoài ở lần hiện tại.

**Phương án đã xem xét**:

- Dùng consent của source đang bật cho mọi memory: loại vì memory không nhất thiết thuộc source đó.
- Gửi metadata nhưng không content: hữu ích cho audit nhưng không giúp model trả lời.
- Chặn toàn bộ memory khỏi cloud: an toàn nhưng loại cả verified/exportable memory; giữ làm rollback nếu contract consent không đạt audit.

## 7. Quyết định 6 — Lưu quyết định mới bằng log cục bộ nhỏ

**Quyết định**: US1 không ghi gì. Từ US2, ghi append-only JSONL dưới `local_cases/workspace_memory/`; record mới supersede record cũ bằng ID/digest, không sửa hoặc xóa lịch sử. Mỗi append tái sử dụng trực tiếp `LibraryWriterLease` trong `src/aios_habit/workspace_chat_store.py` với runtime dir là `local_cases/workspace_memory/`. Không tạo lớp khóa mới.

**Lý do**: Không tạo database hoặc cơ chế khóa mới; dễ export/inspect; mọi dữ liệu người dùng ở ngoài Git. `LibraryWriterLease` đã dùng `msvcrt` trên Windows và `fcntl` trên POSIX, nên đủ cho lượng ghi thấp chỉ xảy ra khi xác nhận.

**Phương án đã xem xét**:

- Ghi vào `05_memory_vault`: loại vì đây là artifact repo, dễ đưa dữ liệu người dùng vào Git.
- Thêm bảng vào `workspace_cases.sqlite`: hoãn vì trí nhớ không nhất thiết thuộc case và sẽ làm migration Goal 008 nặng hơn.
- Ghi đè một JSON snapshot: loại vì mất lịch sử quyết định.
- Tạo helper/file-lock abstraction mới: loại vì `LibraryWriterLease` đã cung cấp khóa liên tiến trình và release an toàn.

## 8. Quyết định 7 — Chia lát cắt và kiểm toán

**Quyết định**: Grok thực hiện tuần tự US1 đọc-only → US2 nhớ/quên → US3 sửa sai, chạy test và ghi checkpoint sau từng phần nhưng không chờ audit giữa phần. Codex kiểm toán độc lập toàn Goal một lần sau khi Grok bàn giao.

**Lý do**: Ba phần tạo thành một vòng học hoàn chỉnh và cùng nằm trong một Goal đã được duyệt. Checkpoint test giữ lỗi cục bộ; một audit cuối giữ đúng phân vai mà không tạo năm lần bàn giao.

**Phương án đã xem xét**:

- Làm cả Goal trong một commit: loại; Grok phải giữ ba nhóm thay đổi logic riêng dù thực hiện trong cùng Goal.
- Làm remember/write trước recall: loại vì tạo thêm dữ liệu mà chưa chứng minh có đường dùng.
- Thêm bàn giao phiên: hoãn vì không cần để khép vòng nhớ–gọi lại–sửa sai.

## 9. Điều kiện xem xét nâng cấp retrieval sau Goal

Chỉ mở Goal khác cho vector/graph khi bộ 30+ tình huống cho thấy lexical recall dưới 90% hoặc tỷ lệ false positive vượt ngưỡng SC-002 dù eligibility, field weights và synonyms curated đã được điều chỉnh. Mọi challenger phải chạy A/B với cùng fixture, có giới hạn RAM/latency và rollback về lexical.
