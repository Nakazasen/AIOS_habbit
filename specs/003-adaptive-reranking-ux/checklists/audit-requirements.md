# Audit Requirements Checklist: Tìm kiếm thích ứng và chế độ Tìm kỹ

**Purpose**: Kiểm tra yêu cầu có đầy đủ, rõ, đo được và audit được trước khi Terra đánh giá implementation
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

**Audience**: Product owner, Gemini implementer và Terra independent auditor

**Note**: Checklist này đánh giá chất lượng của yêu cầu/tài liệu, không thay thế test hành vi code.

## Scope and authority

- [ ] CHK001 Ranh giới giữa tìm/xếp hạng bằng chứng và model sinh câu trả lời đã được tách rõ chưa? [Spec Assumptions; Plan Summary]
- [ ] CHK002 Yêu cầu có nói rõ đường Excel có cấu trúc được xét trước text routing và không bị reranker văn bản chiếm đường không? [Spec FR-008; Plan Routing Algorithm]
- [ ] CHK003 Quyền ưu tiên `structured Excel → user Deep → Auto gates` có nhất quán giữa spec, plan, data model và contract không? [Spec FR-003/FR-008; Plan §Routing Algorithm; Contract §Public adapter]
- [ ] CHK004 Phạm vi đã loại trừ ingestion/chunking, model sinh câu trả lời, UI nghỉ hưu và always-on reranker đủ rõ chưa? [Spec Assumptions]

## Auto routing completeness

- [ ] CHK005 Cổng trước truy xuất có các tín hiệu testable và cấm model sinh câu trả lời làm trọng tài duy nhất không? [Spec FR-004; Research Decision 2]
- [ ] CHK006 Cổng sau Hybrid có tiêu chí độ phủ, facet/obligation, nguồn, trùng lặp, mâu thuẫn và mức chắc chắn thứ hạng đủ cụ thể không? [Spec FR-005/FR-006; Plan §Cổng sau Hybrid]
- [ ] CHK007 Điều kiện để giữ đường fast có yêu cầu đồng thời thay vì chỉ một từ khóa/độ dài câu hỏi không? [Spec FR-007; Research Decision 2]
- [ ] CHK008 Trạng thái `uncertain` có định nghĩa và bắt buộc nâng lên Deep ở mọi artifact không? [Spec FR-006, SC-001; Data Model invariants]
- [ ] CHK009 Yêu cầu chống bias all-fast/all-deep có dataset size, nhóm ca, confusion matrix và blocking behavior không? [Spec FR-015, SC-001; Tasks T002/T013/T038]
- [ ] CHK010 [Ambiguity] Ngưỡng post-gate được yêu cầu versioned và benchmark hóa, nhưng tài liệu có tránh tạo cảm giác các giá trị chưa đo đã được phê duyệt production không? [Plan §Cổng sau Hybrid; Research §Measurements]

## User control and UX

- [ ] CHK011 Quyền `Tìm kỹ hơn` thắng Auto với cả câu dễ đã được nêu như invariant, acceptance scenario và test task chưa? [Spec US2/FR-003/SC-002; Data Model invariant 1; Tasks T025]
- [ ] CHK012 Phạm vi persistence `theo cuộc hội thoại cho tới khi người dùng đổi` có nhất quán không? [Spec US2/Assumptions; Data Model SearchPreference]
- [ ] CHK013 Nhãn UI có hướng kết quả, giải thích đổi tốc độ và tránh tên model/profile kỹ thuật không? [Spec FR-001/FR-002/FR-018; Plan §UX Decision]
- [ ] CHK014 Điều kiện được phép hiển thị `Đã tìm kỹ` có ràng buộc đúng với `reranker_applied=true` không? [Spec FR-010; Data Model invariant 4/6; Contract §User-facing status]
- [ ] CHK015 Yêu cầu accessibility/khả năng hiểu copy có tiêu chí đo được cho người dùng nontech không? [Spec SC-007; Tasks T024/T032/T048]

## Failure, degradation and resource safety

