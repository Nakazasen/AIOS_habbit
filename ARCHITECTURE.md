# AIOS Habit Architecture

Đọc lần đầu: `AGENTS.md` (L0) rồi `CONSTITUTION.md`. File này là canonical kiến trúc. Cây thư mục `00_governance/` … `12_tools/` bên dưới là **bố cục Phase 0 (memory vault)** — không nuốt cả cây khi làm Workspace Chat / RAG v2. Runtime hiện tại: Workspace Chat + `src/aios_habit/rag_v2/`. Khung nhìn container: `docs/architecture/`.

`WORKLENS_ARCHITECTURE.md` là stub chuyển hướng về file này.

### Thư viện (collection) và sổ chat

Sổ tài liệu **không** phải file tìm kiếm. Mỗi **thư viện** có kho SQLite riêng (`library.sqlite`). Sổ chỉ trỏ `collection_id`.

Người dùng chọn **thư viện cá nhân** trên máy hoặc **thư viện dùng chung** trong một thư mục ngay trên giao diện và đổi qua lại không cần khởi động lại. Kho dùng chung nằm trong `aios_thu_vien/library.sqlite`. Đổi chỗ: snapshot SQLite (Online Backup + `PRAGMA quick_check`) rồi mới đổi `storage_root`; kho cũ giữ. Lỗi I/O không đổi pointer. `LibraryWriterLease` chỉ là khóa ghi ngắn hạn: tiến trình lấy khóa trước được ghi, tiến trình sau giữ nội dung và cho người dùng thử lại; khóa không cấp quyền và không có máy ghi cố định. Nhóm dùng chung là nhóm tin cậy, ứng dụng không cấu hình quyền Windows/NAS và không tuyên bố bảo vệ bí mật giữa các thành viên. Tên tài khoản OS chỉ điền sẵn cho lịch sử trách nhiệm, có thể sửa và không phải danh tính xác minh. Máy mới gia nhập kho có sẵn khi máy đó chưa có index. Tài liệu trong kho nhận diện theo nội dung chữ đã lấy ra, không theo mã nguồn trên từng máy và không theo tên file. Chat, audio và bản chép lời thô vẫn local — index dùng chung không mang lịch sử trò chuyện. WAL trên ổ mạng nhiều máy: fail-closed, không tuyên bố an toàn. CSV log không thuộc thư viện hỏi–đáp; parser log Jam/C-call ghi `line_events.sqlite` (sự kiện nghi ngờ), không embed. Cắt đoạn chữ có chồng lấn ~15% (chuẩn Azure/Chonkie); cửa sổ retrieval/citation rộng hơn; ingest BGE gom lô 8–16, không dùng LLM để embed. Khi hỏi điều tra, gói bằng chứng có thể kèm sự kiện `line_events.sqlite` (nghi ngờ), không nhét CSV vào RAG. Gemini Web / Nakazasen Router không được gửi file ảnh hay bản vẽ; C-AGENT thì được.

Goal 010 dùng luồng bốn chặng trên Workspace Chat: chọn thư viện, phỏng vấn, kiểm tra bản nháp, xác nhận và đưa vào thư viện. Chi tiết như mã băm, mã gói, câu hỏi nghiệm thu và trạng thái SQLite được ẩn mặc định. Quyết định lưu tên ghi nhận, máy, thời điểm, độ tự tin, căn cứ, nguồn đã kiểm tra và xác nhận trách nhiệm; không kiểm tra vai trò hoặc cấm tự duyệt trong nhóm tin cậy.

### Vòng trí nhớ công việc thích nghi (Goal 011)

