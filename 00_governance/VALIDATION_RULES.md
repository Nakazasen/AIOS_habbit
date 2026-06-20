# Validation Rules

## Status Values

- `PASS`: đạt đầy đủ tiêu chí, có evidence.
- `FAIL`: không đạt tiêu chí.
- `PARTIAL`: đạt một phần, cần bổ sung.
- `BLOCKED`: không thể hoàn thành do thiếu input/quyền/evidence.
- `NOT_APPLICABLE`: không áp dụng, cần ghi lý do.

## Memory Validation

Memory đạt PASS khi:

1. Có `memory_id` duy nhất.
2. Có `memory_type` hợp lệ.
3. Có statement ngắn gọn, không phải raw quote dài.
4. Có ít nhất một evidence record.
5. Có confidence.
6. Có boundary/scope.
7. Không chứa suy đoán chưa gắn nhãn.
8. Có rollback/deprecation path.

## Project Validation

Project card đạt PASS khi:

1. Path tồn tại hoặc có lý do chưa xác minh.
2. Có purpose.
3. Có status.
4. Có memory relevance.
5. Có evidence hoặc status candidate.

## Workflow Validation

Workflow đạt PASS khi có:

- Trigger.
- Inputs.
- Steps.
- Outputs.
- Validation.
- PASS/FAIL criteria.
- Rollback.
- Handover.
- Evidence.

## Phase Validation

Phase đạt PASS khi:

- Deliverables tồn tại.
- Scope không bị vượt.
- Risk được ghi.
- Validation chạy xong.
- Handover cập nhật.
- Rollback rõ ràng.
- Changelog cập nhật.
