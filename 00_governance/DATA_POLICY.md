# Data Policy

Status: `ACTIVE`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before a new data class, persistent store or external recipient

## Local First

Mọi dữ liệu mặc định được lưu local. Không đồng bộ cloud hoặc gửi provider nếu
chưa có policy route và xác nhận owner phù hợp. Git repository chỉ chứa code,
schema, docs, template và fixture synthetic.

## Data Classes

| Class | Description | Default handling |
|---|---|---|
| Raw source | Chat transcript, email, log, file gốc | Không commit; chỉ local/owner-controlled |
| Workspace Chat state | Notebook, conversation, message, selected source | JSONL local dưới `local_cases/workspace_chat/`, Git ignored |
| Evidence record | Metadata/source reference/summary/hash | Có thể commit nếu không chứa nội dung nhạy cảm |
| Candidate memory | Memory chưa review | Chỉ extraction workspace/local theo policy |
| Validated memory | Memory đã review | Memory vault theo evidence/boundary |
| RAG chunk/index | Chunk/evidence metadata và SQLite index cục bộ | Local, caller-managed path; không cloud-default |
| Export pack | Profile chuyển cho AI khác | Chỉ tạo từ master profile và audit trước use |
| Secrets | Token, key, credential | Không commit/không đưa vào diagnostics hoặc docs |

## Retention and deletion reality

- Raw source chỉ giữ khi cần audit và phải nằm ngoài Git hoặc trong vùng
  local-only.
- Evidence record giữ lâu dài nếu không vi phạm privacy; deprecated memory được
  đánh dấu lý do trước khi xem xét xóa.
- Workspace Chat/runtime data và backup có retention **owner-managed**. Hiện chưa
  có automatic retention/deletion scheduler; không được claim thời hạn pháp lý.
- RAG index chỉ có thể rebuild khi source/chunk input tương ứng vẫn còn và owner
  cho phép dùng nó.

## External route boundary

`local_only` và `confidential` không được gửi provider. Các route external khác
phải dùng privacy/consent controls đã kiểm chứng; coverage hiện tại và P0 gap
được mô tả trong [Privacy Impact Assessment](../docs/security/PRIVACY_IMPACT_ASSESSMENT.md).
Không dùng router/provider như authority quyết định consent.

## Evidence without raw storage

Ưu tiên lưu hash, local reference, short summary, line reference và artifact ID.
Tránh lưu toàn văn hội thoại/email hoặc dữ liệu nhận dạng không cần thiết.

## Related controls

- [Source policy](SOURCE_POLICY.md)
- [Privacy model](../docs/PRIVACY_MODEL.md)
- [Backup and restore](../docs/operations/BACKUP_RESTORE.md)
- [Data migration compatibility](../docs/operations/DATA_MIGRATION_COMPATIBILITY.md)