Workspace Chat có lớp gọi lại read-only trước câu trả lời. Người dùng bật hoặc tắt bằng lựa chọn “Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn” trong thanh bên; lựa chọn được giữ tại `local_cases/workspace_memory/settings.json`, còn cờ `adaptive_work_memory` là giá trị triển khai ban đầu khi chưa có lựa chọn. Nguồn gồm MemoryUnit đã verified, SeniorLearningCard đã confirmed, CaseLesson đã approved và artifact Goal 010 còn published. Goal 010 chỉ là nguồn tùy chọn: thiếu artifact hợp lệ thì adapter trả rỗng, không chặn Goal 011. Trí nhớ đưa vào prompt như dữ liệu tham khảo (“Sổ việc đã xác nhận”), không phải chỉ dẫn hệ thống. Mọi bridge ra ngoài dùng lọc cloud và chặn gửi memory khi fingerprint rỗng hoặc không khớp. Từ US2, quyết định nhớ/quên/sửa sai ghi append-only JSONL dưới `local_cases/workspace_memory/` với `LibraryWriterLease` hiện có; không thêm database, vector store hay model. Rollback = tắt lựa chọn trên giao diện hoặc cờ triển khai khi chưa có lựa chọn. Trạng thái Execution: `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`.

### Hồ sơ vụ cục bộ từ Workspace Chat

Nút “Lưu vào hồ sơ” chỉ lưu thông tin mô tả cục bộ vào `local_cases/workspace_cases.sqlite`: mã cuộc trò chuyện, mã tin nhắn trả lời, mã `trace` bằng chứng và các tham chiếu nguồn/digest. Kho này tách hoàn toàn khỏi `library.sqlite` và `line_events.sqlite`, không đồng bộ nhiều máy. Schema có version, lịch sử migration, Online Backup, `quick_check` và rollback khi lỗi. Transaction SQLite ghi hồ sơ, tham chiếu, activity có chuỗi digest và đầu chuỗi đáng tin cậy cùng lúc; lỗi giữa chừng không tạo hồ sơ nửa vời.

Workspace Chat có mục “Hồ sơ vụ việc” để lọc, xem chi tiết, dòng thời gian, checklist, người phụ trách, chuyển trạng thái và gắn thêm tham chiếu bằng chứng. Actor cục bộ do ứng dụng kiểm soát; bản một người dùng dùng `local_admin` với grant điều tra/chuyên gia tường minh trong scope `general`, không coi `admin` là wildcard. Hồ sơ không sao chép câu hỏi, câu trả lời, đoạn trích, ảnh, log thô hoặc đường dẫn hệ thống; `trace` chỉ được phân giải lúc đọc và khi mất phải hiển thị là thiếu. Phần này chưa bao gồm luồng thẩm định chuyên gia, promotion bài học, pilot line, dự đoán hoặc quyền Agent thực thi.

### Lát cắt cảnh báo sớm Iris LSU — kiến trúc đã triển khai (Mốc 0–4 TECHNICAL_PASS)

Lát cắt cảnh báo sớm Iris LSU đã hoàn thành toàn bộ kiểm chứng kỹ thuật (Mốc 0 đến Mốc 4 đạt `TECHNICAL_PASS`). Kiến trúc bao gồm 4 thành phần trụ cột gắn kết chặt chẽ với Workspace Chat:

1. **Cổng kiểm tra dữ liệu LSU (Data Gate) & Kho lưu trữ chuyên dụng**:
   - Dữ liệu đầu vào gồm 3 tệp nguồn: thông số linh kiện theo lot (`ComponentLotMeasurement`), liên kết Unit-lot (`UnitLotLink`) và kết quả đo tại JIG (`JigOutcomeResult`).
   - Tự động chuẩn hóa múi giờ (`Asia/Ho_Chi_Minh`), kiểm tra tính toàn vẹn, phát hiện trùng lặp khóa chính, thiếu khóa, và rò rỉ dữ liệu tương lai.
   - Kho `local_cases/production_prediction.sqlite` hoạt động độc lập với `library.sqlite` và `workspace_cases.sqlite`, có schema versioned, kiểm tra tính toàn vẹn `quick_check`, và chốt chặn cấm ghi bền vững dữ liệu vi phạm (`BLOCKED_DATA`).

2. **Công cụ phát lại lịch sử tất định (Deterministic Replay Evaluation)**:
   - Giao thức phát lại `ReplayProtocol` đóng băng tham số và tính toán chuỗi digest SHA-256 bất biến từ snapshot/code/threshold.
   - So sánh 2 phương án nền: `no_alert` (mặc định không cảnh báo, ghi nhận toàn bộ NG là bỏ sót) và `EWMA` (ngưỡng dung sai kiểm soát cố định 3.0 độ lệch chuẩn).
   - Nhánh mô hình học máy (`evaluate_supervised_model`) được khóa an toàn ở trạng thái `not_applicable` khi chưa đủ điều kiện cỡ mẫu ($\ge 200$ Units, $\ge 30$ NG), đảm bảo không cài thêm dependency máy học không cần thiết trên CPU laptop.
   - Tự động đánh giá theo hợp đồng rubric để phân loại kết luận (`AUTO_SHADOW` hoặc `LEARNING_SHADOW`).

