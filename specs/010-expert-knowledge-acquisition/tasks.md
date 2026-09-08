# Danh sách việc: Phỏng vấn chuyên gia và làm giàu tri thức có kiểm soát

## Giai đoạn 1 — G0: Khóa mặc định, baseline và fixture

- [x] T000 Pin commit/tag, đọc kiến trúc/test/license và lập ma trận `adopt|adapt|reject` cho STORM/Co-STORM, LangGraph, Microsoft GraphRAG, Microsoft Presidio, `whisper.cpp` và `faster-whisper` trong `specs/010-expert-knowledge-acquisition/research.md`
- [x] T001 Xác minh sáu mặc định đã khóa về identity, scope, consent, retention, collection và fine-tune trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T002 Xác minh ADR-0009 ở trạng thái `ACCEPTED` và không còn câu chờ quyết định trước G1 trong `docs/adr/0009-expert-interview-and-knowledge-publication-boundary.md`
- [x] T003 Tạo feature flags mặc định tắt cho coverage, interview, audio và publication trong `src/aios_habit/feature_flags.py`
- [x] T004 Tạo corpus, hội thoại và audio fixture giả lập không chứa dữ liệu thật trong `tests/fixtures/expert_interview/`
- [x] T005 Viết kiểm thử fixture không có secret, dữ liệu thật hoặc đường dẫn local trong `tests/test_expert_interview_fixture_hygiene.py`
- [x] T006 Ghi baseline test, trạng thái worktree và cổng G0 vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T007 Chạy Audit Specialist bằng agent/phiên tách biệt, tự sửa finding trong phạm vi rồi đổi Gate Card sang `ACTIVE_G1` khi T000–T006 đạt trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Giai đoạn 2 — G1: Danh tính và phạm vi nhiều chuyên gia

**Kiểm thử độc lập**: principal thật/fixture được ánh xạ đúng profile; prompt/form không mạo danh được; grant sai scope, hết hạn hoặc bị thu hồi đều bị từ chối.

- [x] T008 [US2] Định nghĩa `VerifiedPrincipal`, `ExpertProfile`, `ScopeGrant` và action constants trong `src/aios_habit/expert_identity.py`
- [x] T009 [US2] Định nghĩa protocol `IdentityProvider` và adapter fixture trong `src/aios_habit/expert_identity.py`
- [x] T010 [US2] Cài adapter Windows/OS identity đã khóa mặc định, không lưu password, trong `src/aios_habit/expert_identity_windows.py`
- [x] T011 [US2] Mở rộng authorization canonical để kiểm tra principal, action, scope và thời hạn trong `src/aios_habit/workspace_case_authorization.py`
- [x] T012 [US2] Lưu profile/grant append-only bằng migration an toàn trong `src/aios_habit/workspace_case_repository.py`
- [x] T013 [P] [US2] Viết test mạo danh, duplicate subject, disable, expiry, revoke và provider failure trong `tests/test_expert_identity.py`
- [x] T014 [P] [US2] Viết test không fallback `local_admin` khi multi-user bật trong `tests/test_expert_identity.py`
- [x] T015 [US2] Ghi capability/negative-test receipt; nếu máy dev thiếu nhiều tài khoản OS thì giữ runtime multi-user tắt, dùng fixture cho contract và tiếp tục G2 trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Giai đoạn 3 — G2: US1 lập bản đồ và khoảng trống tri thức

**Kiểm thử độc lập**: corpus fixture tạo gap thiếu, xung đột (ít nhất 2 nguồn) và lỗi thời đúng evidence; gap hallucinated hoặc thiếu citation bị loại; model không tự accept gap.

- [x] T016 [US1] Định nghĩa coverage/gap models và state transitions trong `src/aios_habit/knowledge_coverage.py`
- [x] T017 [US1] Adapter lấy inventory và retrieval receipt qua interface hiện có (có production adapter và fake adapter cùng contract) trong `src/aios_habit/knowledge_coverage.py`
- [x] T018 [US1] Định nghĩa bộ câu hỏi bao phủ có expected evidence và version trong `src/aios_habit/knowledge_coverage.py`
- [x] T019 [US1] Thu receipt retrieval (câu hỏi, nguồn, snippets, điểm bao phủ, version/timestamp, lý do) và tạo tín hiệu deterministic thiếu nguồn, mâu thuẫn, stale metadata từ nguồn thật trong `src/aios_habit/knowledge_coverage.py`
- [x] T020 [US1] C-AGENT qua Brain Gateway đọc gói bằng chứng giới hạn (chỉ snippet_id thật) giải thích/xếp hạng gap, loại bỏ output thiếu citation hoặc ngoài retrieval, không tự accept gap trong `src/aios_habit/knowledge_coverage.py`
- [x] T021 [US1] Lưu coverage/gap event idempotent trong `src/aios_habit/workspace_case_repository.py`
- [x] T022 [US1] Thêm service review `accept|merge|defer|reject` có scope trong `src/aios_habit/workspace_case_service.py`
- [x] T023 [P] [US1] Viết integration test chứng minh gói thật qua Brain Gateway/policy, local_only tự suy ra và bị chặn ở đường không hợp lệ, citation ngoài retrieval bị loại, cấm model tự accept trong `tests/test_knowledge_coverage.py`
- [x] T024 [US1] Thêm màn hình kiểm kê và danh sách nội dung còn thiếu bằng tiếng Việt đời thường trong `src/aios_habit/workspace_case_ui.py`

