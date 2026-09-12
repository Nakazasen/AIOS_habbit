# Kế hoạch triển khai: Vòng trí nhớ công việc thích nghi

**Nhánh**: `011-adaptive-work-memory` | **Ngày**: 2026-09-12 | **Đặc tả**: [spec.md](spec.md)  
**Đầu vào**: Đặc tả tại `specs/011-adaptive-work-memory/spec.md`  
**Trạng thái**: `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`

## Tóm tắt

Mục tiêu là khép một vòng học tối thiểu “làm việc → xác nhận bài học → gọi lại trước câu trả lời → sửa sai” trên Workspace Chat. Grok thực hiện toàn bộ phần Execution theo thứ tự trong một Goal có thể tiếp tục từ task chưa xong; Codex kiểm toán độc lập một lần ở cuối. Việc bàn giao phiên và retrieval nâng cao được hoãn để tránh thiết kế thừa.

Giải pháp không thêm model, vector database, reranker, dịch vụ nền hoặc nhà cung cấp. Trạng thái nguồn vẫn nằm ở kho hiện có; Goal 011 chỉ bổ sung lớp đọc thống nhất và các quyết định cục bộ, có nguồn gốc, xác nhận rõ ràng.

## Bối cảnh kỹ thuật

**Ngôn ngữ/Phiên bản**: Python 3.11  
**Phụ thuộc chính**: thư viện chuẩn Python (`dataclasses`, `json`, `pathlib`, `sqlite3`, `unicodedata`, `hashlib`), Streamlit và các module AIOS hiện có  
**Lưu trữ**: đọc `05_memory_vault/memory_units.jsonl`, `local_cases/learning_cards.jsonl`, `local_cases/workspace_cases.sqlite` và thư viện Goal 010 hiện hành; từ US2, quyết định mới dùng JSONL append-only dưới `local_cases/workspace_memory/` và tái sử dụng `LibraryWriterLease` hiện có khi ghi  
**Kiểm thử**: pytest, kiểm thử hợp đồng prompt, kiểm thử tích hợp Workspace Chat, bộ dữ liệu gắn nhãn và benchmark CPU xác định  
**Nền tảng đích**: Windows laptop, CPU i5, RAM 16 GB, không GPU; vẫn tương thích môi trường Python được repo hỗ trợ  
**Loại dự án**: ứng dụng cục bộ Workspace Chat  
**Mục tiêu hiệu năng**: p95 tìm trong 10.000 mục dưới 500 ms; phần tăng working set không quá 200 MB; không tải model  
**Ràng buộc**: local-first; fail-closed; tiếng Việt trên UI; không lộ traceback/đường dẫn; khi tắt feature flag phải giữ baseline prompt; không import `studio` hoặc `case_cockpit`  
**Quy mô/Phạm vi**: một người dùng hoặc nhóm nhỏ tin cậy, tối đa 10.000 mục cục bộ; tối đa 5 mục và 4.000 ký tự mỗi prompt

## Kiểm tra Constitution

*Cổng phải đạt trước nghiên cứu và được kiểm lại sau thiết kế.*

| Nguyên tắc | Trạng thái | Cách đáp ứng |
|---|---|---|
| Bằng chứng trước khẳng định | `PASS_CONDITIONAL` | Chỉ trạng thái đủ điều kiện và có tham chiếu bằng chứng được gọi lại; ứng viên không vào prompt. |
| Riêng tư local-first và đồng ý | `PASS_CONDITIONAL` | Phân loại từng mục trước khi đóng gói; `local_only` không đi cloud; thay đổi tập mục làm hết hiệu lực xác nhận cũ. |
| Tri thức mở, có thể mang theo | `PASS` | Giữ JSON/JSONL/SQLite hiện có, schema và provenance công khai; không phụ thuộc provider. |
| Workspace Chat và tiếng Việt | `PASS_CONDITIONAL` | Chỉ tích hợp Workspace Chat; mọi UI/lỗi tiếng Việt; quét chuỗi người dùng. |
| Kỷ luật thay đổi và chất lượng | `PASS_CONDITIONAL` | Goal 011 có test/checkpoint riêng; Goal 010 chỉ là nguồn tùy chọn và không phải cổng toàn Goal. |
| Ranh giới legacy | `PASS` | Không gọi hoặc import `studio`, `case_cockpit`. |
| Phân vai | `PASS_CONDITIONAL` | Grok là Execution Specialist; Codex là Audit Specialist; một vai không tự đánh dấu cả implement và audit. |

