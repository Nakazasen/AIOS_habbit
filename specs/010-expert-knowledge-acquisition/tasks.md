# Nhiệm vụ: Tiếp nhận tri thức chuyên gia (Goal 010)

Tài liệu này giữ nguyên T000–T080 như lịch sử triển khai. Kiểm toán ngày 2026-09-09 mở lại Goal để sửa lỗi và giản lược theo ADR-0009 bản sửa; các task đã hoàn thành trước đây không chứng minh phần R1–R5 bên dưới đã đạt.

## Giai đoạn 1 — G0: Nghiên cứu, khóa mặc định và fixture

- [x] T000 Nghiên cứu 6 hướng kỹ thuật và lập ma trận adopt/adapt/reject có pin version trong `specs/010-expert-knowledge-acquisition/research.md`
- [x] T001 Khóa sáu quyết định mặc định trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T002 Soạn và chốt ADR-0009 trong `docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md`
- [x] T003 Thêm cờ tính năng `010` fail-closed trong `src/aios_habit/feature_flags.py`
- [x] T004 Chuẩn bị 2 danh tính chuyên gia fixture không chứa secret trong `tests/fixtures/expert_interview/identities/`
- [x] T005 Chuẩn bị 5 gap kiến thức và 3 hội thoại phỏng vấn trong `tests/fixtures/expert_interview/gaps/` và `conversations/`
- [x] T006 Chuẩn bị 1 file audio WAV mono 16kHz synthetic hợp lệ và 1 file corrupt trong `tests/fixtures/expert_interview/audio/`
- [x] T007 [P] Viết test kiểm tra fixture hygiene, audio hợp lệ và cờ tính năng trong `tests/test_expert_interview_fixture_hygiene.py`

## Giai đoạn 2 — G1: Danh tính và phân quyền chuyên gia

- [x] T008 [US1] Định nghĩa `VerifiedPrincipal`, `ExpertProfile` và `ScopeGrant` trong `src/aios_habit/expert_identity.py`
- [x] T009 [US1] Tạo `WindowsOSIdentityProvider` đọc OS user và `FixtureIdentityProvider` trong `src/aios_habit/expert_identity.py`
- [x] T010 [US1] Thêm bảng `expert_profiles` và `expert_scope_grants` trong `src/aios_habit/expert_interview_repository.py`
- [x] T011 [US1] Thêm migration an toàn không xóa bảng cũ trong `src/aios_habit/workspace_case_migrations.py`
- [x] T012 [US1] Thêm màn hình phân quyền chuyên gia thuần Việt trong `src/aios_habit/workspace_case_ui.py`
- [x] T013 [US1] Cài audit event và lý do thu hồi quyền trong `src/aios_habit/expert_identity.py`
- [x] T014 [US1] Cài chặn mạo danh, profile suspended/revoked, grant hết hạn và cấm fallback về `local_admin` khi bật multi-user trong `src/aios_habit/expert_identity.py`
- [x] T015 [P] [US1] Viết unit/contract test cho provider, grant validation và impersonation denial trong `tests/test_expert_identity.py`

## Giai đoạn 3 — G2: US2 phát hiện gap kiến thức

- [x] T016 [US2] Định nghĩa `KnowledgeGapCandidate`, `CoverageEvaluation` và digest trong `src/aios_habit/knowledge_coverage.py`
- [x] T017 [US2] Cài adapter lấy inventory và retrieval receipt từ pipeline BGE-M3 hiện có trong `src/aios_habit/knowledge_coverage.py`
- [x] T018 [US2] Cài bộ sinh gap tất định cho thiếu nguồn, thiếu phần bắt buộc và metadata cũ trong `src/aios_habit/knowledge_coverage.py`
- [x] T019 [US2] Cài phát hiện mâu thuẫn ngữ nghĩa có trích dẫn snippet đối chiếu trong `src/aios_habit/knowledge_coverage.py`
- [x] T020 [US2] Nối C-AGENT qua Brain Gateway đọc tín hiệu gap, giải thích và xếp hạng candidate; loại bỏ citation bịa đặt trong `src/aios_habit/knowledge_coverage.py`
- [x] T021 [US2] Thêm bảng lưu coverage snapshot và gap candidate trong `src/aios_habit/expert_interview_repository.py`
- [x] T022 [US2] Thêm màn hình xem gap, xếp hạng và phê duyệt candidate thuần Việt trong `src/aios_habit/workspace_case_ui.py`
- [x] T023 [P] [US2] Viết test deterministic gap, BGE-M3 retrieval, C-AGENT qua Brain Gateway và digest trong `tests/test_knowledge_coverage.py`
- [x] T024 [US2] Thêm migration cho bảng coverage snapshot và gap candidate trong `src/aios_habit/workspace_case_migrations.py`

