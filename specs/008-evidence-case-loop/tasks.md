# Danh mục công việc: Trợ lý công việc khép kín từ vụ việc đến phòng ngừa lỗi

**Đầu vào**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/workspace-evidence-loop.md`, `quickstart.md`.

**Baseline không làm lại**: commit `2bb7a5f` đã triển khai lưu case metadata từ Workspace Chat; 80 test tập trung đạt trong lượt lập kế hoạch. Các task dưới đây chỉ bao phủ việc còn thiếu hoặc kiểm toán/khóa nền này.

## Định dạng

- `[P]`: có thể chuẩn bị song song vì khác file và không phụ thuộc task chưa xong.
- `[USn]`: liên kết tới câu chuyện người dùng trong `spec.md`.
- Mỗi gate chỉ được đóng sau focused tests, full gate phù hợp và kiểm toán độc lập.

## Cách giao từng việc cho Gemini Flash

Kế hoạch dùng cách chia cuốn chiếu để tránh thiết kế thừa: chỉ chi tiết hóa US sắp làm; US sau được chi tiết hóa khi gate trước đã có bằng chứng. Mỗi lượt giao cho Gemini Flash chỉ giao **một mã công việc** và yêu cầu giữ nguyên các ranh giới sau:

1. Đọc mục story tương ứng trong `spec.md`, phần contract tương ứng trong `contracts/workspace-evidence-loop.md` và đúng các file được nêu trong task; không quét hoặc sửa toàn repo.
2. Viết hoặc cập nhật test trước đối với state, quyền, migration và dữ liệu append-only; chạy test tập trung để thấy lỗi đúng nguyên nhân trước khi sửa implementation.
3. Không thêm bộ khung, cơ sở dữ liệu, dịch vụ hoặc lớp trừu tượng mới nếu hợp đồng hiện có không yêu cầu.
4. Không sửa ngoài file của công việc, trừ import tối thiểu hoặc fixture dùng chung đã được nêu rõ; nếu cần mở rộng phạm vi thì dừng và báo lý do.
5. UI, lỗi và cảnh báo phải là tiếng Việt; không lộ traceback, đường dẫn hệ thống, nội dung `local_only` hoặc tên mô hình nội bộ.
6. Kết thúc bằng danh sách file đã đổi, lệnh test đã chạy, số test đạt/trượt và phần chưa xác minh. Không tự commit, push hoặc đánh dấu gate `PASS`.

Một công việc được xem là hoàn tất thi công khi test tập trung của công việc đạt, `py -3 -m compileall` đạt cho các file liên quan, `git diff --check` sạch và không có thay đổi ngoài phạm vi. Việc đóng gate vẫn do lượt kiểm toán độc lập thực hiện.

## Giai đoạn 1 — Khóa baseline và quyết định kiến trúc

- [X] T001 Ghi audit độc lập cho commit `2bb7a5f`, đối chiếu FR-002/FR-004/FR-016/FR-018 và lưu bằng chứng đã scrub trong `PROJECT_HANDOVER.md`
- [X] T002 [P] Soạn ADR cho ranh giới bốn kho, ba loại case và hai miền Agent trong `docs/adr/0007-evidence-case-loop-boundaries.md`
- [X] T003 [P] Bổ sung phân loại case/review/learning/prediction/artifact vào `00_governance/DATA_POLICY.md` và `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`
- [X] T004 [P] Bổ sung contract migration/retention của hai SQLite mới vào `docs/contracts/PERSISTED_DATA_COMPATIBILITY.md`
- [X] T005 Chốt vai trò/phạm vi, thời hạn lưu, dữ liệu thử nghiệm, đầu ra đầu tiên và điều kiện chạy ngầm trong `specs/008-evidence-case-loop/owner-decisions.example.yaml`

## Giai đoạn 2 — Nền tảng chặn mọi câu chuyện

- [X] T006 [P] Viết test upgrade/rollback/fault injection từ schema Cổng 1 trong `tests/test_workspace_case_migrations.py`
- [X] T007 Triển khai migration version, online backup và `quick_check` trong `src/aios_habit/workspace_case_migrations.py`
- [X] T008 [P] Viết test role/scope/expiry/revocation fail-closed trong `tests/test_workspace_case_authorization.py`
- [X] T009 Triển khai `RoleGrant` registry và authorization service trong `src/aios_habit/workspace_case_authorization.py`
- [X] T010 Mở rộng model nền `CaseActivity`, `CaseChecklistItem` và optimistic version trong `src/aios_habit/workspace_case_models.py`
- [X] T011 Migrate repository Cổng 1 sang schema versioned và transaction activity chain trong `src/aios_habit/workspace_case_repository.py`
- [X] T012 Bổ sung safe error codes, audit payload digest và cấm raw chat/excerpt trong `src/aios_habit/workspace_case_service.py`
- [ ] T013 Chạy Gate 1A theo `specs/008-evidence-case-loop/quickstart.md` và ghi kết quả vào `PROJECT_HANDOVER.md`

## Giai đoạn 3 — US1: Xem và quản lý hồ sơ trong Workspace Chat

**Mục tiêu**: người dùng mở danh sách/chi tiết case mà không hỏi lại RAG.

**Kiểm thử độc lập**: lưu case, mở mục “Hồ sơ vụ việc” trong tối đa ba thao tác, xem timeline/evidence, restart/readback và xử lý trace bị thiếu.

- [X] T014 [P] [US1] Viết contract test list/detail/filter/state transition và gắn thêm evidence trong `tests/test_workspace_case_service.py`
- [X] T015 [P] [US1] Viết test hành trình UI danh sách→chi tiết→mở trace, gắn thêm evidence và trace missing trong `tests/test_workspace_case_ui.py`
- [X] T016 [US1] Mở rộng `CaseRecord` với type/status/priority/owner/assignee/version trong `src/aios_habit/workspace_case_models.py`
- [X] T017 [US1] Thêm query list/detail/filter và optimistic transition trong `src/aios_habit/workspace_case_repository.py`
- [X] T018 [US1] Thêm use case triage/assign/checklist/open-trace và gắn thêm evidence đã làm sạch trong `src/aios_habit/workspace_case_service.py`
- [X] T019 [US1] Tạo renderer tiếng Việt cho list/detail/timeline và form gắn evidence trong `src/aios_habit/workspace_case_ui.py`
- [X] T020 [US1] Gắn mục “Hồ sơ vụ việc” vào `src/aios_habit/workspace_chat_app.py` và loại bỏ placeholder mô phỏng còn sót trong `src/aios_habit/i18n.py`
- [ ] T021 [US1] Chạy focused tests, restart/readback, import boundary và audit Gate 2 theo `specs/008-evidence-case-loop/quickstart.md`

## Giai đoạn 4 — US2: Giao và nhận thẩm định chuyên gia

**Mục tiêu**: có inbox chuyên gia, request/review append-only và phân xử xung đột.

**Kiểm thử độc lập**: sai role/scope/reason/digest bị từ chối; hai review trái chiều được giữ và case chuyển xung đột.

**Điều kiện bắt đầu**: T013 và T021 đã được kiểm toán độc lập và ghi bằng chứng; nếu chưa thì chỉ được đọc/chuẩn bị test, không mở phần triển khai US2.

**Thứ tự giao cho Gemini Flash**: T022 và T023 có thể chuẩn bị song song; sau đó lần lượt T024 → T025 → T026 → T027 → T028. Không gộp mô hình dữ liệu, kho lưu trữ, dịch vụ và giao diện vào một lượt.

- [ ] T022 [P] [US2] Trong `tests/test_workspace_case_expert_review.py`, viết riêng các test cho tạo yêu cầu đúng scope, từ chối role/scope hết hạn hoặc bị thu hồi, khóa `claim_digest`/`evidence_digest`, review append-only, supersede và giữ hai ý kiến trái chiều; chưa sửa phần triển khai
  - Đạt khi: test mới được thu thập thành công và đang trượt đúng vì API/mô hình dữ liệu/kho lưu trữ US2 chưa có, không vì lỗi fixture hoặc import.
- [ ] T023 [P] [US2] Trong `tests/test_workspace_expert_ui.py`, viết test hiển thị hàng chờ theo người nhận, form tạo yêu cầu, form `confirmed`/`rejected`/`needs_more_evidence`, thông báo lỗi tiếng Việt và không lộ dữ liệu kỹ thuật; chưa sửa phần triển khai giao diện
  - Đạt khi: mỗi hành trình UI có một test thành công dự kiến và các test từ chối input thiếu/sai quyền.
- [ ] T024 [US2] Trong `src/aios_habit/workspace_case_models.py`, thêm `ExpertRequest` và `ExpertReview` đúng trường, enum trạng thái/quyết định và validation tại mục 3.6–3.7 của `data-model.md`; chỉ cập nhật test model liên quan nếu cần
  - Đạt khi: mô hình dữ liệu từ chối ID/digest/lý do rỗng, chỉ nhận trạng thái hợp lệ và đọc lại ổn định mà không chứa bằng chứng thô.
- [ ] T025 [US2] Trong `src/aios_habit/workspace_case_repository.py` và migration hiện có, thêm bảng/index/query cho yêu cầu và review append-only; hỗ trợ list inbox, lấy lịch sử và thêm review mới nhưng không có đường update/delete record cũ
  - Đạt khi: upgrade/readback/restart và rollback fixture cũ đạt; ghi review cùng activity trong transaction và chuỗi digest vẫn hợp lệ.
- [ ] T026 [US2] Tạo `src/aios_habit/workspace_expert_service.py` với ba use case `request_expert_review`, `record_expert_review`, `resolve_review_conflict`; tái dùng authorization service hiện có để kiểm role/scope/thời hạn, khóa claim/evidence digest và chuyển trạng thái case đúng contract
  - Đạt khi: toàn bộ test T022 đạt; hai review trái chiều được giữ nguyên, case chuyển trạng thái cần phân xử và AI không có đường tự xác nhận.
- [ ] T027 [US2] Tạo `src/aios_habit/workspace_expert_ui.py` gồm hàng chờ của chuyên gia, chi tiết yêu cầu và form phản hồi tiếng Việt; UI chỉ gọi service, không tự quyết quyền hoặc ghi thẳng repository
  - Đạt khi: toàn bộ test T023 đạt; dữ liệu nhập thiếu lý do/sai quyền nhận thông báo tiếng Việt an toàn và không lộ traceback, đường dẫn hoặc digest nội bộ không cần thiết.
- [ ] T028 [US2] Gắn hàng chờ và chi tiết thẩm định vào `src/aios_habit/workspace_chat_app.py`, sau đó chạy kịch bản Gate 3 trong `specs/008-evidence-case-loop/quickstart.md`; chỉ cập nhật `PROJECT_HANDOVER.md` bằng bằng chứng đã làm sạch sau lượt kiểm toán độc lập
  - Đạt khi: tạo yêu cầu → người đúng scope xem inbox → phản hồi → restart/readback hoạt động; import boundary, test US2, audit chain và kiểm tra tiếng Việt đều đạt.

## Giai đoạn 5 — US3: Học từ phản hồi và dùng lại có truy vết

**Mục tiêu**: promotion bài học có quyền và case-memory retrieval riêng.

**Kiểm thử độc lập**: candidate không được search như sự thật; promoted có provenance; withdrawn biến mất khỏi search chuẩn; `library.sqlite` không đổi.

- [ ] T029 [P] [US3] Viết promotion/withdrawal/provenance tests trong `tests/test_workspace_case_learning.py`
- [ ] T030 [P] [US3] Viết search isolation/ranking/citation tests trong `tests/test_case_memory_search.py`
- [ ] T031 [US3] Thêm `LearningRecord` và migration tương thích thẻ cũ trong `src/aios_habit/workspace_case_models.py`
- [ ] T032 [US3] Triển khai promotion/withdrawal và adapter import opt-in trong `src/aios_habit/workspace_learning_service.py`
- [ ] T033 [US3] Triển khai chỉ mục/truy xuất case-memory riêng trong `src/aios_habit/case_memory_search.py`
- [ ] T034 [US3] Hiển thị bài học promoted có citation trong `src/aios_habit/workspace_case_ui.py` và `src/aios_habit/workspace_chat_app.py`
- [ ] T035 [US3] Chạy Gate 4, regression learning cũ và chứng minh `library.sqlite` bất biến theo `specs/008-evidence-case-loop/quickstart.md`

## Giai đoạn 6 — US4: Trợ lý điều tra line chủ động

**Mục tiêu**: timeline, nhóm lặp, gap questions, relevance review và pilot thật.

**Kiểm thử độc lập**: không match trả rỗng; event giữ `suspected`; mapping cần manifest duyệt; một case thật đi đến báo cáo/outcome.

- [ ] T036 [P] [US4] Viết provenance/timezone/no-fallback tests trong `tests/test_line_log_parser.py`
- [ ] T037 [P] [US4] Viết timeline/repeat/gap/relevance tests trong `tests/test_workspace_case_line_pilot.py`
- [ ] T038 [US4] Thêm source digest, collector version, timezone và bỏ fallback event gần nhất trong `src/aios_habit/line_log_parser.py`
- [ ] T039 [US4] Triển khai timeline/grouping/gap checklist tất định trong `src/aios_habit/line_investigation_service.py`
- [ ] T040 [US4] Triển khai mapping manifest có version/approval guard trong `src/aios_habit/line_mapping_service.py`
- [ ] T041 [US4] Thêm UI timeline/manh mối/câu hỏi thiếu/mapping đã duyệt trong `src/aios_habit/workspace_case_ui.py`
- [ ] T042 [US4] Chạy Gate B/C privacy regression và focused tests theo `specs/008-evidence-case-loop/quickstart.md`
- [ ] T043 [US4] Chạy một pilot line thật được phép và ghi SOP/mã lỗi/report/reviewer/outcome đã scrub trong `PROJECT_HANDOVER.md`

## Giai đoạn 7 — US5: Agent tạo đầu ra công việc có kiểm soát

**Mục tiêu**: capability registry và artifact versioned cho báo cáo/SOP rồi mở rộng thiết kế công đoạn.

**Kiểm thử độc lập**: evidence rỗng, capability tắt, approver sai, overwrite/protected path đều bị chặn; artifact approved truy vết đủ.

- [ ] T044 [P] [US5] Viết capability/risk/verifier/approver contract tests trong `tests/test_agent_artifact_capabilities.py`
- [ ] T045 [P] [US5] Viết version/export/path/approval invalidation tests trong `tests/test_workspace_artifact_service.py`
- [ ] T046 [US5] Thêm `CapabilityDefinition`, `ArtifactProposal`, `ArtifactVersion`, `ApprovalRecord` trong `src/aios_habit/workspace_case_models.py`
- [ ] T047 [US5] Triển khai capability registry fail-closed trong `src/aios_habit/agent_artifact_capabilities.py`
- [ ] T048 [US5] Tổng quát hóa SOP/report thành artifact pipeline có version trong `src/aios_habit/workspace_artifact_service.py`
- [ ] T049 [US5] Tạo preview/diff/verify/approve UI trong `src/aios_habit/workspace_artifact_ui.py`
- [ ] T050 [US5] Thêm adapter format thiết kế công đoạn đầu tiên theo owner decision trong `src/aios_habit/artifact_adapters/`
- [ ] T051 [US5] Chạy Gate 6, protected-path/privacy regression và artifact readback theo `specs/008-evidence-case-loop/quickstart.md`

## Giai đoạn 8 — US6: Agent hỗ trợ lập trình trong workspace tách biệt

**Mục tiêu**: case `agent_work` nối task pack, proposal, command, observed test và audit.

**Kiểm thử độc lập**: deny runtime/factory data; proposal digest-bound; self-report PASS không observed evidence bị từ chối; không tự merge/push.

- [ ] T052 [P] [US6] Viết workspace separation và forbidden-path tests trong `tests/test_workspace_code_agent_policy.py`
- [ ] T053 [P] [US6] Viết task-pack→proposal→approval→observed-test flow trong `tests/test_workspace_code_agent_case.py`
- [ ] T054 [US6] Mở rộng policy để bind approval với proposal/command digest trong `src/aios_habit/workspace_agent_policy.py`
- [ ] T055 [US6] Tạo integration service cho case `agent_work` và task pack trong `src/aios_habit/workspace_code_agent_service.py`
- [ ] T056 [US6] Nối observed evidence/result import và rollback ref trong `src/aios_habit/agent_result_import.py`
- [ ] T057 [US6] Thêm UI proposal/diff/command/test/approve tiếng Việt trong `src/aios_habit/workspace_code_agent_ui.py`
- [ ] T058 [US6] Chạy Gate 7 và toàn bộ test Agent IDE/task pack/result import theo `specs/008-evidence-case-loop/quickstart.md`

## Giai đoạn 9 — US7: Nền dữ liệu dự đoán LSU/Drum/DLP

**Mục tiêu**: store/version/schema/domain adapter với LSU/Iris là lát cắt đầu tiên.

**Kiểm thử độc lập**: stable keys/unit/time/version/labels được kiểm; thiếu một điều kiện readiness trả `blocked`; chưa train model.

- [ ] T059 [P] [US7] Viết prediction store migration/backup/rollback tests trong `tests/test_prediction_store_migrations.py`
- [ ] T060 [P] [US7] Viết data contract/readiness/leakage validation tests trong `tests/test_prediction_data_gate.py`
- [ ] T061 [US7] Tạo package và model lõi trong `src/aios_habit/production_prediction/models.py`
- [ ] T062 [US7] Triển khai SQLite repository/migrations trong `src/aios_habit/production_prediction/repository.py`
- [ ] T063 [US7] Triển khai snapshot ingest, quality report và six-condition readiness trong `src/aios_habit/production_prediction/data_gate.py`
- [ ] T064 [US7] Triển khai adapter LSU/Iris từ data dictionary đã duyệt trong `src/aios_habit/production_prediction/adapters/lsu_iris.py`
- [ ] T065 [US7] Tạo CLI local-only cho validate/snapshot/readiness trong `src/aios_habit/production_prediction/cli.py`
- [ ] T066 [US7] Chạy Gate 8 trên dataset được phép hoặc ghi `BLOCKED` có danh sách thiếu trong `PROJECT_HANDOVER.md`

## Giai đoạn 10 — US8: Huấn luyện và đánh giá model có trách nhiệm

**Mục tiêu**: protocol đóng băng, baseline công bằng, model card và threshold owner-approved.

**Kiểm thử độc lập**: future leakage bị chặn; report đủ metric/digest; model không tự lên shadow.

- [ ] T067 [P] [US8] Viết temporal/group split và `as_of_time` leakage tests trong `tests/test_prediction_feature_snapshots.py`
- [ ] T068 [P] [US8] Viết metrics/calibration/stability/model-card tests trong `tests/test_prediction_evaluation.py`
- [ ] T069 [US8] Triển khai feature snapshot versioned trong `src/aios_habit/production_prediction/features.py`
- [ ] T070 [US8] Triển khai baseline no-alert và EWMA/CUSUM trong `src/aios_habit/production_prediction/baselines.py`
- [ ] T071 [US8] Thêm optional dependency group prediction sau Data Gate trong `pyproject.toml` và `uv.lock`
- [ ] T072 [US8] Triển khai candidate training/temporal evaluation/calibration trong `src/aios_habit/production_prediction/evaluation.py`
- [ ] T073 [US8] Sinh model card và approval manifest trong `src/aios_habit/production_prediction/model_registry.py`
- [ ] T074 [US8] Chạy Gate 9 với protocol đóng băng và ghi model/dataset/code/threshold digests trong `PROJECT_HANDOVER.md`

## Giai đoạn 11 — US9: Shadow prediction tạo hồ sơ dự đoán

**Mục tiêu**: replay/scheduler local tạo risk assessment và case có dedup/cooldown, thu outcome thật.

**Kiểm thử độc lập**: signal tạo case một lần; feature snapshot đầy đủ; outcome đúng/sai/unknown; không alert/control.

- [ ] T075 [P] [US9] Viết shadow run/dedup/cooldown tests trong `tests/test_prediction_shadow_runtime.py`
- [ ] T076 [P] [US9] Viết prediction-case/outcome/missed-detection tests trong `tests/test_prediction_case_loop.py`
- [ ] T077 [US9] Triển khai shadow runner và risk assessment trong `src/aios_habit/production_prediction/shadow.py`
- [ ] T078 [US9] Triển khai outbox/reconciliation/idempotent upsert case `prediction` qua service guard trong `src/aios_habit/prediction_case_service.py`
- [ ] T079 [US9] Thêm dashboard shadow/outcome review tiếng Việt trong `src/aios_habit/prediction_shadow_ui.py`
- [ ] T080 [US9] Chạy shadow replay và regression cấm external alert/PLC theo `specs/008-evidence-case-loop/quickstart.md`
- [ ] T081 [US9] Thu đủ số case/thời gian theo owner decision và ghi shadow gate report trong `PROJECT_HANDOVER.md`

## Giai đoạn 12 — US10: Cảnh báo có duyệt và đề xuất phòng ngừa

**Mục tiêu**: chỉ mở in-app alert sau shadow; action library có version/human approval/outcome.

**Kiểm thử độc lập**: thiếu owner approval/kill switch bị chặn; role đúng thấy alert; action không plant control.

- [ ] T082 [P] [US10] Viết alert-policy/kill-switch/escalation tests trong `tests/test_prediction_alert_policy.py`
- [ ] T083 [P] [US10] Viết preventive-action/outcome tests trong `tests/test_preventive_action_service.py`
- [ ] T084 [US10] Triển khai in-app alert policy và kill switch trong `src/aios_habit/production_prediction/alert_policy.py`
- [ ] T085 [US10] Triển khai action library versioned và outcome trong `src/aios_habit/preventive_action_service.py`
- [ ] T086 [US10] Gắn alert/action proposal vào Workspace Chat trong `src/aios_habit/prediction_shadow_ui.py`
- [ ] T087 [US10] Chạy Gate 11 và chứng minh không connector plant-control theo `specs/008-evidence-case-loop/quickstart.md`

## Giai đoạn 13 — US11: NAS, pilot tổ chức và phần mở rộng US7 cho Drum/DLP

**Mục tiêu**: runtime evidence thật cho thư viện chung, bàn giao liên ca và mở rộng miền sau LSU.

**Kiểm thử độc lập**: NAS one-writer/multi-reader + restore thật; hai vai trò mở cùng case; Drum/DLP có Data Gate riêng.

- [ ] T088 [P] [US11] Soạn runbook NAS/pilot không chứa dữ liệu thật trong `docs/operations/WORKSPACE_LIBRARY_AND_CASE_PILOT.md`
- [ ] T089 [US11] Chạy NAS one-writer/multi-reader, backup/restore/`quick_check` thật và cập nhật Gate A trong `PROJECT_HANDOVER.md`
- [ ] T090 [US11] Chạy pilot bàn giao một case giữa ít nhất hai vai trò/ca và ghi acceptance đã scrub trong `PROJECT_HANDOVER.md`
- [ ] T091 [US7] Triển khai Data Gate adapter Drum trong `src/aios_habit/production_prediction/adapters/drum.py`
- [ ] T092 [US7] Triển khai Data Gate adapter DLP trong `src/aios_habit/production_prediction/adapters/dlp.py`
- [ ] T093 [US7] Chạy readiness/evaluation/shadow gate độc lập cho Drum và DLP hoặc ghi từng miền `BLOCKED` trong `PROJECT_HANDOVER.md`

## Giai đoạn 14 — Hội tụ, tài liệu và bàn giao

- [ ] T094 [P] Cập nhật kiến trúc bốn kho, case loop, Agent boundary và prediction pipeline trong `ARCHITECTURE.md`
- [ ] T095 [P] Cập nhật trạng thái từng gate bằng evidence thật trong `ROADMAP.md` và `Thảo_luận_AI_dự_đoán_lỗi_LSU.md`
- [ ] T096 [P] Cập nhật UI guide, retention/backup, PIA và migration runbook trong `docs/user/WORKSPACE_CHAT_USER_GUIDE.md` và `docs/operations/`
- [ ] T097 Chạy `py -3 -m compileall src tests`, focused suites và `py -3 -m pytest -q`, ghi exit code/test count trong `PROJECT_HANDOVER.md`
- [ ] T098 Chạy `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit`, import Workspace Chat, docs check, `git diff --check` và `git diff --cached --check`
- [ ] T099 Chạy restore drill, privacy regression, no-legacy-import và no-plant-control audit theo `specs/008-evidence-case-loop/quickstart.md`
- [ ] T100 Thực hiện kiểm toán độc lập từng gate/commit và chỉ đánh dấu `DONE` cho yêu cầu có runtime evidence trong `PROJECT_HANDOVER.md`

## Phụ thuộc và thứ tự

```text
Giai đoạn 1 → Giai đoạn 2
Giai đoạn 2 → US1 → US2 → US3 → US4
Giai đoạn 2 → US5 → US6
Giai đoạn 2 → US7 → US8 → US9 → US10
US4 + US9 + quyết định owner → US11
Các story mong muốn hoàn tất → Giai đoạn 14
```

- US1–US4 phải tuần tự vì expert/learning/pilot cần case UI và state machine.
- US5–US6 có thể bắt đầu sau nền tảng nhưng Gate 6 phải đóng trước Gate 7.
- US7–US10 phải tuần tự; thiếu dataset/owner giữ track prediction `BLOCKED` mà không chặn US1–US6.
- US11 chỉ mở adapter Drum/DLP sau vertical slice LSU/Iris đạt shadow gate; NAS evidence chạy độc lập.

## Cơ hội chuẩn bị song song

- Sau Giai đoạn 2, nhóm case UI, capability Agent và data contract prediction có thể chuẩn bị ở các file tách biệt; mỗi gate vẫn cần audit riêng.
- Test contract `[P]` có thể được viết song song trước implementation trong cùng story.
- T094–T096 có thể chuẩn bị song song sau khi hành vi tương ứng đã đóng gate; không được viết trạng thái DONE trước evidence.

## Phạm vi MVP đề xuất

MVP tiếp theo không phải toàn chương trình mà là **Gate 1A + US1**: migration an toàn và mục “Hồ sơ vụ việc” dùng được. Sau demo/acceptance, tiếp tục US2–US3 để khép vòng chuyên gia–bài học. Prediction không được rút gọn thành model giả chỉ để có demo.

## Quy tắc thực thi

- Viết test trước cho contract/state/policy quan trọng và xác minh test fail đúng lý do trước implementation.
- Mỗi gate có commit nhỏ, allowlist rõ, rollback và reviewer độc lập với implementer.
- Không commit `local_cases/`, `local_runs/`, raw log, dataset/model thật, ảnh/sơ đồ mật hoặc `.env`.
- Không tự mở code implementation cho đến khi chủ sở hữu phê duyệt kế hoạch và quyết định gate liên quan.