**Kết luận trước thiết kế**: Goal 011 được phép triển khai. Chỉ contract dữ liệu nào thực sự được đọc mới phải đạt kiểm tra tương ứng; trạng thái tổng thể của Goal 010 không chặn Goal 011.

## Cấu trúc dự án

### Tài liệu của tính năng

```text
specs/011-adaptive-work-memory/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── workspace-memory-loop.md
├── checklists/
│   └── requirements.md
├── tasks.md
└── GROK_EXECUTION_PROMPT.md
```

### Mã nguồn dự kiến

```text
src/aios_habit/
├── feature_flags.py
├── workspace_memory_models.py
├── workspace_memory_service.py
├── workspace_memory_ui.py
├── workspace_chat_ai_answer.py
├── antigravity_bridge.py
└── workspace_chat_app.py

tests/
├── fixtures/workspace_memory/
├── test_workspace_memory_recall.py
├── test_workspace_memory_commands.py
├── test_workspace_memory_corrections.py
├── test_workspace_memory_ui.py
├── test_workspace_chat_ai_answer.py
└── test_workspace_chat_ui_i18n.py

scripts/
├── benchmark_workspace_memory_recall.py
└── check_user_facing_vietnamese.py
```

**Quyết định cấu trúc**: Tách model thuần khỏi service để kiểm thử dễ, nhưng chưa tạo repository/adapter hierarchy riêng. `workspace_memory_service.py` chứa các bộ đọc nguồn nhỏ và logic xếp hạng; chỉ tách thêm khi file vượt ranh giới trách nhiệm rõ ràng. Tất cả call path tạo prompt dùng cùng hợp đồng `WorkspaceMemoryRecallResult`.

## Thiết kế theo giai đoạn

### Giai đoạn 0 — Baseline và tương thích nguồn

1. Chụp baseline prompt, focused tests và trạng thái feature flag để có rollback oracle.
2. Kiểm tra từng nguồn đọc độc lập. Nguồn Goal 010 chỉ bật khi artifact đã published, chưa revoked và đọc được provenance cần thiết.
3. Nếu Goal 010 chưa sẵn sàng, adapter trả candidate rỗng cùng reason code nội bộ; không chặn Goal 011 và không hiện lỗi kỹ thuật cho người dùng.

### Giai đoạn 1 — Gọi lại tri thức đã xác nhận

1. Giữ feature flag `adaptive_work_memory` mặc định `False` làm giá trị triển khai ban đầu; lựa chọn đơn giản trên Workspace Chat được lưu cục bộ và trở thành giá trị sử dụng thực tế sau khi người dùng bật hoặc tắt.
2. Chỉ tạo các model bất biến cần cho US1: yêu cầu gọi lại, mục gọi lại, kết quả, lý do loại và dấu vết an toàn. `MemoryDecision` chưa thuộc lát cắt này.
3. Đọc bốn nguồn theo eligibility matrix trong contract, không di chuyển dữ liệu.
4. Chuẩn hóa Unicode/case/whitespace; chấm điểm theo title, tags/keywords, phạm vi áp dụng và nội dung; sắp xếp ổn định.
5. Lọc trạng thái, riêng tư, scope, xung đột và giới hạn trước khi tạo prompt.
6. Tích hợp cả đường gọi provider trực tiếp và bridge; tập mục nhớ phải tham gia consent fingerprint như nguồn gửi đi.
7. Nếu service lỗi hoặc không có kết quả, quay về baseline prompt; không chèn block rỗng.
8. Đạt test trạng thái, prompt injection, privacy, no-match, deterministic rank và benchmark; ghi checkpoint rồi tiếp tục.

