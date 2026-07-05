# AIOS Existing AI Inventory

## Phạm vi và nguyên tắc A15

Tài liệu này kiểm kê các đường đi liên quan AI tại baseline `89c017d08437ee66c4791c78ebc080de8ecd4441`. A15 chỉ audit và thiết kế; không xóa, đổi tên, hoặc sửa runtime cũ. Workspace Chat là UI chính. `studio.py` và `case_cockpit.py` chỉ là nguồn tham chiếu/debug legacy.

Quy ước quyết định:

- `KEEP`: giữ nguyên trách nhiệm, có thể được Brain Gateway gọi lại.
- `MIGRATE_TO_BRAIN_GATEWAY`: giữ code trong A15, nhưng chuyển dần quyền điều phối về gateway ở gate sau.
- `DEPRECATE`: không dùng cho luồng mới; vẫn giữ để tương thích và rollback.
- `DELETE_LATER`: chỉ là ứng viên xóa tại gate riêng sau khi có test bảo vệ, telemetry migration và owner phê duyệt.

Không xóa gì trong A15.

## Bảng inventory

| Thành phần | File/module chính | Hiện dùng ở đâu | Có gọi cloud? | Privacy gate hiện có? | Test hiện có? | Rủi ro chính | Quyết định |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Workspace Chat AI answer | `workspace_chat_app.py`, `workspace_chat_ai_answer.py`, `llm_client.py` | UI chính: retrieval cục bộ, đóng gói snippet, gọi endpoint OpenAI-compatible từ biến môi trường | Có, nếu `AIOS_LLM_PROVIDER` và endpoint cloud được cấu hình | Có nhưng cục bộ trong module; block nhãn không cho gửi, kiểm source fingerprint; `machine_only` lại được coi là gửi được | Có: `test_workspace_chat_ai_answer.py`, owner-flow, UI-copy, architecture-boundary | UI tự đặt `cloud_consent_confirmed=True`; không có gateway/audit log chung; locality trong `LLMConfig` không được enforcement tại call site; lỗi có thể chứa body provider | `MIGRATE_TO_BRAIN_GATEWAY` |
| Workspace Chat local retrieval/evidence | `workspace_chat_retrieval.py`, `rag_search.py`, `rag_ingest.py` | UI chính; SQLite in-memory FTS/LIKE, chọn tối đa 5 snippet | Không | Retrieval là local; blank/unknown fail về `local_only`, nhưng `machine_only` bị map thành `cloud_safe` | Có: `test_workspace_chat_retrieval.py`, RAG tests | Privacy vocabulary không thống nhất; snippet được chuyển thẳng sang prompt ở đường cloud | `KEEP`, gateway nhận output qua contract |
| Workspace source privacy UX/model | `workspace_chat_ui.py`, `workspace_chat_models.py`, `workspace_chat_store.py` | UI chính; owner chọn “Có thể gửi AI” hoặc “Chỉ dùng trên máy” | Không tự gọi | Có; mặc định model là `machine_only`, nhưng UI ánh xạ “Có thể gửi AI” thành `machine_only` | Có: source/privacy/owner-flow tests | Tên `machine_only` trái nghĩa với hành vi “sendable”; dễ leak khi tái sử dụng ngoài UI | `MIGRATE_TO_BRAIN_GATEWAY`; giữ storage compatibility |
| Direct LLM client | `llm_client.py` | Workspace Chat và `notebook_qa.py` | Có | Chỉ dựa vào caller; trường `locality` không tự chặn endpoint cloud | Có: `test_llm_client.py` | Điểm gọi mạng cấp thấp có thể bị gọi bỏ qua policy; body lỗi thô; không route log chung | `DEPRECATE` cho call site mới; gateway adapter bọc lại |
| AIOS in-repo router | `ai_router.py`, `provider_catalog.py`, `provider_health.py`, `route_log_ui.py` | Chủ yếu Case Cockpit legacy và test | Có | Safety mode chặn Auto/company khỏi cloud; normal docs được phép | Có: router/catalog/health/route-log tests | Trùng trách nhiệm với Nakazasen Router; nhận `source_context` thô; policy dùng vocabulary cũ | `MIGRATE_TO_BRAIN_GATEWAY`, sau đó `DEPRECATE` phần provider routing trùng lặp |
| Local/provider bridge | `ai_provider_bridge.py`, `provider_safety.py` | Case Cockpit/RAG strong answer; local OpenAI-compatible và một số cloud config | Có | Chặn `local_only` khi provider không local; kiểm local/private endpoint khi khai báo local | Có: `test_ai_provider_bridge.py`, `test_provider_safety.py` | Caller tự gán locality; prompt chứa raw source context; nhiều policy path khác nhau | `MIGRATE_TO_BRAIN_GATEWAY` |
| Prompt Pack cho Case/Notebook | `case_prompt.py` | Case Cockpit legacy; Gemini/GPT/Copilot/local AI/NotebookLM-safe | Không tự gọi | Có lọc `local_only`; policy learning card dựa case privacy và confirmation | Có: hardening, quick-intake, learning-memory tests | `include_local_only=True` là cờ mạnh; target string tự do; không có manifest/hash/consent thống nhất | `KEEP` formatter, `MIGRATE_TO_BRAIN_GATEWAY` policy/export decision |
| RAG evidence pack và answer composers | `rag_evidence.py`, `rag_answer_composer.py`, `final_answer_composer.py`, `citation_answer.py` | Local RAG, benchmark, strong answer UI | Không tự gọi hoặc deterministic local | Có strictest `local_only`; có `allowed_external` và citation IDs | Có nhiều test RAG/final-answer/citation | Privacy chỉ có tập nhãn nhỏ; “allowed_external” có thể bị caller tin quá mức | `KEEP`; gateway là owner cuối của route decision |
| IDE prompt pack/paste-back | `ide_bridge.py` | RAG strong-model manual bridge | Không | Block `local_only`, config cho `cloud_safe`/redacted | Có: `test_ide_bridge.py`, phase owner pilot | Chỉ xử lý answer, chưa phải task executor; `external_ai_used` suy ra từ pack thay vì bằng chứng execution | `MIGRATE_TO_BRAIN_GATEWAY`; giữ schema tương thích |
| Full IDE handoff bundle/import | `ide_handoff_bridge.py` | Case Cockpit legacy; outbox/inbox thủ công | Không tự launch agent | Có warning/ack cho `local_only`, allow-list evidence ID, full-bundle checksum | Có: handoff, pending, markdown import, UI-flow tests | Bundle có thể chứa raw `local_only`; task pack chưa giới hạn file/command; import chưa audit git/tests/scope/fake PASS | `MIGRATE_TO_BRAIN_GATEWAY`; mở rộng qua A17, không thay runtime A15 |
| NotebookLM prompt/manual bridge | `notebook_bridge.py` | Legacy Notebook/Case Cockpit; owner copy/paste | Không tự gọi | Prompt không chứa raw source trong hàm này; phụ thuộc owner đã upload nguồn đúng | Có: `test_notebook_bridge.py` | Không tự chứng minh nguồn đã cloud-safe; lời dẫn giả định toàn bộ nguồn đã upload | `KEEP` cho manual workflow; gateway quản lý export permission |
| NotebookLM-safe prompt/export | `case_prompt.py`, `visual_map_export.py`, `notebook_qa.py` | Legacy Case/Notebook/visual map | Có thể đi đến `complete_chat` trong notebook Q&A; export bản thân không gọi | Có redaction/removal `local_only` | Có hardening, visual-map-export, notebook-QA tests | Nhiều implementation “safe” khác nhau, dễ lệch quy tắc strictest-wins | `MIGRATE_TO_BRAIN_GATEWAY` |
| NotebookLM comparison | `notebooklm_compare.py`, CLI `notebooklm-compare`, docs/runbook | Benchmark local; có capability discovery và manual fallback | Có khả năng gọi CLI ngoài nếu owner chạy flow tương ứng; A15 không chạy | Config mặc định `local_only`; output ở `local_runs`; claim policy rõ | Có: `test_notebooklm_compare.py` | Có `subprocess`; arena hiện thiên benchmark kỹ thuật, chưa có owner-supplied comparison contract A18 | `KEEP` evaluator concepts; `MIGRATE_TO_BRAIN_GATEWAY` route/privacy |
| Senior Learning Memory | `learning_models.py`, `memory.py`, `case_prompt.py`, `case_handover.py` | Case Cockpit legacy, prompt/handover, JSONL local | Không tự gọi | Learning card chỉ đưa cloud khi case không local-only và card confirmed; audit memory kiểm evidence | Có: `test_learning_memory.py`, core audit tests | Hai memory model (`SeniorLearningCard` và `MemoryUnit`) tồn tại song song; tạo card từ agent result có thể biến claim chưa kiểm chứng thành memory | `KEEP`; gateway/import chỉ tạo draft/review-required |
| Handover/export | `case_handover.py`, `handover.py`, `export_pack.py`, CLI export | Legacy Case và CLI | Không | Có local/redacted/cloud-safe modes; CLI chỉ export verified+allowed records, redacts secret patterns | Có case-handover, learning-memory và core tests | Policy phân tán; `cloud_safe` vẫn phụ thuộc dữ liệu upstream gán đúng; audit pattern không phải DLP đầy đủ | `KEEP` formatters; `MIGRATE_TO_BRAIN_GATEWAY` approval/audit |
| Audit CLI | `audit.py`, `cli.py` | `python -m aios_habit.cli audit` | Không | Scan secret/raw markers, verified-memory evidence links | Có: `test_aios_habit.py`, phase-gate tests | Không audit mọi privacy route, task report hay git scope; command ghi `08_audit/final_audit_report.md` | `KEEP`, mở rộng ở gate riêng sau A15 |
| Legacy Studio | `studio.py` | Reference/debug | Không phải UI chính | Có metadata/local-only controls cơ bản | Có core/studio-related coverage gián tiếp | UX và model cũ, không nên nhận tính năng gateway mới | `DEPRECATE`; không xóa |
| Legacy Case Cockpit | `case_cockpit.py` | Reference/debug; chứa nhiều integration AI cũ | Có | Có nhiều guard theo từng feature | Có suite Case Cockpit lớn | Monolith, nhiều đường AI song song, có nguy cơ trở thành “gateway ngầm” | `DEPRECATE` cho tính năng mới; giữ làm reference/debug |

