# Nghiên cứu cho vòng hồ sơ–chuyên gia–bài học

## Quyết định 1: Tách hồ sơ cục bộ khỏi thư viện chữ dùng chung

**Quyết định đề xuất**: tạo kho metadata hồ sơ cục bộ, transactional, dưới `local_cases/`; hồ sơ chỉ giữ tham chiếu evidence bất biến, digest và dữ liệu hiển thị đã scrub. Không dùng `library.sqlite` cho hồ sơ, chat history, CSV hay raw factory data.

**Bằng chứng hiện trạng**:

- `workspace_chat_app.py:1016-1021` và `:3288-3300` cho thấy “Lưu vào hồ sơ” còn là placeholder, không có persistence.
- `notebook_case_actions.py:71-159` đã biết chuyển Q&A thành `Case` và pointers evidence không chứa excerpt nguồn; đây là logic có thể tái dùng sau khi validate đầu vào.
- `case_store.py:57-87` rewrite JSONL theo read–mutate–truncate; `:27-54` nuốt lỗi đọc. Nó không đủ cho audit trail có trách nhiệm hay thao tác nguyên tử.

**Các phương án đã xét**:

1. Vá `case_store.py` JSONL bằng write-then-replace: ít thay đổi nhưng không tự nhiên cho quan hệ case/review/lesson, recovery và nhiều thao tác trạng thái.
2. Một `workspace_case_repository.py` dùng SQLite cục bộ và transaction: rõ ràng cho quan hệ, trạng thái và atomic commit; đổi lại phải có migration/test kỹ.

Chọn phương án 2, vì kho này cục bộ một máy và không phải `KnowledgeCollection` dùng chung. Không thêm NAS, sync đa máy hay một kiến trúc RAG khác.

## Quyết định 2: Chuyên gia là cổng quyền, không phải prompt

**Quyết định đề xuất**: phản hồi chuyên gia là record append-only gắn case/evidence digest. AI chỉ được tạo câu hỏi hoặc draft; chỉ reviewer có role/scope đã cấu hình mới chuyển nhận định sang `confirmed` hoặc `rejected`.

**Bằng chứng hiện trạng**:

- Không có model/UI/route dedicated cho expert Q&A, identity, scope hay transition trong Workspace Chat.
- `learning_models.py:11-96` có `SeniorLearningCard` và trạng thái `draft/reviewed/confirmed`, nhưng chỉ là JSONL detached; không có UI integration.
- `agent_learning.py:31-164` có candidate hash và promotion guard nhưng dựa vào evidence registry khác, không phải case pipeline hiện tại.

**Hệ quả**: không nối thẳng hai module learning cũ vào UI. Tạo adapter/migration rõ ràng, giữ provenance của record cũ nếu import sau này được duyệt. Không AI nào tự set `confirmed`.

## Quyết định 3: “Học hỏi” là promotion có kiểm soát, không phải tự train

**Quyết định đề xuất**: bài học chỉ được tạo sau phản hồi `confirmed`, có reviewer, lý do, case/evidence digest. Promotion không tự re-embed, không thay `library.sqlite`, không gửi cloud và không đổi mô hình.

**Bằng chứng hiện trạng**: `agent_learning.py` đã tách candidate/promotion nhưng chưa được Workspace Chat gọi; test `test_learning_memory.py` chỉ chứng minh persistence/model, không phải vòng end-to-end.

**Hệ quả**: đo “học được” bằng khả năng tra cứu provenance của bài học, không đo bằng tuyên bố tăng độ chính xác mô hình.

## Quyết định 4: Pilot line là event nghi vấn trong hồ sơ

**Quyết định đề xuất**: nhận event qua parser riêng, chụp provenance bất biến trước khi đưa vào case, giữ mọi output `suspected`; chuyên gia phải xác nhận relevance trước khi nó thành nhận định hay bài học.

**Bằng chứng hiện trạng**:

- `line_log_parser.py:22-24,196-219,259-320` tách CSV vào `line_events.sqlite`, nhận Jam/C-call/LSU camera và đặt `suspected`.
- `workspace_chat_rag_v2_adapter.py:2401-2492` gắn evidence line local-only cả khi RAG không sẵn.
- `line_log_parser.py:430-441` fallback 5 event mới nhất khi không match; nếu không có expert check, có thể đưa evidence không liên quan vào hồ sơ.
- `line_log_parser.py:237-247` chỉ có `source_name`, chưa có source digest/version/collector đầy đủ.

**Hệ quả**: cổng pilot phải thêm contract provenance và relevance review trước, không mở overlay. CSV vào parser vẫn không được đi library RAG.

## Quyết định 5: LSU prediction chỉ là readiness rồi shadow, không phải feature code đơn lẻ

**Quyết định đề xuất**: cổng LSU trước hết persist một readiness manifest có owner, nguồn lịch sử, nhãn outcome, split/replay, tiêu chí quality và shadow reviewer. Nếu thiếu một mục, trạng thái là `blocked`; không có model run, production alert hoặc control.

**Bằng chứng hiện trạng**:

- `cagent_api.py:42-96` chỉ là HTTP client tên `call_cagent_prediction`; nó không có train/evaluate, label hay shadow run.
- Parser LSU camera là dữ liệu input có thể có, không phải nhãn lỗi hay chứng minh dự đoán.

**Hệ quả**: thực hiện code readiness chỉ sau khi owner chọn schema/nguồn data. Bất kỳ model/shadow runtime nào phải là gate follow-up, được review riêng.

## Quyết định 6: Agent tự trị chỉ tự thu thập/đề xuất, không tự thực thi

**Quyết định đề xuất**: sau case→expert→lesson, agent chỉ tạo `ActionProposal` và document draft có case/evidence digest. Approval tạo output mới trong allowlisted output root; không gọi command/bridge, không write factory/source/PLC, không delete/overwrite.

**Bằng chứng hiện trạng**:

- `agent_draft_sop.py:127-328` có draft, approved và chặn write chưa approved/overwrite; UI `workspace_chat_app.py:3165-3245` chỉ download sau người duyệt nhập tên.
- `agent_draft_sop.py:141-144` vẫn nhận evidence rỗng ở API; chưa đủ để gọi là evidence-bound.
- `workspace_agent_policy.py:55-66` tin boolean `approved` từ caller; `workspace_agent_orchestrator.py:188-203` có thể chuyển command tùy ý đến bridge. Đây không thể dùng cho nghiệp vụ nhà máy.
- Agent IDE bị disable tại `workspace_chat_app.py:3315-3316`; `workspace_agent_bridge_client.py:18-72` là bridge developer/local code, không phải tooling nhà máy.

**Hệ quả**: không bật flag, không tái dùng bridge/command. Feature chỉ mở proposal/export, thêm policy binding durable và kiểm no-evidence fail-closed.

## Regression bắt buộc

- Gate B: CSV không vào `library.sqlite`.
- Gate C: Gemini Web/Nakazasen Router không nhận ảnh/bản vẽ; C-AGENT là route duy nhất được policy hiện hữu cho phép nhận chúng.
- Parser line giữ `suspected`, không chẩn đoán.
- `bge_m3_hybrid` và `activation_state` không thay đổi; không tuyên bố RAG production-qualified từ các test này.