## Giai đoạn 4 — G3: Lập kế hoạch phỏng vấn

**Kiểm thử độc lập**: một gap accepted tạo plan đúng chuyên gia/scope, câu hỏi nền, ngân sách và completion rubric; plan thiếu expert hợp lệ bị chặn.

- [x] T025 [US2] Định nghĩa `InterviewPlan` và version/digest trong `src/aios_habit/expert_interview_models.py`
- [x] T026 [US2] Chọn eligible experts từ verified profile và grant, không từ model text, trong `src/aios_habit/expert_interview_service.py`
- [x] T027 [US2] Sinh seed questions theo gap/process và kiểm tra schema trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T028 [US2] Khóa max turns/time/token, completion rubric và escalation owner trong `src/aios_habit/expert_interview_service.py`
- [x] T029 [P] [US2] Viết test plan đúng/sai scope, empty expert, stale gap và budget vô hạn trong `tests/test_adaptive_expert_interview.py`

## Giai đoạn 5 — G4: US2 chat thích nghi nhiều vòng

**Kiểm thử độc lập**: câu trả lời mơ hồ khiến C-AGENT qua Brain Gateway hỏi đúng ngưỡng, đơn vị và ngoại lệ; `unknown`, pause, restart và conflict hoạt động; không lặp vô hạn.

- [x] T030 [US2] Cài máy trạng thái phiên và transition validator trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T031 [US2] Lưu session, turn và checkpoint append-only/idempotent trong `src/aios_habit/expert_interview_repository.py`
- [x] T032 [US2] Bind session với principal, expert, plan và kiểm tra lại quyền mỗi turn trong `src/aios_habit/expert_interview_service.py`
- [x] T033 [US2] Gọi C-AGENT qua Brain Gateway với schema `next_action`, trigger refs và privacy label trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T034 [US2] Chặn câu hỏi ngoài scope, dẫn dắt, semantic duplicate và vượt budget trong `src/aios_habit/adaptive_interview_engine.py`
- [x] T035 [US2] Hỗ trợ `unknown|uncertain|skip|pause|stop` và correction version trong `src/aios_habit/expert_interview_service.py`
- [x] T036 [US2] Thêm khung trò chuyện tiếng Việt, tiến độ, giới hạn và nút dừng/tiếp tục dễ hiểu trong `src/aios_habit/workspace_case_ui.py`
- [x] T037 [P] [US2] Viết contract test ambiguity, threshold, exception, example, contradiction và no-leading trong `tests/test_adaptive_expert_interview.py`
- [x] T038 [P] [US2] Viết fault test timeout, schema repair, restart/resume và duplicate submit trong `tests/test_expert_interview_recovery.py`

## Giai đoạn 6 — G5: US3 audio và chép lời cục bộ

**Kiểm thử độc lập**: record trước consent bị chặn; text chat vẫn chạy khi từ chối; transcript local có timestamps và critical tokens phải xác nhận.

- [x] T039 [US3] Định nghĩa consent/audio/transcription protocol và receipt trong `src/aios_habit/local_transcription.py`
- [x] T040 [US3] Viết benchmark `whisper.cpp` và `faster-whisper` trên fixture tiếng Việt trong `scripts/benchmark_local_transcription.py`
- [x] T041 [US3] Tự chọn engine theo điểm benchmark tất định rồi ghi version, checksum, license và tài nguyên vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [x] T042 [US3] Cài một adapter local đã thắng benchmark, pin version và timeout trong `src/aios_habit/local_transcription.py`
- [x] T043 [US3] Lưu audio/transcript dưới `local_only` root cấu hình sẵn với path validation và digest trong `src/aios_habit/expert_interview_repository.py`
- [x] T044 [US3] Thêm lời đồng ý theo phiên bản, chỉ báo đang ghi, rút đồng ý và phương án trả lời bằng chữ trong `src/aios_habit/workspace_case_ui.py`
- [x] T045 [US3] Thêm sửa bản chép lời theo đoạn và xác nhận mã máy, con số, đơn vị trong `src/aios_habit/workspace_case_ui.py`
- [x] T046 [P] [US3] Viết test consent lifecycle, device failure, corrupt audio, critical token và UTF-8 trong `tests/test_local_transcription.py`
- [x] T047 [P] [US3] Viết privacy test không có raw audio/transcript trong Git, case DB, log và provider payload trong `tests/test_expert_interview_privacy.py`
- [x] T052 [US4] Lưu claim event/version và review decision trong `src/aios_habit/expert_interview_repository.py`
- [x] T053 [P] [US4] Viết test unsupported claim, exact provenance, uncertainty, correction và conflict trong `tests/test_knowledge_claims.py`