## Khả năng cloud hiện tại

AIOS hiện có khả năng gọi cloud thật, không chỉ mock:

1. Workspace Chat gọi `llm_client.complete_chat()` tới `AIOS_LLM_BASE_URL`.
2. `ai_provider_bridge.py` gọi endpoint OpenAI-compatible.
3. `ai_router.py` chọn nhiều provider từ biến môi trường và có fallback/key health.
4. `notebook_qa.py` có thể gọi `complete_chat()`.

Những đường này không đi qua một policy owner duy nhất. Nakazasen Router chưa được tích hợp vào AIOS.

## Vì sao AI hiện tại chưa đủ

- Không có một entry point duy nhất quyết định Local Brain, Router Brain hay IDE Agent Brain.
- Privacy labels và ý nghĩa không đồng nhất: `local_only`, `cloud_allowed`, `cloud_safe`, `redacted`, `machine_only`, safety-mode labels.
- Workspace Chat coi `machine_only` là gửi được; thiết kế A15 yêu cầu mặc định deny cloud và cần consent rõ.
- Nhiều module tự dựng prompt, tự gọi provider và tự ghi route summary.
- Router nội bộ AIOS trùng vai trò provider routing với repo Nakazasen, trong khi business/privacy policy phải thuộc AIOS.
- IDE bridge hiện là answer handoff, chưa phải task pack executor boundary và chưa kiểm chứng PASS bằng git/test evidence.
- Audit CLI chưa nối route decision, sanitization receipt, agent-result validation và case history.

