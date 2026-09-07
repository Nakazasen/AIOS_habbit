# Hợp đồng an toàn cho vòng vụ việc, Agent và dự đoán

> **Ranh giới áp dụng**: Đây là hợp đồng đích của toàn bộ đặc tả. Trong mỗi đợt chỉ các mục được kích hoạt trong `plan.md` và `tasks.md` mới là hợp đồng thực thi. Không tạo API, bảng hay dependency tương lai chỉ để đáp ứng phần chưa đủ điều kiện.

## 1. Bất biến toàn hệ thống

1. Thiếu evidence, role, scope, digest, migration hoặc owner decision thì fail-closed.
2. `local_only` không đi Gemini Web/Nakazasen Router; C-AGENT chỉ theo policy và consent hiện có.
3. Không có API nào trong phạm vi này được điều khiển PLC, dừng line, chặn/xuất hàng, xóa hoặc ghi đè nguồn nhà máy.
4. AI output không tự trở thành `confirmed`, outcome label, bài học hoặc PASS.
5. Workspace Chat không import `studio` hoặc `case_cockpit`.
6. Mọi câu chữ người dùng hoặc người vận hành thấy chỉ dùng tiếng Việt dễ hiểu, gồm giao diện, tiến độ, cảnh báo, lỗi, nhật ký vận hành và báo cáo; không có câu tiếng Anh dự phòng.
7. Lỗi từ thư viện, hệ điều hành hoặc dịch vụ bên ngoài phải được chặn và đổi thành lời giải thích cùng bước xử lý bằng tiếng Việt; không hiện traceback, secret hoặc đường dẫn hệ thống.
8. Tác tử phát triển dùng model cloud không được đọc file `local_only` hoặc dữ liệu nhà máy thật. Phát triển chỉ dùng fixture giả hoàn toàn hoặc manifest tên cột/quy tắc đã được chủ sở hữu làm sạch.

## 2. Hợp đồng migration

```text
migrate_store(database_path, target_version) -> MigrationResult
```

### Điều kiện trước

- Path nằm trong local runtime root được phép.
- Migration chain liên tục, checksum đúng, không có version lạ.
- Online backup thành công và `quick_check` của bản nguồn đạt.

### Kết quả

- Tất cả migration hoặc không migration nào được commit.
- `schema_migrations` và `PRAGMA user_version` khớp.
- `quick_check` sau migration đạt; nếu lỗi, restore snapshot và trả error code an toàn.

## 3. Hợp đồng tạo và đọc case

```text
create_case_from_trace_id(trace_id, expected_conversation_id) -> CaseRecord
list_cases(filter, actor) -> CaseSummary[]
get_case_detail(case_id, actor) -> CaseDetail
transition_case(case_id, expected_version, transition, actor, rationale) -> CaseRecord
attach_evidence_reference(case_id, expected_version, source_store, source_id, source_version, locator, content_digest, provenance_status, actor) -> EvidenceReference
```

### Chốt chặn

- Tạo từ trace cần citation/source locator/digest/`local_only`; không copy raw Q&A/excerpt.
- `list_cases` chỉ trả metadata đã scrub và case actor được phép xem.
- `get_case_detail` phân giải trace gốc ở read time; trace mất trả `missing`, không tái sinh nội dung.
- Transition kiểm state machine, role/scope, optimistic version và ghi `CaseActivity` cùng transaction.
- Gắn thêm evidence chỉ nhận locator đã làm sạch, digest và provenance từ kho nguồn được phép; không nhận raw bytes/raw excerpt và phải ghi activity cùng transaction.
- Actor được lấy từ local actor context đáng tin cậy do ứng dụng cấu hình, không nhận ID tự khai từ form UI. Case luôn có scope để đối chiếu grant; thiếu actor/grant/scope thì fail-closed.
- Mỗi activity có `event_digest`; case giữ `activity_head_digest` và service phải kiểm toàn chuỗi trước thao tác ghi.

## 4. Hợp đồng chuyên gia

```text
request_expert_review(case_id, claim_digest, question, assignee, scope, actor) -> ExpertRequest
record_expert_review(request_id, decision, rationale, confidence, actor) -> ExpertReview
resolve_review_conflict(case_id, review_ids, decision, rationale, actor) -> ExpertReview
```

### Chốt chặn

- Assignee/actor phải có `RoleGrant` còn hiệu lực và scope khớp.
- `confirmed`/`rejected` cần rationale không rỗng và evidence digest vẫn khớp case.
- Review append-only; sửa tạo record mới với `supersedes_review_id`.
- Hai review trái chiều chuyển case sang trạng thái xung đột; AI không chọn bên thắng.

## 5. Hợp đồng bài học

```text
create_learning_candidate(review_id, learning_text, actor) -> LearningRecord
promote_learning(learning_id, actor, rationale) -> LearningRecord
withdraw_learning(learning_id, actor, rationale) -> LearningRecord
search_promoted_learning(query, case_scope, actor) -> LearningHit[]
```

### Chốt chặn