3. **Trình chạy bóng thủ công (Manual Shadow Runner) & Liên kết Case chống trùng**:
   - `ManualShadowRunner` xử lý file theo lô nhỏ do người dùng kích hoạt, có tiến độ thời gian thực, nút dừng an toàn, không có scheduler ngầm hay kết nối điều khiển máy PLC.
   - Khóa định danh `idempotency_key` được sinh tất định từ digest snapshot, digest protocol, mã Unit và thời điểm `as_of_time`, không phụ thuộc vào đồng hồ lúc chạy.
   - Liên kết tự động sang `workspace_cases.sqlite` qua `link_shadow_risk_to_workspace_case` với nhãn `local_only`. Cơ chế phục hồi tự động tìm case hiện có theo digest để chống trùng lặp tuyệt đối khi chạy lại.
   - Cho phép ghi nhận kết quả thực tế (`record_shadow_outcome`) cho cả Unit đã cảnh báo và Unit NG bị bỏ sót không có cảnh báo trước đó.

4. **Bản đồ mở rộng có điều kiện & Bí danh dữ liệu cục bộ**:
   - Đăng ký 2 bí danh: `KHO_LSU_CUC_BO` (dữ liệu sản xuất thật LSU tại xưởng, nhãn `local_only`) và `GOI_KYOCERA_CUC_BO` (tài liệu/log kiểm kê dòng máy Kyocera cục bộ).
   - 6 nhánh độc lập sẵn sàng kích hoạt khi dữ liệu đạt yêu cầu theo chuẩn `spec.md`: US3 (Học từ bài học đã xác nhận), US4 (Trợ lý điều tra line chủ động), US5 (Agent tạo Báo cáo & SOP có kiểm soát), US6 (Agent hỗ trợ lập trình sandbox tách biệt), US10 (Cảnh báo nguy cơ an toàn trong app), US11 (Thư viện dùng chung đa máy qua NAS/SMB). Các miền mở rộng Kyocera (Drum/DLP) và C-call/Jam được xếp thành task pack riêng sau chuỗi LSU Iris (US7–US10). Không nhánh nào tạo điểm nghẽn cho các nhánh còn lại.

### Lớp trình bày tiếng Việt duy nhất

Mọi nội dung do chương trình hiển thị hoặc xuất cho người dùng/người vận hành phải đi qua lớp trình bày tiếng Việt: giao diện, trạng thái, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo. Lỗi tiếng Anh từ thư viện, hệ điều hành hoặc dịch vụ bên ngoài không được truyền thẳng ra ngoài; phải đổi thành câu tiếng Việt nói rõ sự cố và bước xử lý. Mã kỹ thuật có thể được lưu nội bộ để tra cứu nhưng không thay thế lời giải thích.

Giao diện chỉ hỗ trợ tiếng Việt và không hiển thị bộ chọn ngôn ngữ khác. Locale giao diện được tách khỏi ngôn ngữ nguồn và locale lịch sử: khả năng đọc trace cũ cùng tài liệu đa ngôn ngữ vẫn được giữ để bảo toàn nguồn tiếng Nhật, tiếng Trung hoặc nguồn khác; nội dung nguồn được phân biệt rõ với lời điều khiển/kết luận do chương trình tạo.

## Workspace Chat: chuẩn bị nguồn tăng dần (2026-08-22)

- Mỗi nguồn mới chỉ được đưa vào hàng đợi lập chỉ mục riêng sau khi đọc file thành công;
  không đọc lại cả thư viện khi người dùng thêm một tài liệu.
- Nếu người dùng hỏi trong lúc tài liệu liên quan đang chuẩn bị, hệ thống chỉ chọn một tài
  liệu khớp nhất. Câu hỏi và lựa chọn nguồn được giữ tối đa 5 phút, có thể hủy, rồi tự tiếp
  tục đúng một lần khi chính tài liệu đó sẵn sàng.
