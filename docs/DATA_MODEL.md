# Mô Hình Dữ Liệu (Data Model)

## Bản Ghi Bằng Chứng (EvidenceRecord)
Các trường: `evidence_id`, `title`, `source_type`, `source_path`, `source_pointer`, `captured_at`, `classification`, `summary`, `hash`, `risk_level`, `allowed_for_export`, `notes`.

## Đơn Vị Bộ Nhớ (MemoryUnit)
Các trường: `memory_id`, `category`, `title`, `statement`, `evidence_ids`, `confidence`, `status`, `created_at`, `updated_at`, `tags`, `export_allowed`, `review_notes`.

Bộ nhớ đã xác thực (Verified memory) bắt buộc phải có ít nhất một ID bằng chứng. Bộ nhớ cho phép xuất (Export-allowed memory) bắt buộc phải ở trạng thái đã xác thực.

## Thẻ Dự Án (ProjectCard)
Các trường: `project_id`, `name`, `path`, `status`, `description`, `detected_signals`, `evidence_ids`, `risks`, `last_seen_at`, `tags`.

## Thẻ Quy Trình (WorkflowCard)
Các trường: `workflow_id`, `title`, `trigger`, `context`, `steps`, `output`, `failure_modes`, `evidence_ids`, `status`, `tags`.

## Mẫu Quyết Định (DecisionPattern)
Các trường: `decision_id`, `title`, `context`, `criteria`, `tradeoffs`, `preferred_action`, `anti_patterns`, `evidence_ids`, `status`, `tags`.