### Giai đoạn 2 — Nhớ và quên có xác nhận

1. Nhận ý định rõ ràng qua tiền tố tiếng Việt và thẻ xác nhận, không dùng model để tự đoán mọi hội thoại.
2. Hiển thị bản xem trước; factual memory thiếu source/evidence chỉ ở candidate.
3. Sau xác nhận, tạo rồi append `MemoryDecision`; idempotent theo digest ngữ nghĩa và phạm vi.
4. Mỗi lượt append phải lấy `LibraryWriterLease` hiện có trên thư mục `local_cases/workspace_memory/`; nếu đang bận thì fail-closed bằng thông báo tiếng Việt và không tạo lock abstraction mới.
5. Quên/thu hồi ghi quyết định mới, không xóa lịch sử; cache luôn kiểm tra quyết định mới nhất trước khi trả kết quả.
6. Đạt test restart, duplicate, lease contention, revoke/cache và privacy; ghi checkpoint rồi tiếp tục.

### Giai đoạn 3 — Học từ sửa sai

1. Cung cấp hành động “Sửa để AIOS học” trên câu trả lời, lấy đúng phần sửa do người dùng nhập.
2. Tạo ứng viên có statement, applies_when, does_not_apply_when và tham chiếu message/trace dạng metadata.
3. Không lưu nguyên câu trả lời sai hoặc transcript; ứng viên tồn tại trong session cho tới khi xác nhận/hủy.
4. Dò trùng/xung đột trước ghi; người dùng chọn hợp nhất, thay thế, giữ cả hai có cảnh báo hoặc hủy.
5. Đạt test candidate isolation, dedup, conflict và reuse ở phiên mới; ghi checkpoint rồi tiếp tục.

### Giai đoạn 4 — Kiểm chứng và bàn giao Codex

1. Chạy quickstart, benchmark, test riêng tư, test hồi quy và toàn bộ quality gates bằng Python 3.11.
2. Cập nhật Graphify sau thay đổi code.
3. Grok cập nhật canonical ở trạng thái `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`, ghi bằng chứng, diff và rủi ro rồi dừng.
4. Codex độc lập đọc diff, test, privacy, persistence/rollback và chạy lại mẫu quan trọng.
5. Chỉ khi Codex không còn finding mức chặn mới đổi canonical và Gate Card sang trạng thái hoàn thành.

## Rollback và quan sát

- Tắt `adaptive_work_memory` trả về baseline prompt và bỏ toàn bộ hook gọi lại.
- Người dùng có thể bật hoặc tắt ngay trên Workspace Chat; lựa chọn được lưu tại `local_cases/workspace_memory/settings.json`, không cần sửa `.env` và không tạo database mới.
- Dữ liệu mới nằm ngoài Git; rollback code không xóa lịch sử quyết định.
- Dấu vết chỉ ghi ID, loại nguồn, score, reason code, scope và digest; không ghi secret, raw transcript hoặc full memory content.
- Nếu lượt Grok bị gián đoạn, chạy lại cùng prompt và tiếp tục từ task chưa đánh dấu có evidence; không khởi động lại từ đầu.

## Kiểm tra Constitution sau thiết kế

- `PASS`: không thêm provider, model, vector database hoặc nền dịch vụ.
- `PASS`: nguồn dữ liệu giữ schema/provenance và không hợp nhất vật lý.
- `PASS_CONDITIONAL`: phải triển khai consent fingerprint và lọc `local_only` trước mọi đường cloud.
- `PASS_CONDITIONAL`: phải kiểm thử fallback cho cả direct provider và bridge.
- `PASS_CONDITIONAL`: adapter Goal 010 phải fail-closed tại chính nguồn đó, không biến tình trạng Goal 010 thành blocker toàn hệ.

## Theo dõi độ phức tạp

Không có vi phạm Constitution cần biện minh. Thiết kế cố ý hoãn bàn giao phiên, vector search, GraphRAG, WorkflowCard tự thực thi, fine-tune, đồng bộ nhiều máy và RBAC.