- Độ sẵn sàng được kiểm tra và tìm kiếm bằng cùng một tập nguồn. Không được chọn lại từ toàn
  bộ thư viện sau khi báo câu hỏi đã sẵn sàng, vì điều đó tạo lỗi chờ rồi thất bại mâu thuẫn.
- Câu hỏi quá rộng không được phép kích hoạt lập chỉ mục hàng loạt. Người dùng phải nêu tên
  hệ thống/tài liệu hoặc chọn rõ nguồn, trừ khi toàn bộ nguồn đã sẵn sàng từ trước.
- Khi bộ tìm kiếm tài liệu chưa được triển khai hợp lệ, nguồn hiển thị “Bộ tìm kiếm tài liệu chưa sẵn sàng”; ứng dụng
  không tạo hàng đợi giả hoặc treo chờ vô hạn. Quy tắc fail-closed của truy xuất vẫn giữ nguyên.

## 1. Ý định kiến trúc

AIOS Habit được thiết kế như một **local-first, evidence-based, AI-independent personal memory platform**.

Mục tiêu kiến trúc:

- Không phụ thuộc vào lịch sử chat của bất kỳ AI nào.
- Không lưu raw conversation làm memory chính.
- Tách nguồn, evidence, memory, profile và export pack thành các lớp riêng.
- Có thể thay GPT bằng Gemini, Claude, Grok hoặc AI tương lai mà không mất tri thức.
- Có thể audit, rollback, handover và mở rộng trong nhiều năm.

## 2. Luồng dữ liệu cốt lõi

```text
[Source Artifacts]
        |
        v
[Source Inventory]
        |
        v
[Evidence Registry]
        |
        v
[Extraction Workspace]
        |
        v
[Candidate Memory]
        |
        v
[Validation Gate]
        |
        v
[Memory Vault]
        |
        +--> [Master Profiles]
        |
        +--> [Workflow Library]
        |
        +--> [Project Knowledge Index]
        |
        +--> [AI Export Packs]
```

## 3. Kiến trúc phân lớp

### Lớp 0: Quản trị

Chứa constitution, roadmap, phase gate, changelog, handover và policy.

Folder:

```text
00_governance/
```

Trách nhiệm:

- Giữ nguyên tắc dự án.
- Ngăn nhảy phase.
- Định nghĩa PASS/FAIL.
- Quản lý rủi ro, rollback và handover.

### Lớp 1: Nguồn

Chứa thông tin về nguồn tri thức được phép xử lý.

Folder:

```text
02_sources/
```

Nguồn có thể gồm:

- Chat transcripts.
- Markdown notes.
- Audit reports.
- Commit history.
- Roadmaps.
- Specifications.
- Project folders.
- Prompt libraries.
- User interviews.

Raw source không phải memory.

### Lớp 2: Sổ bằng chứng

Chứa evidence record đại diện cho nguồn đã được kiểm tra.

Folder:

```text
03_evidence_registry/
```

Evidence record không nên chứa toàn bộ nội dung thô. Nó chứa:

- Source type.
- Source reference.
- Hash hoặc pointer.
- Summary.
- Boundary.
- Permission/retention rule.
- Memory liên kết.

### Lớp 3: Không gian trích xuất

Nơi xử lý tạm thời để chuyển evidence thành candidate memory.

Folder:

```text
04_extraction_workspace/
```

Quy tắc:

- Candidate chưa phải sự thật.
- Candidate phải có evidence.
- Candidate phải được review trước khi vào memory vault.

### Lớp 4: Kho bộ nhớ

Kho memory đã phân loại.

Folder:

```text
05_memory_vault/
```

Phân loại chính:

- `identity/`
- `behavior/`
- `language/`
- `workflow/`
- `project_knowledge/`
- `lessons_learned/`
- `decision_patterns/`

### Lớp 5: Hồ sơ tổng thể

Các file master ở root là bản tổng hợp có thể dùng cho AI khác.

Files:

- `MASTER_IDENTITY.md`
- `MASTER_BEHAVIOR_PROFILE.md`
- `MASTER_LANGUAGE_PROFILE.md`
- `MASTER_PROJECT_INDEX.md`
- `MASTER_WORKFLOW_PROFILE.md`

### Lớp 6: Khả năng chuyển AI

Chuyển memory trung lập thành prompt/profile phù hợp từng AI.

Folder:

```text
07_ai_export_packs/
```

Adapters:

- GPT.
- Gemini.
- Claude.
- Grok.
- Future AI.

Không adapter nào được trở thành nguồn sự thật. Source of truth vẫn là memory vault và master profile.

### Lớp 7: Kiểm toán và vận hành

Folder:

```text
08_audit/
09_handover/
```

Trách nhiệm:

- Ghi issue.
- Ghi validation result.
- Ghi conflict.
- Ghi phase handover.
- Hỗ trợ rollback.

## 4. Cấu trúc kho mã

```text
AIOS_habbit/
├── README.md
├── CONSTITUTION.md
├── ROADMAP.md
├── ARCHITECTURE.md
├── PROJECT_HANDOVER.md
├── CHANGELOG.md
├── MASTER_IDENTITY.md
├── MASTER_BEHAVIOR_PROFILE.md
├── MASTER_LANGUAGE_PROFILE.md
├── MASTER_PROJECT_INDEX.md
├── MASTER_WORKFLOW_PROFILE.md
├── .gitignore
│
├── 00_governance/
│   ├── PHASE_0_EXIT_CHECKLIST.md
│   ├── PHASE_GATE_LOG.md
│   ├── DATA_POLICY.md
│   ├── SOURCE_POLICY.md
│   └── VALIDATION_RULES.md
│
├── 01_design/
│   ├── SYSTEM_CONTEXT.md
│   ├── DATA_FLOW.md
│   └── TERMINOLOGY.md
│
├── 02_sources/
│   ├── README.md
│   ├── inbox_local_only/.gitkeep
│   ├── source_inventory.md
│   └── excluded_sources.md
│
├── 03_evidence_registry/
│   ├── README.md
│   ├── evidence_index.md
│   └── records/.gitkeep
│
├── 04_extraction_workspace/
│   ├── README.md
│   ├── candidate_memory/.gitkeep
│   ├── extraction_reports/.gitkeep
│   └── conflict_log.md
│
├── 05_memory_vault/
│   ├── README.md
│   ├── identity/.gitkeep
│   ├── behavior/.gitkeep
│   ├── language/.gitkeep
│   ├── workflow/.gitkeep
│   ├── project_knowledge/.gitkeep
│   ├── lessons_learned/.gitkeep
│   └── decision_patterns/.gitkeep
│
├── 06_workflow_library/
│   ├── README.md
│   └── workflows/.gitkeep
│
├── 07_ai_export_packs/
│   ├── README.md
│   ├── gpt/.gitkeep
│   ├── gemini/.gitkeep
│   ├── claude/.gitkeep
│   ├── grok/.gitkeep
│   └── future_ai/.gitkeep
│
├── 08_audit/
│   ├── README.md
│   ├── open_issues.md
│   ├── validation_log.md
│   └── rollback_log.md
│
├── 09_handover/
│   ├── README.md
│   └── phase_0_handover.md
│
├── 10_schemas/
│   ├── memory_unit.schema.json
│   ├── evidence_record.schema.json
│   ├── project_card.schema.json
│   ├── workflow_card.schema.json
│   ├── decision_pattern.schema.json
│   └── phase_record.schema.json
│
├── 11_templates/
│   ├── memory_card.md
│   ├── evidence_record.md
│   ├── project_card.md
│   ├── workflow_card.md
│   ├── decision_record.md
│   ├── extraction_report.md
│   ├── audit_report.md
│   └── handover.md
│
├── 12_tools/
│   └── README.md
│
└── _archive/
    └── README.md
```

## 5. Mô hình đối tượng bộ nhớ

```text
Evidence Record
    -> supports one or more Candidate Memory Units
Candidate Memory Unit
    -> becomes Validated Memory after review
Validated Memory
    -> feeds Master Profiles and AI Export Packs
```

### Trường của đơn vị bộ nhớ