- [ ] CHK016 Các trường hợp thiếu model, checksum sai, timeout, inference error, OOM/resource pressure và circuit-open đều có expected outcome chưa? [Spec Edge Cases/FR-009/FR-013; Tasks T030-T037]
- [ ] CHK017 Hybrid fallback và full retrieval unavailable có được phân biệt rõ, bao gồm khi nào phải abstain không? [Spec FR-009/FR-011; Plan §Thực thi reranker]
- [ ] CHK018 Yêu cầu có cấm silent fallback và false assurance bằng cả telemetry lẫn UI copy không? [Spec FR-009/FR-010/SC-003]
- [ ] CHK019 Giới hạn worker, timeout, cache/warm-up, candidate window và circuit breaker có mục tiêu rõ cho máy i5/16 GB không? [Spec FR-013; Plan Technical Context; Research Decision 5]
- [ ] CHK020 Gate RAM/latency có nêu cùng máy, cùng phiên và tránh chạy benchmark song song với full tests không? [Spec SC-005; Tasks Parallel Opportunities]

## Privacy and observability

- [ ] CHK021 Local-only/no-network có áp dụng cho classifier, Hybrid, reranker và model loading không? [Spec FR-012; Constitution Check]
- [ ] CHK022 Allow-list telemetry có đủ requested/effective path, reason, timing, counts và policy version để tái hiện quyết định không? [Spec FR-014; Contract §Safe telemetry]
- [ ] CHK023 Danh sách cấm có bao gồm raw query, query-derived short hash, snippets, titles, absolute paths, secrets và exception strings không? [Data Model §RetrievalExecutionRecord; Contract §Forbidden behavior]
- [ ] CHK024 Privacy scan có tiêu chí zero finding và là activation blocker không? [Spec SC-006; Plan Validation Matrix; Tasks T033/T041]

## Quality and performance evidence

- [ ] CHK025 Baseline, dataset labels và checksum có bắt buộc khóa trước tuning không? [Plan Phase A; Tasks T001-T004]
- [ ] CHK026 Chất lượng Deep có threshold tăng tối thiểu và recall non-regression rõ ràng không? [Spec SC-004; Plan Phase E]
- [ ] CHK027 Đường fast có threshold regression so với baseline đo lại cùng phiên, không chỉ so với số lịch sử không? [Spec SC-005; Plan Validation Matrix]
- [ ] CHK028 Báo cáo benchmark có bắt buộc per-gate PASS/PARTIAL/FAIL thay vì một nhãn tổng mơ hồ không? [Tasks T003/T041; Quickstart §Frozen benchmark]
- [ ] CHK029 [Gap] Tài liệu có quy định ai duyệt label route/evidence trước khi mở mù hay cần ghi owner trong implementation evidence? [Plan Phase A; Tasks T002/T045]

## Deployment, rollback and handover

- [ ] CHK030 Manifest v2 Hybrid-only có được giữ tương thích và adaptive mặc định off không? [Research Decision 6; Data Model Migration; Tasks T005/T006]
- [ ] CHK031 Activation có bị chặn nếu thiếu quality, latency, RAM, privacy, fallback hoặc rollback evidence không? [Spec FR-016; Tasks T039/T043]
- [ ] CHK032 Rollback có thể hoàn tất bằng flag/manifest + restart, không rebuild index hoặc mất data không? [Spec FR-017/SC-008; Plan §Rollout and Rollback]
- [ ] CHK033 Trạng thái full suite, focused suite, CLI audit, import smoke và benchmark có được yêu cầu báo riêng không? [Plan Validation Matrix; Tasks T050/T051]
- [ ] CHK034 Tài liệu canonical, operator runbook, performance baseline, troubleshooting, UX/test strategy, handover và graph refresh đều có owner task không? [Plan Phase F; Tasks T046-T053]
- [ ] CHK035 Terra có đủ evidence artifact, exact commands và stop conditions để audit read-only mà không tin narrative của Gemini không? [Tasks T045/T054; TERRA_AUDIT_PROMPT.md]

## Notes

- Đánh dấu `[x]` chỉ khi requirement wording và traceability đủ; ghi finding ngay dưới item nếu chưa đạt.
- `[Gap]` và `[Ambiguity]` là điểm Terra phải xác nhận bằng artifact thực tế hoặc trả PARTIAL.
- Implementation behavior được kiểm tra bằng `audit-plan.md` và `TERRA_AUDIT_PROMPT.md`, không bằng checklist này.
