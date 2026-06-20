# Source Policy

## Purpose

Quy định nguồn nào được dùng để trích xuất memory và cách xử lý.

## Allowed Source Types

- Markdown notes.
- Roadmaps.
- Architecture docs.
- Audit reports.
- Commit history.
- Project specifications.
- Prompt libraries.
- User-approved chat transcript.
- User interviews.

## Source Processing Rule

```text
Source -> Source Inventory -> Evidence Record -> Candidate Memory -> Validation -> Memory Vault
```

Không được đi thẳng:

```text
Source -> Memory Vault
```

## Raw Chat Rule

Chat transcript không được lưu như memory. Chỉ được dùng để trích xuất:

- Behavior pattern.
- Workflow pattern.
- Decision pattern.
- Project knowledge.
- Lessons learned.

## Exclusion Criteria

Loại trừ hoặc local-only nếu source chứa:

- Secrets.
- Credential.
- Private personal data không liên quan.
- Nội dung không được phép xử lý.
- Raw data quá dài chưa phân loại.

## Evidence Requirements

Mỗi evidence record cần:

- Source type.
- Source location hoặc reference.
- Hash nếu có thể.
- Summary.
- Boundary.
- Permission status.
- Retention status.

## Discovery Rule

Không giả định danh sách project/source là đầy đủ. Phase 1 phải có inventory và exclusion report.