- `memory_id`
- `memory_type`
- `title`
- `statement`
- `evidence`
- `confidence`
- `status`
- `scope`
- `tags`
- `created_at`
- `updated_at`
- `validation`
- `rollback`

## 6. Chính sách bằng chứng

Evidence phải trả lời được:

1. Tri thức này đến từ đâu?
2. Có được phép lưu không?
3. Có phải raw conversation không?
4. Có thể kiểm tra lại không?
5. Có bị suy đoán không?
6. Nếu sai thì rollback thế nào?

## 7. Mô hình độ tin cậy

| Level | Meaning | Allowed Use |
| --- | --- | --- |
| `low` | Có dấu hiệu nhưng evidence yếu | Không dùng cho master profile |
| `medium` | Có evidence rõ nhưng ít nguồn | Dùng có chú thích |
| `high` | Có nhiều evidence hoặc xác nhận trực tiếp | Dùng trong master profile |
| `verified` | Đã được người dùng hoặc reviewer xác nhận | Dùng làm canonical memory |

## 8. Mô hình trạng thái

| Status | Meaning |
| --- | --- |
| `candidate` | Mới trích xuất, chưa validate |
| `validated` | Đã qua kiểm định |
| `deprecated` | Không còn đúng hoặc đã thay thế |
| `conflicted` | Có evidence mâu thuẫn |
| `rejected` | Bị loại, không dùng |

## 9. Chiến lược phát hiện dự án

Không giả định danh sách project hiện tại là đầy đủ.

Phase 1 phải có cơ chế discovery:

```text
Allowed root folders -> Scan project markers -> Build source inventory -> Create project cards -> Review -> Update master project index
```

Project markers gồm:

- `.git/`
- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `ARCHITECTURE.md`
- `AGENT_RULES.md`
- `pyproject.toml`
- `package.json`
- `*.sln`
- `docs/`
- `prompts/`
- `specs/`

## 10. Thiết kế khả năng chuyển AI

Master memory được viết trung lập. Export pack chỉ là bản chuyển đổi.

```text
Memory Vault -> Master Profile -> AI Adapter -> AI-Specific Prompt Pack
```

Không chỉnh sửa memory lõi để phù hợp một AI. Nếu adapter cần đặc thù, ghi rõ trong adapter.

## 11. Mặc định bảo mật và quyền riêng tư

- Không commit raw transcripts.
- Không commit token, cookie, API key.
- Không commit dữ liệu cá nhân không cần thiết.
- Không lưu thông tin nhạy cảm nếu không có yêu cầu rõ ràng.
- Local first.
- Evidence record nên dùng summary và hash thay vì full raw content.

## 12. Ranh giới triển khai ban đầu (không phải mã)

Phase 0 là design và documentation phase.

Không thực hiện:

- Parser.
- Crawler.
- Vector database.
- CLI automation.
- UI.

Chỉ tạo nền móng để Phase 1 có thể audit và triển khai an toàn.

## 13. Triển khai hiện tại và tham chiếu kiểm soát

Tài liệu này giữ vai trò kiến trúc logic/data-memory lịch sử. Runtime/container,
trust-boundary, sequence, decision và control hiện hành nằm trong:

- [Professionalization index](docs/PROFESSIONALIZATION_INDEX.md)
- [Architecture context](docs/architecture/CONTEXT.md)
- [Architecture containers](docs/architecture/CONTAINERS.md)
- [Architecture components](docs/architecture/COMPONENTS.md)
- [Deployment view](docs/architecture/DEPLOYMENT.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Threat model](docs/security/THREAT_MODEL.md)
- [Runtime interfaces](docs/contracts/RUNTIME_INTERFACES.md)

Các hồ sơ đó không thay thế nguyên tắc local-first/evidence-first ở đây; chúng
mô tả implementation boundary và operational evidence cho trạng thái hiện tại.

## 14. Ranh giới trợ lý thực thi công việc kế thừa

Feature 009 dùng Workspace Chat làm giao diện chính và OpenCode server làm runtime Agent ứng viên qua adapter mỏng; Cline chỉ là fallback nếu probe OpenCode không đạt. `antigravity_bridge.py` vẫn là tuyến nguồn AI của Workspace Chat và không bị thay; chỉ bridge NVIDIA lập trình cũ nằm trong đường chuyển đổi. AIOS sở hữu Task Pack, policy theo vùng, checkpoint, verifier, receipt và Case/Evidence; runtime sở hữu session cùng vòng model–tool.