## Giai đoạn 4 — G3: US2 lập kế hoạch phỏng vấn thích nghi

- [x] T025 [US2] Định nghĩa `InterviewPlan`, `InterviewBudget`, `CompletionRubric`, `SeedQuestion` và digest trong `src/aios_habit/expert_interview_models.py`
- [x] T026 [US2] Cài thuật toán chọn chuyên gia theo verified profile và scope grant trong `src/aios_habit/expert_interview_service.py`
- [x] T027 [US2] Sinh seed questions bám sát gap type, scope và required aspects trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T028 [US2] Khóa ngân sách hữu hạn và escalation owner bắt buộc khi duyệt plan trong `src/aios_habit/expert_interview_service.py`
- [x] T029 [P] [US2] Viết test sinh câu hỏi từ gap, chọn chuyên gia, budget hữu hạn và rubric validation trong `tests/test_adaptive_expert_interview.py`

## Giai đoạn 5 — G4: US3 phỏng vấn thích nghi dạng văn bản

- [x] T030 [US3] Định nghĩa session, turn, checkpoint và transition validator trong `src/aios_habit/expert_interview_models.py`
- [x] T031 [US3] Cài lưu session, turn và checkpoint append-only, idempotent trong `src/aios_habit/expert_interview_repository.py`
- [x] T032 [US3] Cài máy trạng thái phiên, bind verified principal và re-check quyền mỗi turn trong `src/aios_habit/expert_interview_service.py`
- [x] T033 [US3] Nối C-AGENT qua Brain Gateway sinh câu hỏi thích nghi theo schema, trigger refs và budget limit trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T034 [US3] Cài bộ lọc chống câu hỏi dẫn dắt, ngoài scope và trùng lặp ngữ nghĩa trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T035 [US3] Hỗ trợ câu trả lời không rõ, chưa chắc chắn, đính chính, tạm dừng và dừng phiên trong `src/aios_habit/expert_interview_service.py`
- [x] T036 [US3] Thêm giao diện chat phỏng vấn, thanh tiến độ, budget counter và nút pause/stop thuần Việt trong `src/aios_habit/workspace_case_ui.py`
- [x] T037 [P] [US3] Viết test luồng hỏi-đáp, guardrails, budget cutoff, pause/resume và stop escalation trong `tests/test_adaptive_expert_interview.py`
- [x] T038 [P] [US3] Viết test timeout, schema repair, restart/resume và duplicate submission idempotency trong `tests/test_expert_interview_recovery.py`

## Giai đoạn 6 — G5: US3 phỏng vấn bằng giọng nói và chép lời cục bộ

- [x] T039 [US3] Định nghĩa consent record, audio path validator, transcript segment và critical token trong `src/aios_habit/local_transcription.py`
- [x] T040 [US3] Viết benchmark `whisper.cpp` và `faster-whisper` trên fixture tiếng Việt trong `scripts/benchmark_local_transcription.py`
- [x] T041 [US3] Tự chọn engine theo điểm benchmark tất định rồi ghi version, checksum, license và tài nguyên vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T042 [US3] Cài một adapter local đã thắng benchmark, pin version và timeout trong `src/aios_habit/local_transcription.py`
- [x] T043 [US3] Lưu audio/transcript dưới `local_only` root cấu hình sẵn với path validation và digest trong `src/aios_habit/expert_interview_repository.py`
- [x] T044 [US3] Thêm lời đồng ý theo phiên bản, chỉ báo đang ghi, rút đồng ý và phương án trả lời bằng chữ trong `src/aios_habit/workspace_case_ui.py`
- [x] T045 [US3] Thêm sửa bản chép lời theo đoạn và xác nhận mã máy, con số, đơn vị trong `src/aios_habit/workspace_case_ui.py`
- [x] T046 [P] [US3] Viết test consent lifecycle, device failure, corrupt audio, critical token và UTF-8 trong `tests/test_local_transcription.py`
- [x] T047 [P] [US3] Viết privacy test không có raw audio/transcript trong Git, case DB, log và provider payload trong `tests/test_expert_interview_privacy.py`

## Giai đoạn 7 — G6: US4 claim, nguồn và xung đột

