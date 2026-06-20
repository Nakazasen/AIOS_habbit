# AIOS Habit Architecture

## 1. Architectural Intent

AIOS Habit được thiết kế như một **local-first, evidence-based, AI-independent personal memory platform**.

Mục tiêu kiến trúc:

- Không phụ thuộc vào lịch sử chat của bất kỳ AI nào.
- Không lưu raw conversation làm memory chính.
- Tách nguồn, evidence, memory, profile và export pack thành các lớp riêng.
- Có thể thay GPT bằng Gemini, Claude, Grok hoặc AI tương lai mà không mất tri thức.
- Có thể audit, rollback, handover và mở rộng trong nhiều năm.

## 2. Core Data Flow

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

## 3. Layered Architecture

### Layer 0: Governance Layer

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

### Layer 1: Source Layer

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

### Layer 2: Evidence Registry Layer

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

### Layer 3: Extraction Workspace

Nơi xử lý tạm thời để chuyển evidence thành candidate memory.

Folder:

```text
04_extraction_workspace/
```

Quy tắc:

- Candidate chưa phải sự thật.
- Candidate phải có evidence.
- Candidate phải được review trước khi vào memory vault.

### Layer 4: Memory Vault

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

### Layer 5: Master Profile Layer

Các file master ở root là bản tổng hợp có thể dùng cho AI khác.

Files:

- `MASTER_IDENTITY.md`
- `MASTER_BEHAVIOR_PROFILE.md`
- `MASTER_LANGUAGE_PROFILE.md`
- `MASTER_PROJECT_INDEX.md`
- `MASTER_WORKFLOW_PROFILE.md`

### Layer 6: AI Portability Layer

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

### Layer 7: Audit & Operations Layer

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

## 4. Repository Structure

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

## 5. Memory Object Model

```text
Evidence Record
    -> supports one or more Candidate Memory Units
Candidate Memory Unit
    -> becomes Validated Memory after review
Validated Memory
    -> feeds Master Profiles and AI Export Packs
```

### Memory Unit fields

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

## 6. Evidence Policy

Evidence phải trả lời được:

1. Tri thức này đến từ đâu?
2. Có được phép lưu không?
3. Có phải raw conversation không?
4. Có thể kiểm tra lại không?
5. Có bị suy đoán không?
6. Nếu sai thì rollback thế nào?

## 7. Confidence Model

| Level | Meaning | Allowed Use |
|---|---|---|
| `low` | Có dấu hiệu nhưng evidence yếu | Không dùng cho master profile |
| `medium` | Có evidence rõ nhưng ít nguồn | Dùng có chú thích |
| `high` | Có nhiều evidence hoặc xác nhận trực tiếp | Dùng trong master profile |
| `verified` | Đã được người dùng hoặc reviewer xác nhận | Dùng làm canonical memory |

## 8. Status Model

| Status | Meaning |
|---|---|
| `candidate` | Mới trích xuất, chưa validate |
| `validated` | Đã qua kiểm định |
| `deprecated` | Không còn đúng hoặc đã thay thế |
| `conflicted` | Có evidence mâu thuẫn |
| `rejected` | Bị loại, không dùng |

## 9. Project Discovery Strategy

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

## 10. AI Portability Design

Master memory được viết trung lập. Export pack chỉ là bản chuyển đổi.

```text
Memory Vault -> Master Profile -> AI Adapter -> AI-Specific Prompt Pack
```

Không chỉnh sửa memory lõi để phù hợp một AI. Nếu adapter cần đặc thù, ghi rõ trong adapter.

## 11. Security and Privacy Defaults

- Không commit raw transcripts.
- Không commit token, cookie, API key.
- Không commit dữ liệu cá nhân không cần thiết.
- Không lưu thông tin nhạy cảm nếu không có yêu cầu rõ ràng.
- Local first.
- Evidence record nên dùng summary và hash thay vì full raw content.

## 12. Initial Non-Code Implementation Boundary

Phase 0 là design và documentation phase.

Không thực hiện:

- Parser.
- Crawler.
- Vector database.
- CLI automation.
- UI.

Chỉ tạo nền móng để Phase 1 có thể audit và triển khai an toàn.