Vòng đầu hỗ trợ ba loại việc: báo cáo lỗi có bảng/biểu đồ, rà soát thiết kế công đoạn có dẫn nguồn và sửa mã có test thật. Action hợp lệ trong task root được tự động duyệt; action ngoài vùng, secret, quyền admin, commit/push/merge/deploy và sửa tài liệu công đoạn chính thức bị chặn. Mã nguồn chạy trong Git worktree; artifact ghi vào vùng bản nháp có checkpoint. Người dùng xem kết quả tiếng Việt và hoàn tác ở cấp nhiệm vụ, không bắt buộc duyệt raw diff. Trạng thái hàng đợi dùng record hiện có, khóa một writer theo workspace; không tạo database session, extension Code-OSS hoặc scheduler đa Agent ở MVP. Quyết định đầy đủ: [ADR-0008](docs/adr/0008-inherited-agent-runtime-and-code-oss-companion.md).

## 15. Ranh giới phỏng vấn chuyên gia và xuất bản tri thức

T000–T080 là đường triển khai lịch sử của Goal 010. Thiết kế danh tính xác thực, hồ sơ chuyên gia, quyền theo phạm vi và cấm tự duyệt trong đường cũ đã được thay thế bởi [ADR-0009](docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md) bản sửa. Các lớp cũ được giữ để đọc dữ liệu lịch sử hoặc phục vụ feature khác, nhưng không còn là điều kiện thao tác của Goal 010.

Goal 010 hiện dùng mô hình cá nhân hoặc nhóm nhỏ tin cậy:

1. Người dùng chọn thư viện cá nhân hoặc thư viện dùng chung ngay trên Workspace Chat và có thể đổi mà không khởi động lại.
2. Tên tài khoản hệ điều hành chỉ là gợi ý có thể sửa để ghi nhận trách nhiệm; không phải danh tính xác minh và không cấp quyền.
3. Không có tài khoản ứng dụng, RBAC, quyền theo công đoạn, quản trị viên, cấu hình quyền NAS hoặc máy ghi cố định trong Goal 010.
4. `LibraryWriterLease` chỉ là khóa ghi ngắn hạn chống hai lượt ghi đè nhau; tiến trình không lấy được khóa phải giữ bản nháp và cho người dùng thử lại.
5. Mỗi quyết định xác nhận, từ chối, yêu cầu sửa hoặc thu hồi phải gắn đúng nội dung và phiên bản, đồng thời lưu tên ghi nhận, máy, thời điểm, mức tự tin, căn cứ, nguồn đã kiểm tra và xác nhận trách nhiệm.
6. Model AI chỉ đề xuất câu hỏi và bản nháp. Model không được tự ghi quyết định, xuất bản, thu hồi hoặc ghi SQL vào thư viện.

Ba lớp lưu trữ tiếp tục được cách ly:

- Siêu dữ liệu phiên và biên nhận đã làm sạch nằm trong `workspace_cases.sqlite`.
- Âm thanh và bản chép lời thô nằm trong vùng `local_only` ngoài Git và ngoài thư viện dùng chung.
- Chỉ tri thức đã được người dùng xác nhận mới được đưa vào `library.sqlite`; bản nháp, nội dung mâu thuẫn chưa xử lý và bản đã thu hồi không xuất hiện trong truy xuất thông thường.

```text
Chọn thư viện -> Phỏng vấn bằng chữ hoặc âm thanh cục bộ
    -> Xem và sửa bản nháp cùng nguồn
    -> Ghi quyết định có trách nhiệm
    -> Khóa ghi ngắn hạn -> Bản sao cục bộ -> Kiểm tra -> Sao lưu -> Thay snapshot
```

Nếu cần phân quyền bảo mật thật giữa các thành viên, phải mở Goal riêng với dịch vụ danh tính và kho tập trung; không mở rộng Goal 010 bằng một lớp phân quyền không tạo ranh giới bảo mật thực.