- [x] T048 [US4] Định nghĩa `KnowledgeClaim`, source refs, uncertainty và conflict links trong `src/aios_habit/knowledge_claim_extractor.py`
- [x] T049 [US4] Trích claim theo schema và kiểm tra support tối thiểu với source refs trong `src/aios_habit/knowledge_claim_extractor.py`
- [x] T050 [US4] Chặn source stale và transcript có critical token chưa xác nhận trong `src/aios_habit/knowledge_claim_extractor.py`
- [x] T051 [US4] Phát hiện claim overlap/conflict và tạo escalation, không auto-resolve, trong `src/aios_habit/knowledge_claim_extractor.py`
- [x] T052 [US4] Lưu claim event/version và review decision trong `src/aios_habit/expert_interview_repository.py`
- [x] T053 [P] [US4] Viết test unsupported claim, exact provenance, uncertainty, correction và conflict trong `tests/test_knowledge_claims.py`

## Giai đoạn 8 — G7: US4 SOP/bài học và phê duyệt

- [x] T054 [US4] Định nghĩa artifact, version, claim map và approval matrix trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T055 [US4] Sinh SOP và lesson candidate tiếng Việt từ claim được phép trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T056 [US4] Tạo diff giữa artifact versions và mục cần quyết định cho conflict trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T057 [US4] Cài approve/reject/request-change/revoke theo exact digest và scope trong `src/aios_habit/expert_interview_service.py`
- [x] T058 [US4] Thêm giao diện xem trước nguồn, so sánh phiên bản và phê duyệt thuần Việt trong `src/aios_habit/workspace_case_ui.py`
- [x] T059 [P] [US4] Viết test self-approval policy, stale digest, missing approval, conflict và revoke trong `tests/test_controlled_knowledge_artifact.py`

## Giai đoạn 9 — G8: US5 xuất bản vào thư viện

- [x] T060 [US5] Định nghĩa `PublicationPackage` bất biến và acceptance question set trong `src/aios_habit/knowledge_publication.py`
- [x] T061 [US5] Xác minh approval, status, digest và collection trước publication trong `src/aios_habit/knowledge_publication.py`
- [x] T062 [US5] Nối backup và `LibraryWriterLease` hiện có, không ghi SQL trực tiếp từ model, trong `src/aios_habit/knowledge_publication.py`
- [x] T063 [US5] Nạp Markdown/JSON qua pipeline collection hiện có và ghi source digest trong `src/aios_habit/knowledge_publication.py`
- [x] T064 [US5] Chạy SQLite `quick_check`, retrieval acceptance và receipt trước trạng thái published trong `src/aios_habit/knowledge_publication.py`
- [x] T065 [US5] Cài revoke, supersede, re-index và rollback receipt trong `src/aios_habit/knowledge_publication.py`
- [x] T066 [US5] Thêm màn hình đưa vào thư viện/thu hồi cùng trạng thái sao lưu/kiểm tra bằng tiếng Việt trong `src/aios_habit/workspace_case_ui.py`
- [x] T067 [P] [US5] Viết test unpublished/conflicted/revoked filtering và stale package trong `tests/test_knowledge_publication.py`
- [x] T068 [P] [US5] Viết fault test writer busy, disk-full simulation, interrupted ingest và restore trong `tests/test_knowledge_publication_recovery.py`

## Giai đoạn 10 — G9: Đánh giá fine-tune có điều kiện

- [x] T069 Tạo baseline retrieval/prompt và holdout split chống leakage trong `scripts/evaluate_expert_learning_baseline.py`
- [x] T070 Cài eligibility rubric không có side effect trong `src/aios_habit/fine_tune_eligibility.py`
- [x] T071 Viết test không dùng raw audio/transcript/local-only và không tự chạy train trong `tests/test_fine_tune_eligibility.py`
- [x] T072 Ghi kết luận `NOT_APPLICABLE` cho fine-tune trong feature 010 cùng số đo baseline vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Giai đoạn 11 — G10: Pilot thật, bảo mật và đóng cổng

- [x] T073 Cập nhật threat model, privacy impact và retention đã duyệt trong `docs/security/THREAT_MODEL.md` và `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`
- [x] T074 Chạy E2E fixture trọn vòng gap đến chat, claim, SOP, publish và revoke trong `tests/test_expert_knowledge_e2e.py`
- [x] T075 Chạy E2E Windows với path tiếng Việt/khoảng trắng, restart và local transcription theo `specs/010-expert-knowledge-acquisition/quickstart.md`
- [x] T076 Chạy diễn tập tự động tối thiểu 2 danh tính chuyên gia fixture, 2 scope, 3 phiên và 5 gap; chỉ ghi receipt đã làm sạch vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T077 Đo 5 đơn vị tri thức, 1 quy trình fixture, provenance/citation, unauthorized access và critical-token confirmation theo SC-001–SC-008 trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T078 Chạy đầy đủ quality gate, quét cấm từ kỹ thuật tiếng Anh trên giao diện và ghi command, exit code, phạm vi vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T079 Đồng bộ trạng thái thực tế trong `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md` và `Thảo_luận_AI_dự_đoán_lỗi_LSU.md`
- [x] T080 Chạy Audit Specialist bằng agent/phiên tách biệt, tự sửa và kiểm toán lại logic, privacy, quyền và evidence; chuyển Gate Card sang `TECHNICAL_READY` khi SC-001–SC-010 đạt trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Phụ thuộc và chiến lược

