# AIOS Habit Architecture

Đọc lần đầu: `AGENTS.md` (L0) rồi `CONSTITUTION.md`. File này là canonical kiến trúc. Cây thư mục `00_governance/` … `12_tools/` bên dưới là **bố cục Phase 0 (memory vault)** — không nuốt cả cây khi làm Workspace Chat / RAG v2. Runtime hiện tại: Workspace Chat + `src/aios_habit/rag_v2/`. Khung nhìn container: `docs/architecture/`.

`WORKLENS_ARCHITECTURE.md` là stub chuyển hướng về file này.

### Thư viện (collection) và sổ chat

Sổ tài liệu **không** phải file tìm kiếm. Mỗi **thư viện** có kho SQLite riêng (`library.sqlite`). Sổ chỉ trỏ `collection_id`.

Chủ sở hữu chọn **thư mục dùng chung**. Kho nằm trong `aios_thu_vien/library.sqlite`. Đổi chỗ: snapshot SQLite (Online Backup + `PRAGMA quick_check`) rồi mới đổi `storage_root`; kho cũ giữ. Lỗi I/O không đổi pointer. Một writer (file lease); writer thứ hai fail-closed. Máy mới gia nhập kho có sẵn khi máy đó chưa có index. Tài liệu trong kho nhận diện theo nội dung chữ đã lấy ra, không theo mã nguồn trên từng máy và không theo tên file. Chat/JSONL vẫn local — index dùng chung không mang lịch sử trò chuyện. WAL trên ổ mạng nhiều máy: fail-closed, không tuyên bố an toàn. CSV log không thuộc thư viện hỏi–đáp; parser log Jam/C-call ghi `line_events.sqlite` (sự kiện nghi ngờ), không embed. Gemini Web / Nakazasen Router không được gửi file ảnh hay bản vẽ; C-AGENT thì được.

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
- Khi BGE-M3 chưa được triển khai hợp lệ, nguồn hiển thị `BGE-M3 chưa sẵn sàng`; ứng dụng
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
|---|---|---|
| `low` | Có dấu hiệu nhưng evidence yếu | Không dùng cho master profile |
| `medium` | Có evidence rõ nhưng ít nguồn | Dùng có chú thích |
| `high` | Có nhiều evidence hoặc xác nhận trực tiếp | Dùng trong master profile |
| `verified` | Đã được người dùng hoặc reviewer xác nhận | Dùng làm canonical memory |

## 8. Mô hình trạng thái

| Status | Meaning |
|---|---|
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