## Ma trận giữ/chuyển/deprecate/xóa sau

| Nhóm | KEEP | MIGRATE_TO_BRAIN_GATEWAY | DEPRECATE | DELETE_LATER |
| --- | --- | --- | --- | --- |
| Retrieval/evidence | Local retrieval, RAG evidence/citations | Quyết định external route | Không | Không |
| Provider/network | Provider adapters làm implementation detail | Mọi call site và policy | Direct `llm_client` cho code mới; in-repo router sau migration | Chỉ đề xuất phần router trùng lặp sau A16+ và test parity |
| Prompt/export | Formatters và safe placeholders | Privacy resolution, consent, audit receipt | Target-string tự do cho flow mới | Không |
| IDE | Bundle/checksum/evidence allow-list | Task pack + result import | Answer-only schema làm mặc định cho coding task | Schema/adapter cũ chỉ sau migration đầy đủ |
| UI legacy | Reference/debug | Không mở feature mới | Studio/Case Cockpit | Chỉ ở gate retirement riêng |

## Giảm rủi ro “bãi rác AI”

1. Chỉ Brain Gateway được phép chọn brain và cho phép external transmission.
2. Mỗi module cũ được bọc bằng adapter; không copy logic sang gateway.
3. Thêm dependency rule: UI/domain không import network client trực tiếp.
4. Chuẩn hóa privacy ở boundary, nhưng giữ raw legacy label trong metadata để migration có thể truy vết.
5. Mọi cloud request có sanitized payload hash, consent receipt và audit event; không log raw prompt/evidence.
6. Mỗi migration giữ test characterization cho hành vi cũ và test denial cho hành vi mới.
7. `DEPRECATE` không đồng nghĩa xóa. `DELETE_LATER` cần gate riêng, usage proof, rollback và owner approval.

## Ghi chú roadmap

`WORKLENS_MASTER_ROADMAP.md` đã có commit sync `e6abb87`, nhưng nội dung tại baseline vẫn ghi “Current local/remote HEAD: `8adab34`” và Gate 1C “IN PROGRESS”, trong khi baseline là `89c017d` và Gate 1C đã hoàn thành. A15 không sửa roadmap vì phạm vi ghi chỉ là `docs/design/*.md`; đây là documentation drift cần gate/commit riêng.