- Candidate chỉ từ review `confirmed` có provenance đầy đủ.
- Promotion cần role `quality_manager`, digest không đổi và rationale.
- Search chỉ trả `promoted`, luôn kèm case/review/evidence refs và nhãn “Bài học đã xác nhận”.
- Không ghi `library.sqlite`, không train/re-embed tự động vào RAG library.

## 6. Hợp đồng điều tra line

```text
attach_line_events(case_id, event_ids, actor) -> EvidenceReference[]
build_investigation_timeline(case_id, actor) -> Timeline
propose_missing_evidence(case_id, actor) -> CaseChecklistItem[]
review_event_relevance(case_id, evidence_ref_id, decision, actor) -> EvidenceReference
```

### Chốt chặn

- Event phải tồn tại trong `line_events.sqlite`, có source digest/version và trạng thái `suspected`.
- Không match thì trả rỗng; cấm fallback năm event gần nhất.
- Timeline phân biệt fact, hypothesis và missing data.
- Mapping overlay chỉ dùng manifest có version/approver/scope khớp.
- CSV thô không đi `library.sqlite` hoặc external route.

## 7. Hợp đồng Agent artifact

```text
create_artifact_proposal(case_id, capability_id, instruction, actor) -> ArtifactProposal
generate_artifact_version(proposal_id, actor) -> ArtifactVersion
verify_artifact(artifact_version_id, verifier_id) -> VerificationResult
review_artifact(artifact_version_id, decision, actor, rationale) -> ApprovalRecord
export_approved_artifact(artifact_version_id, output_root, actor) -> ExportResult
```

### Chốt chặn

- Capability phải enabled, risk tier/inputs/outputs/template/verifier/approver đầy đủ.
- Case/evidence digest rỗng hoặc review chưa đạt theo capability thì từ chối.
- Mọi output là path tương đối nằm trong allowlisted root; file tồn tại thì tạo version/path mới.
- Chỉnh artifact sau approval làm approval cũ không còn hiệu lực.
- `process_design` không đồng nghĩa cho phép sửa file CAD/PLC gốc; adapter cụ thể phải có contract riêng.

## 8. Hợp đồng Agent lập trình

```text
create_code_task_case(task_pack, workspace, actor) -> CaseRecord
propose_code_change(case_id, proposal, actor) -> ArtifactVersion
approve_code_change(case_id, proposal_digest, actor) -> ApprovalRecord
run_approved_command(case_id, command_digest, actor) -> AgentExecutionRecord
record_observed_tests(case_id, evidence, auditor) -> AgentExecutionRecord
```

### Chốt chặn

- Workspace code đã xác nhận, nằm ngoài factory/local runtime data roots.
- Task pack xác định allowed/forbidden files, commands, tests, branch/head.
- `local_cases`, `.env`, factory source và system paths bị deny mặc định.
- Patch/command proposal bất biến; approval gắn đúng digest/version.
- Báo cáo PASS cần observed evidence do runner/auditor thu, không tin self-report.
- Không tự merge/push/commit nếu capability và approval riêng chưa được cấp.

## 9. Hợp đồng Data Gate Iris LSU

```text
validate_lsu_snapshot(files, data_dictionary, target_config, actor) -> ReadinessResult
register_lsu_snapshot(readiness_id, actor) -> DatasetVersion
trace_lsu_unit(dataset_id, unit_serial, actor) -> LsuUnitTrace
```

### Điều kiện đăng ký snapshot

1. Khóa nối `component_lot_id → unit_serial → jig_id/run_id` và data dictionary đạt rubric T011.
2. Thông số lot và phép đo JIG có đơn vị, thời điểm sự kiện, thời điểm nhận dữ liệu và nguồn/digest.
3. Outcome OK/NG đến từ trường kết quả cuối cùng có khóa/digest hợp lệ hoặc bản sửa append-only của người dùng; số lượng dương/âm được báo theo protocol.
4. Data owner và quality owner được chỉ định.

Rubric tại `lsu-acceptance-rubric.md` tự trả `PASS`, `PASS_WITH_WARNING` hoặc `BLOCKED_DATA`. Phần hợp lệ được phép đăng ký bằng digest riêng; dữ liệu mâu thuẫn không được tự sửa hoặc ghép đoán. Kho/migration vẫn phải được kiểm thử bằng SQLite tạm và fixture đã làm sạch để không khóa tiến độ kỹ thuật. `trace_lsu_unit` chỉ trả dữ liệu thuộc snapshot đã đăng ký.

Trong quá trình phát triển bằng Gemini, `files` chỉ được trỏ tới fixture trong repo. Kiểm tra file thật là thao tác cục bộ do chủ sở hữu chạy; đầu ra chia sẻ cho tác tử chỉ gồm schema manifest và số tổng hợp đã làm sạch.

### Điều kiện mở đánh giá và shadow

- Mở phát lại lịch sử khi temporal/group split, thời điểm dự báo và kiểm tra rò rỉ đã được định nghĩa. Việc này không cần ngưỡng shadow.
- Mở chạy thử nghiệm bóng đọc-only khi báo cáo phát lại tự nhận `AUTO_SHADOW` hoặc `LEARNING_SHADOW` theo rubric có version/digest và có nút tắt/quay lại phiên bản trước.
- Thiếu điều kiện đánh giá hoặc shadow chỉ chặn đúng hoạt động phụ thuộc. Nó không được làm mất snapshot hợp lệ hoặc chặn kiểm thử kỹ thuật của API kế tiếp.