## Giai đoạn 8 — G7: US4 SOP/bài học và phê duyệt

**Kiểm thử độc lập**: Gemini tạo SOP/lesson candidate có claim map/diff; đúng người duyệt exact digest; sửa sau duyệt làm approval stale.

- [x] T054 [US4] Định nghĩa artifact, version, claim map và approval matrix trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T055 [US4] Sinh SOP và lesson candidate tiếng Việt từ claim được phép trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T056 [US4] Tạo diff giữa artifact versions và mục cần quyết định cho conflict trong `src/aios_habit/controlled_knowledge_artifact.py`
- [x] T057 [US4] Cài approve/reject/request-change/revoke theo exact digest và scope trong `src/aios_habit/expert_interview_service.py`

- [ ] T060 [US5] Định nghĩa `PublicationPackage` bất biến và acceptance question set trong `src/aios_habit/knowledge_publication.py`
- [ ] T061 [US5] Xác minh approval, status, digest và collection trước publication trong `src/aios_habit/knowledge_publication.py`
- [ ] T062 [US5] Nối backup và `LibraryWriterLease` hiện có, không ghi SQL trực tiếp từ model, trong `src/aios_habit/knowledge_publication.py`
- [ ] T063 [US5] Nạp Markdown/JSON qua pipeline collection hiện có và ghi source digest trong `src/aios_habit/knowledge_publication.py`
- [ ] T064 [US5] Chạy SQLite `quick_check`, retrieval acceptance và receipt trước trạng thái published trong `src/aios_habit/knowledge_publication.py`
- [ ] T065 [US5] Cài revoke, supersede, re-index và rollback receipt trong `src/aios_habit/knowledge_publication.py`
- [ ] T066 [US5] Thêm màn hình đưa vào thư viện/thu hồi cùng trạng thái sao lưu/kiểm tra bằng tiếng Việt trong `src/aios_habit/workspace_case_ui.py`
- [ ] T067 [P] [US5] Viết test unpublished/conflicted/revoked filtering và stale package trong `tests/test_knowledge_publication.py`
- [ ] T068 [P] [US5] Viết fault test writer busy, disk-full simulation, interrupted ingest và restore trong `tests/test_knowledge_publication_recovery.py`

- [ ] T071 Viết test không dùng raw audio/transcript/local-only và không tự chạy train trong `tests/test_fine_tune_eligibility.py`
- [ ] T072 Ghi kết luận `NOT_APPLICABLE` cho fine-tune trong feature 010 cùng số đo baseline vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Giai đoạn 11 — G10: Pilot thật, bảo mật và đóng cổng

- [ ] T073 Cập nhật threat model, privacy impact và retention đã duyệt trong `docs/security/THREAT_MODEL.md` và `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`
- [ ] T074 Chạy E2E fixture trọn vòng gap đến chat, claim, SOP, publish và revoke trong `tests/test_expert_knowledge_e2e.py`
- [ ] T075 Chạy E2E Windows với path tiếng Việt/khoảng trắng, restart và local transcription theo `specs/010-expert-knowledge-acquisition/quickstart.md`
- [ ] T076 Chạy diễn tập tự động tối thiểu 2 danh tính chuyên gia fixture, 2 scope, 3 phiên và 5 gap; chỉ ghi receipt đã làm sạch vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [ ] T077 Đo 5 đơn vị tri thức, 1 quy trình fixture, provenance/citation, unauthorized access và critical-token confirmation theo SC-001–SC-008 trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [ ] T078 Chạy đầy đủ quality gate, quét cấm từ kỹ thuật tiếng Anh trên giao diện và ghi command, exit code, phạm vi vào `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`
- [ ] T079 Đồng bộ trạng thái thực tế trong `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md` và `Thảo_luận_AI_dự_đoán_lỗi_LSU.md`
- [ ] T080 Chạy Audit Specialist bằng agent/phiên tách biệt, tự sửa và kiểm toán lại logic, privacy, quyền và evidence; chuyển Gate Card sang `TECHNICAL_READY` khi SC-001–SC-010 đạt trong `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md`

## Phụ thuộc và chiến lược

T000 phải hoàn tất trước code để không viết lại pattern đã trưởng thành. T001–T007 khóa mặc định và tự mở G1 sau audit agent. G2 tạo gap; G3 lập plan; G4 là MVP chat văn bản; G5 audio local; G6–G8 claim, duyệt và thư viện; G9 tự kết luận fine-tune `NOT_APPLICABLE`; G10 diễn tập kỹ thuật bằng fixture.

Task `[P]` chỉ chạy song song khi không sửa cùng file và task nền của giai đoạn đã xong. Sau mỗi cổng, Gemini tự chuyển việc cho Audit Specialist ở agent/phiên tách biệt, sửa finding rồi tiếp tục; không chờ con người quyết định phase và không tự vừa implement vừa ghi PASS.