T000 phải hoàn tất trước code để không viết lại pattern đã trưởng thành. T001–T007 khóa mặc định và tự mở G1 sau audit agent. G2 tạo gap; G3 lập plan; G4 là MVP chat văn bản; G5 audio local; G6–G8 claim, duyệt và thư viện; G9 tự kết luận fine-tune `NOT_APPLICABLE`; G10 diễn tập kỹ thuật bằng fixture.

Task `[P]` chỉ chạy song song khi không sửa cùng file và task nền của giai đoạn đã xong. Sau mỗi cổng, Gemini tự chuyển việc cho Audit Specialist ở agent/phiên tách biệt, sửa finding rồi tiếp tục; không chờ con người quyết định phase và không tự vừa implement vừa ghi PASS.

## Giai đoạn 12 — Mở lại: Chốt quyết định và finding

- [x] T081 Ghi quyết định nhóm tin cậy, tên ghi nhận không cấp quyền và khóa ghi chỉ điều phối đồng thời trong `docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md`
- [x] T082 Đồng bộ đặc tả, kế hoạch, mô hình dữ liệu, hợp đồng và kịch bản kiểm chứng mới trong `specs/010-expert-knowledge-acquisition/`

## Giai đoạn 13 — R1: Sửa ranh giới dữ liệu và hành vi sai

- [ ] T083 [P] [US2] Viết test chứng minh audio và bản chép lời thô không được lưu trong `workspace_cases.sqlite` tại `tests/test_expert_interview_privacy.py`
- [ ] T084 [US2] Di chuyển nội dung bản chép lời thô sang kho `local_only` và chỉ giữ locator/digest đã làm sạch trong `src/aios_habit/expert_interview_repository.py` cùng migration tại `src/aios_habit/workspace_case_migrations.py`
- [ ] T085 [P] [US2] Viết test runtime không được fallback sang mock rồi báo kết quả chép lời thật trong `tests/test_local_transcription.py`
- [ ] T086 [US2] Tách adapter thật khỏi mock fixture và trả thông báo tiếng Việt có bước tiếp theo khi bộ máy thật chưa sẵn sàng trong `src/aios_habit/local_transcription.py`
- [ ] T087 [P] [US4] Bổ sung test trạng thái xuất bản, thu hồi và khôi phục phải khớp dữ liệu thực trong `tests/test_knowledge_publication.py` và `tests/test_knowledge_publication_recovery.py`
- [ ] T088 [US4] Sửa kiểm tra nghiệm thu, thu hồi và rollback để không ghi thành công giả hoặc giữ nội dung đã thu hồi trong truy xuất tại `src/aios_habit/knowledge_publication.py`

## Giai đoạn 14 — R2: Cộng tác tin cậy và trách nhiệm

- [ ] T089 [P] [US3] Viết test hợp đồng tên OS chỉ điền sẵn, có thể sửa và không cấp quyền trong `tests/test_expert_identity.py`
- [ ] T090 [US1] Bỏ hồ sơ chuyên gia, scope grant và tái kiểm tra quyền khỏi điều kiện bắt đầu/tiếp tục phỏng vấn của Goal 010 trong `src/aios_habit/expert_interview_service.py`
- [ ] T091 [US3] Thêm `DecisionRecord` gồm tên ghi nhận, máy, thời điểm, độ tự tin, căn cứ, nguồn đã kiểm tra và xác nhận trách nhiệm trong `src/aios_habit/controlled_knowledge_artifact.py` và `src/aios_habit/expert_interview_repository.py`
- [ ] T092 [P] [US3] Viết test quyết định thiếu trường, nội dung đổi phiên bản và tên tự khai không bị mô tả là xác thực trong `tests/test_controlled_knowledge_artifact.py`
- [ ] T093 [US3] Thay điều kiện vai trò/scope/cấm tự duyệt bằng kiểm tra nội dung đúng phiên bản và thông tin trách nhiệm đầy đủ trong `src/aios_habit/expert_interview_service.py`