## 10. Hợp đồng phát lại lịch sử

```text
evaluate_lsu_replay(dataset_id, method_config, protocol, actor) -> EvaluationReport
evaluate_shadow_rubric(evaluation_id, rubric_version) -> EvaluationRun
```

### Chốt chặn

- Feature chỉ dùng event có thời gian không vượt `as_of_time`.
- Dataset/protocol/code/threshold digest phải đóng băng. Protocol bắt buộc có metric, chiều rủi ro, tham số EWMA, cửa sổ nền, khoảng dự báo, quy tắc ghép cảnh báo–outcome, feature allowlist và phép chia thời gian/Unit.
- Mỗi Unit có tối đa một cảnh báo trong một cửa sổ. Cảnh báo đúng là cảnh báo có NG cùng Unit trong khoảng dự báo; cảnh báo nhầm là có cảnh báo nhưng không có NG; bỏ sót là có NG nhưng không có cảnh báo. Lead time bằng thời điểm NG trừ thời điểm cảnh báo.
- Phương án `no_alert` có mọi NG là bỏ sót. Thiếu trường protocol hoặc chuỗi thời gian không dùng được thì EWMA trả `not_applicable`, không tự chọn luật khác.
- Luôn có phương án `no_alert` và EWMA cấu hình được để so sánh; nếu EWMA không áp dụng được thì báo lý do thay vì tự chọn luật khác.
- Báo cáo bắt buộc có cảnh báo đúng, cảnh báo nhầm, bỏ sót và thời gian cảnh báo sớm; nếu đủ mẫu mới báo thêm precision/recall/calibration.
- MVP chỉ cho phép một hồi quy logistic nhẹ trên CPU khi Data Gate và công thức cỡ mẫu trong rubric tự động đạt. Trước thời điểm đó không thêm dependency máy học; nhánh model trả `not_applicable` và báo cáo baseline vẫn hoàn thành.
- Threshold dùng mặc định versioned hoặc cấu hình cục bộ versioned. Kết quả là `AUTO_SHADOW`, `LEARNING_SHADOW`, `BLOCKED_DATA` hoặc `FAIL_TECHNICAL`; không có trạng thái điều khiển sản xuất.

## 11. Hợp đồng shadow thủ công và case dự đoán

```text
run_manual_shadow(evaluation_id, files, actor) -> ShadowRun
upsert_prediction_case(risk_assessment, actor) -> CaseRecord
record_shadow_outcome(assessment_id, decision, observed_outcome, actor) -> ShadowOutcome
record_missed_detection(shadow_run_id, unit_serial, observed_outcome, actor, rationale) -> ShadowOutcome
```

### Chốt chặn

- Baseline/model, schema, threshold và rubric version phải đúng bản đã tự chấm.
- Risk assessment có snapshot đầu vào, thời điểm đánh giá, threshold digest và phần giải thích yếu tố.
- File đầu vào shadow chỉ chứa dữ liệu có sẵn tại `as_of_time`; outcome/retest xảy ra sau thời điểm dự báo chỉ được nhập ở bước ghi phản hồi.
- Dedup/cooldown ngăn tạo bão case. Khóa idempotency dùng digest lô dữ liệu, Unit và cửa sổ đánh giá; không dùng thời điểm đồng hồ lúc chạy.
- Người dùng chọn file; chương trình tự kiểm và chạy khi rubric cho phép. Không scheduler hoặc worker nền trong MVP.
- Tạo/cập nhật case bằng idempotency key. Assessment đi qua `pending_case_link` → `linked`; lỗi có thể thử lại giữ `retryable_error`. Nếu lỗi giữa hai kho, lần chạy lại phải tìm case hiện có trước khi tạo mới; MVP không dựng outbox phân tán.
- Shadow chỉ ghi kho cục bộ; không gửi cảnh báo ngoài và không có hành động máy.
- Outcome `true_positive`, `false_alarm`, `missed_detection`, `unknown` có nguồn/digest. Nguồn máy hợp lệ được xác nhận tự động; mâu thuẫn thành `unknown`; người dùng có thể sửa bằng bản ghi append-only có lý do. Bỏ sót được ghi theo Unit trong shadow run dù trước đó không có assessment cảnh báo.

## 12. Hợp đồng cảnh báo có duyệt

```text
enable_in_app_alert_policy(policy, actor) -> AlertPolicy
create_preventive_action_proposal(case_id, action_id, actor) -> ArtifactProposal
record_action_outcome(proposal_id, outcome, actor, evidence) -> ActionOutcome
```

### Chốt chặn

- Chỉ mở sau shadow gate có owner approval, kill switch và rollback.
- Alert chỉ trong Workspace Chat cho role được phép.
- Hành động từ thư viện versioned, có evidence và human approval.
- Không có connector PLC/line control trong contract này.