## Giai đoạn 15 — R3: Chọn thư viện và ghi snapshot an toàn

- [ ] T094 [P] [US1] Viết test chọn thư viện cá nhân/dùng chung và đổi qua lại không cần restart trong `tests/test_workspace_chat_store.py`
- [ ] T095 [US1] Thêm lựa chọn thư viện hiện hành dùng chung đường lưu trữ sẵn có, không thêm công tắc cấu hình hoặc hệ tài khoản, trong `src/aios_habit/workspace_chat_store.py`
- [ ] T096 [P] [US4] Viết fault test hai lượt ghi, khóa bận, mất kết nối, hết dung lượng và bản cũ còn dùng được trong `tests/test_knowledge_publication_recovery.py`
- [ ] T097 [US4] Hoàn thiện luồng bản sao cục bộ → khóa ghi ngắn hạn → kiểm tra → sao lưu → thay snapshot → giải phóng khóa trong `src/aios_habit/knowledge_publication.py`

## Giai đoạn 16 — R4: Giao diện bốn chặng cho người không chuyên

- [ ] T098 [P] [US5] Viết smoke test chứng minh bốn chặng Goal 010 đều truy cập được từ Workspace Chat trong `tests/test_workspace_chat_app_smoke.py`
- [ ] T099 [US5] Tạo điều hướng bốn chặng “Chọn thư viện”, “Phỏng vấn”, “Kiểm tra bản nháp”, “Đưa vào thư viện” và nối các màn hiện đang không được gọi trong `src/aios_habit/workspace_case_ui.py`
- [ ] T100 [US1] Thêm hai lựa chọn thư viện với mô tả đời thường, hiển thị lựa chọn hiện hành và cho đổi không restart trong `src/aios_habit/workspace_case_ui.py`
- [ ] T101 [US2] Bỏ chọn chuyên gia/scope/budget khỏi luồng chính, bỏ công tắc fixture và gom hành động phụ vào phần thu gọn trong `src/aios_habit/workspace_case_ui.py`
- [ ] T102 [US3] Hợp nhất xem, sửa, nguồn và form trách nhiệm; dùng một nút chính “Xác nhận và đưa vào thư viện” trong `src/aios_habit/workspace_case_ui.py`
- [ ] T103 [US4] Cho thu hồi từ lịch sử mà không nhập mã gói và đổi lỗi khóa bận/thư mục lỗi thành hướng dẫn thử lại trong `src/aios_habit/workspace_case_ui.py`
- [ ] T104 [P] [US5] Mở rộng bộ quét để phát hiện `fixture`, `digest`, `claim`, `approved`, `Markdown`, `JSON`, `lease` và trạng thái nội bộ trên bề mặt chính trong `scripts/check_user_facing_vietnamese.py`
- [ ] T105 [P] [US5] Viết test chữ giao diện, một hành động chính mỗi chặng và chi tiết kỹ thuật ẩn mặc định trong `tests/test_workspace_case_ui.py`

## Giai đoạn 17 — R5: Kiểm chứng và đóng lại Goal

- [ ] T106 [US5] Chạy kịch bản người không chuyên trong `specs/010-expert-knowledge-acquisition/quickstart.md` và ghi finding ngắn gọn vào Gate Card
- [ ] T107 [US1] Chạy E2E cá nhân và dùng chung từ chọn thư viện đến hỏi lại/thu hồi trong `tests/test_expert_knowledge_e2e.py`
- [ ] T108 Chạy toàn bộ quality gate, smoke giao diện và ghi đúng lệnh/mã thoát/phạm vi vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [ ] T109 Kiểm toán độc lập logic, quyền riêng tư, ghi đồng thời và UX/UI; chỉ khi không còn finding mức chặn mới đồng bộ `ARCHITECTURE.md`, `ROADMAP.md` và `PROJECT_HANDOVER.md`

## Phụ thuộc của phần mở lại

R1 và test của R2 có thể làm song song khi không sửa cùng file. R2 phải xong trước khi nối form xác nhận mới. R3 phải xong trước nút “Xác nhận và đưa vào thư viện”. R4 phải xong trước lượt đi bộ người không chuyên. R5 là cổng cuối và không được kế thừa trạng thái `PASS` của T000–T080.

MVP sửa là R1 + R2 + luồng văn bản cá nhân trong R3/R4. Audio và thư viện dùng chung chỉ bật lại sau khi test ranh giới dữ liệu và ghi an toàn đạt; điều này không chặn trợ lý cá nhân bằng văn bản.
